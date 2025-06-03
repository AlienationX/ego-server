from django.shortcuts import render
from django.db.models import Q, Func, Value
from django.core.cache import cache
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from datetime import datetime, timedelta
import random

from ..models import Wall
from ..serializers import WallSerializer
from ..paginations import CustomPageNumberPagination
from ..renderers import CustomJSONRenderer
from ..permissions import HasAccessKey

import logging

logger = logging.getLogger(__name__)


class ApiModelView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Wall.objects.select_related('classify').all()
    serializer_class = WallSerializer
    pagination_class = CustomPageNumberPagination  # 使用自定义分页类
    renderer_classes = [CustomJSONRenderer]        # 使用自定义渲染器，额外统一增加code和message字段。默认是JSONRenderer

    def get_queryset(self):
        # 获取查询参数中的 class_id
        classify_id = self.request.query_params.get("classify_id")

        # 获取所有数据
        queryset = self.queryset

        # 如果 class_id 参数存在，则过滤查询集
        if classify_id:
            queryset = queryset.filter(classify_id=classify_id)

        # 返回最终的查询集
        return queryset

    @action(detail=False, methods=['get'])
    def random(self, request):
        # detail=True 表示这个动作是针对单个对象的，如果设置为 False，则表示这个动作是针对所有对象的。

        # 获取所有的对象，且classify.enable为True的数据
        queryset = self.get_queryset().filter(Q(classify__enable=True))

        # 方法 1：使用 order_by('?') 来随机排序，返回前 9 条数据
        random_queryset = queryset.order_by('?')[:9]

        # 方法 2：或者使用 random.sample() 来从 queryset 中随机选择 10 条数据
        # import random
        # random_queryset = random.sample(list(queryset), 10)  # 使用 list() 转换为列表进行随机选择

        # 将随机选择的数据序列化
        serializer = self.get_serializer(random_queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        # detail=True 表示这个动作是针对单个对象的，如果设置为 False，则表示这个动作是针对所有对象的。

        keyword = self.request.query_params.get("keyword")
        if not keyword:
            # 如果kw为空则返回空结果
            return Response([])

        # 获取所有数据
        # queryset = Wall.objects.all()
        queryset = self.get_queryset()

        # 使用 Q 对象进行过滤
        # models.XX.objects.filter( Q(id=10) )
        # models.XX.objects.filter( Q(id=10)&Q(age=19) )
        # models.XX.objects.filter( Q(id=10)|Q(age=19) )
        # models.XX.objects.filter( Q(id__gt=10)|Q(age__lte=19) )
        # models.XX.objects.filter( Q( Q(id__gt=10)|Q(age__lte=19) ) & Q(name=19))

        # 以年龄为例
        # res = models.User.objects.filter(age__gt=35)
        # 1、年龄大于35的：age__gt=35
        # 2、年龄小于35的：age__lt=35
        # 3、年龄大于等于35的：age__gte=35
        # 4、年龄小于等于35的：age__lte=35
        # 5、age__in=[1,3,5]   # age=1 or age=3 or age=5   （in走索引、not in不在索引）
        # 6、age__range=[18,40] # where age between 18 and 40
        # 7、age__contains="s" # age like %s%  包含s的
        # 8、age__icontains="s"  #忽略大小写
        # 9、age__startswith= "m" #以m开头的 age like m%
        # 10、age__endswith= "m" #以m结尾的 age like %n
        # 11、create_time__year="2021" #查出某一年的
        # 12、create_time__mouth="10" #查出某一月的
        # 13、create_time__day="17" #查出每个月17号的

        # 进行过滤，description 字段包含kw关键字，或者 tabs字段包含kw关键字
        # search_fields = ["description", "tabs", "classify.enable"]
        queryset = queryset.filter(Q(classify__enable=True) & (Q(description__contains=keyword) | Q(tabs__contains=keyword)))
        
        data = []

        # 进行排序
        sortord = self.request.query_params.get("sortord")
        if sortord:
            if sortord == "random":
                # 随机排序，性能差且分页会出现重复数据。其实使用缓存结果即可解决这个问题
                # queryset = queryset.order_by('?')

                # annotate增加虚拟计算列，功能强大
                # 随机排序，固定种子，保证固定时间内数据是有序的
                # now = datetime.now()
                # start_of_interval = now - timedelta(minutes=now.minute % 10)  # 使用每10分钟一个区间作为种子生成固定随机顺序
                # seed = int(start_of_interval.strftime("%Y%m%d"))  # 种子到天即可，因为有缓存实效时间控制
                # 1. mysql的随机函数是RAND，支持传入固定种子保持顺序不变
                # queryset = queryset.annotate(random_order=Func(Value(seed), function='RAND')).order_by('random_order')  
                # 2. postgresql的随机函数是RANDOM，不支持出入种子，需结合setseed实现 setseed(seed)+RANDOM()
                # queryset = queryset.annotate(random_order=Func(Value(seed), function='RANDOM')).order_by('random_order')  # 报错
                # 3. 使用django的函数库Random，但是不支持固定种子，结果还是乱序和重复的 
                # from django.db.models.functions import Random
                # queryset = queryset.annotate(random_order=Random() * Value(seed)).order_by('random_order')

                # 4. 跨数据库的标准方式，使用缓存，强烈推荐
                # import random
                # from django.core.cache import cache

                #     # 缓存当日结果
                #     cache_key = f"daily_products_{datetime.today().strftime('%Y%m%d')}"
                #     products = cache.get(cache_key)
                    
                #     if not products:
                #         products = list(Product.objects.all())
                #         random.seed(seed)  # 固定种子
                #         random.shuffle(products)
                #         cache.set(cache_key, products, timeout=86400)  # 缓存24小时
                #     return products

                # 最终方案，乱序加缓存
                cache_key = f"walls_{keyword}"
                
                # data = cache.get(cache_key)
                # if not data:
                #     queryset = queryset.order_by('?')
                #     data = list(queryset.values())
                #     cache.set(cache_key, data, timeout=5)  # 缓存5秒

                data = cache.get_or_set(cache_key, lambda: list(queryset.order_by('?').values()), timeout=600)  # 缓存10分钟

            elif sortord == "score":
                queryset = queryset.order_by('-score')
            elif sortord == "date_asc":
                queryset = queryset.order_by('updated_at')
            elif sortord == "date_desc":
                queryset = queryset.order_by('-updated_at')

        # 没有走random排序，就使用现有的queryset
        if not data:
            data = list(queryset.values())

        # 如果启用分页器，则返回分页信息
        if ApiModelView.pagination_class is not None:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(data, request)
            return paginator.get_paginated_response(paginated_data)

        return Response(data)
    
        # 直接使用data返回，不再使用下面花里胡哨的东西

        # # DRF的ModelViewSet在默认的list、retrieve等方法中会自动处理分页，但对于自定义的action，开发者需要手动集成分页逻辑。
        # # 手动分页处理，如果存在分页器类，且数据量大于分页数则显示分页信息
        # page = self.paginate_queryset(queryset)  # 关键！调用分页方法
        # # print(self.paginator.page_size)  # self.paginator 即为 CustomPageNumberPagination
        # if page and queryset.count() > self.paginator.page_size:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)  # 返回分页响应

        # # 数据序列化
        # serializer = self.get_serializer(queryset, many=True)
        # return Response(serializer.data)
