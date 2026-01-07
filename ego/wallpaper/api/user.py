import logging
import random

import requests
from django.contrib.auth.models import User
from django.db import connection
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from ..models import Actions, Profile
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import ProfileSerializer, UserSerializer, WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(RetrieveModelMixin, GenericViewSet):

    queryset = User.objects.select_related("profile").all()
    serializer_class = UserSerializer
    # authentication_classes = [JSONWebTokenAuthentication]  # JWT 认证, 已在settings中全局配置
    # permission_classes = [HasAccessKey, IsAuthenticated]
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    @action(detail=False, methods=["get"])
    def me(self, request):
        # JWT通过，会将user放入到request.user中，没有登录默认返回是AnonymousUser
        user = request.user
        if not user.is_authenticated:
            # /user/1/ 可以直接访问，但 /user/me/ 需要认证
            return Response({"error": "未认证或token无效"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            serializer = UserSerializer(user)
            # return Response(serializer.data)  # 直接返回序列化数据

            # 将序列化后的数据复制为可变 dict 并添加统计字段
            data = dict(serializer.data)
            user_id = user.id
            collect_count = Actions.objects.filter(user_id=user_id, is_collect=True).count()
            download_count = Actions.objects.filter(user_id=user_id, is_download=True).count()
            rate_count = Actions.objects.filter(user_id=user_id, pic_score__isnull=False).count()
            data["count"] = {
                "collect_count": collect_count,
                "download_count": download_count,
                "rate_count": rate_count,
            }
            return Response(data)
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return Response({"error": f"获取用户信息失败: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def my_collect(self, request, *args, **kwargs):
        """用户收藏壁纸"""
        user = request.user
        # 使用 select_related 避免 N+1 查询
        actions = Actions.objects.filter(user_id=user.id, is_collect=True).select_related("wall")

        # 提取关联的壁纸对象
        walls = [action.wall for action in actions if action.wall]

        # 使用 WallSerializer 序列化壁纸数据
        serializer = WallSerializer(walls, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_download(self, request, *args, **kwargs):
        """用户下载壁纸"""
        user = request.user
        # 使用 select_related 避免 N+1 查询
        actions = Actions.objects.filter(user_id=user.id, is_download=True).select_related("wall")

        # 提取关联的壁纸对象
        walls = [action.wall for action in actions if action.wall]

        # 使用 WallSerializer 序列化壁纸数据
        serializer = WallSerializer(walls, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_rate(self, request, *args, **kwargs):
        """用户评分壁纸"""
        user = request.user
        # 使用 select_related 避免 N+1 查询
        actions = Actions.objects.filter(user_id=user.id, pic_score__isnull=False).select_related("wall")

        # 提取关联的壁纸对象
        walls = [action.wall for action in actions if action.wall]

        # 使用 WallSerializer 序列化壁纸数据
        serializer = WallSerializer(walls, many=True)
        return Response(serializer.data)

    # def retrieve(self, request, *args, **kwargs):
    #     # 获取路径上的pk/id值
    #     # print(self.kwargs)
    #     # print(self.kwargs.get('pk'))

    #     url = "http://whois.pconline.com.cn/ipJson.jsp"
    #     ip = request.META.get('REMOTE_ADDR')
    #     params = {"ip": ip, "json": "true"}

    #     province = ""
    #     city = ""
    #     region = ""

    #     try:
    #         logger.info(f"请求的IP地址: {ip}")
    #         # ​​连接超时​​：3 秒内未建立连接则抛出 ConnectTimeout。
    #         # ​​读取超时​​：连接建立后，5 秒内未收到数据则抛出 ReadTimeout。
    #         response = requests.get(url, params=params, timeout=(2, 1))

    #         response.raise_for_status()

    #         data = response.json()
    #         province = data.get("pro", "")
    #         city = data.get("city", "")
    #         region = data.get("region", "")

    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"IP查询接口请求失败: {e}")
    #         regions = ["地球", "月球", "太阳系", "银河系", "宇宙", "黑洞", "未知", "unknown"]
    #         region = regions[random.randint(0, len(regions)-1)]
    #     except Exception as e:
    #         # 异常处理，url问题、请求超时等 e.args / str(e) / repr(e)
    #         logger.error(f"系统异常: {e}")
    #         region = "error"
    #         # return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    #     return Response({
    #         "id": -1,
    #         "name": "unknown",
    #         "IP": ip,
    #         "address": {
    #             "province": province,
    #             "city": city,
    #             "region": region
    #         }
    #     })
