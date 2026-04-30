from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from utils.tools import get_client_ip, ip_to_region

from ..models import Access
from ..renderers import CustomJSONRenderer
from ..serializers import AccessSerializer

# GeoIP2需要的数据库文件太大，100+MB，不推荐使用
# from django.contrib.gis.geoip2 import GeoIP2
# import geoip2.database


class ApiModelView(CreateModelMixin, GenericViewSet):
    # CreateAPIView = (CreateModelMixin, GenericViewSet)

    queryset = Access.objects.all()
    serializer_class = AccessSerializer
    pagination_class = None  # 不使用分页器，直接返回所有数据
    renderer_classes = [CustomJSONRenderer]
    # permission_classes = []  # 这里可以根据需要设置权限类

    def create(self, request, *args, **kwargs):
        # 1. 获取客户端真实IP（支持代理场景）
        client_ip = get_client_ip(request)

        # 2. 解析IP地址对应的地区信息
        region_str = ip_to_region(client_ip)

        # 3. 复制请求数据并注入IP
        data = request.data.copy()
        data["ip"] = client_ip  # 后端自动注入IP字段
        data["address"] = region_str  # 解析ip地址存储数据库

        # 3. 数据验证与保存
        serializer = AccessSerializer(data=data)
        if serializer.is_valid():
            serializer.save()  # 自动保存含IP的数据
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # 4. 返回错误详情（如字段缺失/格式错误）
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
