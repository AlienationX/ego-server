from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Wall, Classify, Notice, Banner
from .serializers import WallSerializer, ClassifySerializer, NoticeSerializer, BannerSerializer
from .paginations import CustomPageNumberPagination
from .renderers import CustomJSONRenderer
from .permissions import HasAccessKey

import logging

logger = logging.getLogger(__name__)

# class WallView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
#     queryset = Wall.objects.all()
#     serializer_class = WallSerializer
#     pagination_class = CustomPageNumberPagination  # 使用自定义分页类
#     renderer_classes = [CustomJSONRenderer]        # 使用自定义渲染器，额外统一增加code和message字段。默认是JSONRenderer
#     permission_classes = [HasAccessKey]            # 使用自定义权限

#     def get_queryset(self):
#         # 获取查询参数中的 class_id
#         class_id = self.request.query_params.get("class_id", None)

#         # 获取所有数据
#         # queryset = Wall.objects.all()
#         queryset = self.queryset

#         # 如果 class_id 参数存在，则过滤查询集
#         if class_id is not None:
#             queryset = queryset.filter(class_id=class_id)

#         # 返回最终的查询集
#         return queryset

#     @action(detail=False, methods=['get'])
#     def random(self, request):
#         # detail=True 表示这个动作是针对单个对象的，如果设置为 False，则表示这个动作是针对所有对象的。

#         # 获取所有的对象
#         queryset = self.get_queryset()

#         # 方法 1：使用 order_by('?') 来随机排序，返回前 9 条数据
#         random_queryset = queryset.order_by('?')[:9]

#         # 方法 2：或者使用 random.sample() 来从 queryset 中随机选择 10 条数据
#         # import random
#         # random_queryset = random.sample(list(queryset), 10)  # 使用 list() 转换为列表进行随机选择

#         # 将随机选择的数据序列化
#         serializer = self.get_serializer(random_queryset, many=True)
#         return Response(serializer.data)
    
#     # @action(detail=False, methods=['get'])
#     # def search(self, request):
#     #     # detail=True 表示这个动作是针对单个对象的，如果设置为 False，则表示这个动作是针对所有对象的。

#     #     # 获取所有的对象
#     #     queryset = self.get_queryset()

#     #     # 方法 1：使用 order_by('?') 来随机排序，返回前 9 条数据
#     #     random_queryset = queryset.order_by('?')[:9]

#     #     # 方法 2：或者使用 random.sample() 来从 queryset 中随机选择 10 条数据
#     #     # import random
#     #     # random_queryset = random.sample(list(queryset), 10)  # 使用 list() 转换为列表进行随机选择

#     #     # 将随机选择的数据序列化
#     #     serializer = self.get_serializer(random_queryset, many=True)
#     #     return Response(serializer.data)


# class ClassifyView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
#     queryset = Classify.objects.all()
#     serializer_class = ClassifySerializer
#     pagination_class = None                        # 不使用分页器，直接返回所有数据
#     renderer_classes = [CustomJSONRenderer]

#     def get_queryset(self):
#         # 获取查询参数中的 select
#         select = self.request.query_params.get("select", None)
#         select = True if select == "true" else False

#         # 获取所有数据
#         # queryset = Wall.objects.all()
#         queryset = self.queryset

#         # 如果 select 参数存在，则过滤查询集
#         if select:
#             queryset = queryset.filter(select=select)
#             # select=true即首页显示的分类，只显示8条即可
#             return queryset[:8]

#         # 返回所有数据
#         return queryset


# class NoticeView(ModelViewSet):
#     queryset = Notice.objects.all()
#     serializer_class = NoticeSerializer
#     pagination_class = CustomPageNumberPagination
#     renderer_classes = [CustomJSONRenderer]

#     def list(self, request, *args, **kwargs):
#         # 动态修改分页器的 page_size，只显示 6 个公告
#         self.paginator.page_size = 6
#         return super().list(request, *args, **kwargs)

#     @action(detail=False, methods=['get'])
#     def latest(self, request):
#         # 假设 'publish_date' 是你要倒序排列的字段，- 代表倒序的意思
#         latest_queryset = self.get_queryset().order_by('-publish_date')[:3]

#         # 将查询集序列化
#         serializer = self.get_serializer(latest_queryset, many=True)

#         return Response(serializer.data)


# class BannerView(ModelViewSet):
#     queryset = Banner.objects.all()
#     serializer_class = BannerSerializer
#     renderer_classes = [CustomJSONRenderer]

#     def get_queryset(self):
#         # 自定义结果集
#         # 获取enable=True的数据并按 'created_at' 字段倒序排序，返回前 4 个滑动图
#         return self.queryset.filter(enable=True).order_by('-created_at')[:4]
