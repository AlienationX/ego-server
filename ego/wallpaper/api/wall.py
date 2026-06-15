import logging
from datetime import datetime

from django.core.cache import cache
from django.db.models import F, Func, Q, Value
from django.forms.models import model_to_dict
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Wall
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(ListModelMixin, CreateModelMixin, GenericViewSet):
    queryset = Wall.objects.select_related("classify").all()
    serializer_class = WallSerializer
    permission_classes = [HasAccessKey]
    pagination_class = CustomPageNumberPagination  # 使用自定义分页类
    renderer_classes = [CustomJSONRenderer]  # 使用自定义渲染器，额外统一增加code和message字段。默认是JSONRenderer

    def get_queryset(self):
        # 获取所有数据，且classify.enable为True的数据
        queryset = self.queryset.filter(is_active=True)

        # 获取查询参数中的 classify_id ，如果参数存在，则过滤查询集
        classify_id = self.request.query_params.get("classify_id")
        if classify_id:
            queryset = queryset.filter(classify_id=classify_id)

        # 获取查询参数中的 classify_enable
        classify_enable = self.request.query_params.get("classify_enable")
        if classify_enable not in ("false", "False"):
            queryset = queryset.filter(classify__enable=True)

        # 返回最终的查询集
        return queryset

    def _get_sorted_data(self, queryset, keyword=None):
        """
        统一处理排序和缓存逻辑
        """
        sortord = self.request.query_params.get("sortord")
        classify_id = self.request.query_params.get("classify_id", "0")
        data = None

        # 向查询集中的每个对象添加一个名为 classify_name 的新字段，值为 classify__name
        # F 表达式，用于引用模型字段：classify ：当前模型的外键字段，__name ：双下划线表示跨关系查询，获取 classify 关联对象的 name 属性
        queryset = queryset.annotate(classify_name=F("classify__name"))
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
            cache_key = f"walls_rand_{keyword or 'blank'}_{classify_id}"

            # data = cache.get(cache_key)
            # if not data:
            #     data = list(queryset.order_by('?').values())
            #     cache.set(cache_key, data, timeout=5)  # 缓存5秒

            # 使用list(queryset.order_by('?').values())会丢失序列化器的处理逻辑
            data = cache.get_or_set(cache_key, lambda: list(queryset.order_by("?").values()), timeout=10 * 60)
            # 极慢，不推荐
            # data = cache.get_or_set(
            #     cache_key, lambda: self.get_serializer(queryset.order_by("?"), many=True).data, timeout=600
            # )  # 缓存10分钟

        elif sortord == "score":
            cache_key = f"walls_score_{keyword or 'blank'}_{classify_id}"
            data = cache.get_or_set(
                cache_key, lambda: list(queryset.order_by("-score", "-updated_at", "-id").values()), timeout=10 * 60
            )
        elif sortord == "date_asc":
            cache_key = f"walls_date_asc_{keyword or 'blank'}_{classify_id}"
            data = cache.get_or_set(cache_key, lambda: list(queryset.order_by("updated_at", "-id").values()), timeout=60 * 60)
        # elif sortord == "date_desc":
        else:
            cache_key = f"walls_date_desc_{keyword or 'blank'}_{classify_id}"
            data = cache.get_or_set(cache_key, lambda: list(queryset.order_by("-updated_at", "-id").values()), timeout=60 * 60)

        # if data is not None:
        #     return data
        # else:
        #     return list(queryset.values())
        # return self.get_serializer(queryset, many=True).data  # 极慢，不推荐

        return data

    def list(self, request, *args, **kwargs):
        """重写list方法，添加过滤和排序逻辑"""
        queryset = self.get_queryset()
        data = self._get_sorted_data(queryset)

        # 使用 DRF 内置的分页逻辑
        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(data)

    def create(self, request, *args, **kwargs):
        """更新壁纸相关信息，如名称、描述、分类等。update接口是put请求，为了统一接口，这里使用create"""
        user = request.user
        if not user.is_authenticated or not user.is_staff:
            return Response({"error": "您没有权限修改壁纸信息"}, status=status.HTTP_403_FORBIDDEN)

        try:
            data = request.data.copy()
            wall_obj = self.queryset.filter(id=data.get("id")).first()
            if not wall_obj:
                return Response({"error": "壁纸不存在"}, status=status.HTTP_404_NOT_FOUND)

            data.pop("id", None)
            # 更新数据，类似于 wall_obj.classify_id = classify_id, wall_obj.description = description
            for attr, value in data.items():
                setattr(wall_obj, attr, value)
            wall_obj.save(update_fields=list(data.keys()))  # 仅更新变化的字段
            return Response(model_to_dict(wall_obj))
        except Exception as e:
            logger.error(e, exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def random_daily(self, request):
        # detail=True 表示这个动作是针对单个对象的，如果设置为 False，则表示这个动作是针对所有对象的。

        cache_key = f"walls_rand_daily_{datetime.today().strftime('%Y%m%d')}"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        # 获取所有的对象，且classify.enable为True的数据
        queryset = self.get_queryset()

        # 方法 1：使用 order_by('?') 来随机排序，返回前 n 条数据
        random_queryset = queryset.order_by("?")[:12]

        # 方法 2：或者使用 random.sample() 来从 queryset 中随机选择 n 条数据
        # import random
        # random_queryset = random.sample(list(queryset), 12)  # 使用 list() 转换为列表进行随机选择

        # 缓存序列化后的数据，避免直接缓存 QuerySet
        serializer = self.get_serializer(random_queryset, many=True)
        data = serializer.data
        cache.set(cache_key, data, timeout=10 * 60)  # 缓存10分钟
        return Response(data)

    @action(detail=False, methods=["get"])
    def random_recommend(self, request):
        cache_key = f"walls_rand_recommend_{datetime.today().strftime('%Y%m%d')}"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        # 获取所有的对象，且classify.enable为True的数据
        queryset = self.get_queryset()

        data = []
        # 获取查询参数中的 classify_ids
        classify_ids = self.request.query_params.get("classify_ids")
        if classify_ids:
            classify_ids = classify_ids.split(",")
            queryset = queryset.filter(Q(classify_id__in=classify_ids))
            for classify_id in classify_ids:
                # 过滤该分类的数据并随机排序
                classified_queryset = queryset.filter(classify_id=classify_id).order_by("?")[:12]
                first_wall = classified_queryset.first()
                if first_wall:  # 只有当有数据时才添加
                    data.append(
                        {
                            "id": first_wall.classify.id,
                            "name": first_wall.classify.name,
                            "name_en": first_wall.classify.name_en,
                            "data": self.get_serializer(classified_queryset, many=True).data,
                        }
                    )

        cache.set(cache_key, data, timeout=10 * 60)  # 缓存10分钟
        return Response(data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        # detail=True 表示这个动作是针对单个对象的，如果设置为 False，则表示这个动作是针对所有对象的。

        keyword = self.request.query_params.get("keyword")
        if not keyword:
            # 如果kw为空则返回空结果
            return Response([])

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

        # 进行过滤，description 字段包含kw关键字，或者 tags字段包含kw关键字
        # search_fields = ["description", "tags", "classify.enable"]

        # queryset = Wall.objects.all()
        queryset = self.get_queryset().filter((Q(description__icontains=keyword) | Q(tags__icontains=keyword)))

        data = self._get_sorted_data(queryset, keyword=keyword)

        # 如果启用分页器，则返回分页信息
        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)

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

    @action(detail=False, methods=["get"])
    def top(self, request):
        type = self.request.query_params.get("type")
        n = self.request.query_params.get("n", "10")
        n = int(n)
        if type not in ["views", "downloads"]:
            return Response([])
        if n <= 0:
            n = 10
        if n > 30:
            n = 30
        queryset = self.get_queryset().order_by(f"-{type}")[:n]
        data = self.get_serializer(queryset, many=True).data
        return Response(data)

    # datail=True时，表示这个动作是针对单个对象。url会自动增加pk，例如wall/<pk>/increment_views/
    # pk参数会自动传入increment_views和increment_downloads方法，必须有
    @action(detail=True, methods=["post"])
    def increment_views(self, request, pk=None):
        instance = self.get_object()  # 获取单个对象
        instance.views = F("views") + 1  # 使用 F() 避免竞争条件
        instance.save(update_fields=["views"])
        instance.refresh_from_db(fields=["views"])  # 刷新实例字段值
        return Response({"id": instance.id, "views": instance.views})

    @action(detail=True, methods=["post"])
    def increment_downloads(self, request, pk=None):
        instance = self.get_object()
        instance.downloads = F("downloads") + 1
        instance.save(update_fields=["downloads"])
        instance.refresh_from_db(fields=["downloads"])
        return Response({"id": instance.id, "downloads": instance.downloads})
