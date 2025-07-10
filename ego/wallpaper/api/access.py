from django.conf import settings
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from utils.ip2region.xdbSearcher import XdbSearcher

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
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        # X-Forwarded-For: client_ip, proxy1_ip, proxy2_ip
        # client_ip 是发起请求的客户端的真实 IP 地址。即第一个。
        # proxy1_ip 和 proxy2_ip 分别是代理服务器的 IP 地址。
        client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR", "unknown")

        db_path = settings.BASE_DIR / "utils/ip2region/ip2region.xdb"  # 数据库打包路径
        try:
            # 缓存优化参考：https://github.com/lionsoul2014/ip2region/tree/master/binding/python
            # 缓存 VectorIndex 索引
            # 缓存整个 xdb 数据
            searcher = XdbSearcher(dbfile=db_path)
            region_str = searcher.searchByIPStr(client_ip)
            searcher.close()
        except Exception as e:
            region_str = "N/A|N/A|N/A|N/A|N/A"

        # 2. 复制请求数据并注入IP
        data = request.data.copy()
        data["ip"] = client_ip  # 后端自动注入IP字段
        data["address"] = region_str.replace("|", ",")  # 解析ip地址存储数据库

        # 3. 数据验证与保存
        serializer = AccessSerializer(data=data)
        if serializer.is_valid():
            serializer.save()  # 自动保存含IP的数据
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # 4. 返回错误详情（如字段缺失/格式错误）
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
