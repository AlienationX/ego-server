import logging
import random
import string

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from ..renderers import CustomJSONRenderer

logger = logging.getLogger(__name__)


class ApiModelView(ViewSet):
    """激励视频奖励接口，接收前端传来的奖励相关参数，进行记录"""

    permission_classes = []  # uni-ad设置的回调函数，不支持key或token的设置，暂时关闭
    # pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):
        queryParams = request.query_params
        logger.info(f"Uniapp received query parameters: {queryParams}")
        return Response({"Uniapp queryParams": queryParams})

    def create(self, request, *args, **kwargs):
        """
        新增激励视频奖励记录
        """
        access_key = request.data.get("access_key")
        if access_key:
            # 检查access_key是否符合要求
            if len(access_key) < 4:
                return Response(
                    {"error": "access_key is invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            access_key = "".join(random.choices(string.ascii_letters + string.digits, k=6))

        cache_key = f"rewards_{access_key}"

        # 验证缓存中是否有cache_key，有的话+1，没有的话设置为1
        value = cache.get(cache_key)
        new_value = value + 1 if value else 1
        cache.set(cache_key, new_value, timeout=600)

        return Response({"access_key": access_key, "count": new_value})

    @action(detail=False, methods=["get"])
    def check(self, request, *args, **kwargs):
        """
        检查激励视频奖励记录
        """
        data = request.query_params
        access_key = data.get("access_key")

        if not access_key:
            return Response(
                {"error": "access_key is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"rewards_{access_key}"
        value = cache.get(cache_key)

        if value:
            # 删除缓存
            cache.delete(cache_key)
            return Response({"detail": "ok"})
        else:
            return Response(
                {"error": "access_key not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
