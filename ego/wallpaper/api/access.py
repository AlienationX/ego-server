from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Access
from ..renderers import CustomJSONRenderer
from ..serializers import AccessSerializer


class ApiModelView(CreateModelMixin, GenericViewSet):
    # CreateAPIView = (CreateModelMixin, GenericViewSet)

    queryset = Access.objects.all()
    serializer_class = AccessSerializer
    pagination_class = None  # 不使用分页器，直接返回所有数据
    renderer_classes = [CustomJSONRenderer]
    # permission_classes = []  # 这里可以根据需要设置权限类

    def create(self, request, *args, **kwargs):
        # 1. 获取客户端真实IP（支持代理场景）
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        # X-Forwarded-For: client_ip, proxy1_ip, proxy2_ip
        # client_ip 是发起请求的客户端的真实 IP 地址。即第一个。
        # proxy1_ip 和 proxy2_ip 分别是代理服务器的 IP 地址。
        client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR", "unknown")

        # 2. 复制请求数据并注入IP
        data = request.data.copy()
        data["ip"] = client_ip  # 后端自动注入IP字段
        # data["address"] = ""  # 解析ip地址存储数据库

        # 3. 数据验证与保存
        serializer = AccessSerializer(data=data)
        if serializer.is_valid():
            serializer.save()  # 自动保存含IP的数据
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # 4. 返回错误详情（如字段缺失/格式错误）
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
