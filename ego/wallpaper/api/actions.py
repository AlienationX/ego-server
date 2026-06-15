import logging
import random

from django.db import connection, transaction
from django.db.models import Avg, F, Window
from django.db.models.functions import Rank, RowNumber
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from ..models import UserActions, Wall
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import UserActionsSerializer, WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(CreateModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = UserActions.objects.all()
    serializer_class = UserActionsSerializer
    # authentication_classes = [JSONWebTokenAuthentication]  # JWT 认证, 已在settings中全局配置
    permission_classes = [HasAccessKey]
    pagination_class = CustomPageNumberPagination  # 使用自定义分页类
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):
        """获取用户对壁纸的操作记录列表，支持过滤和分页。"""
        user = request.user
        action_key = self.request.query_params.get("action_key")

        if not user.is_authenticated:
            return Response({"error": "未登录"}, status=status.HTTP_401_UNAUTHORIZED)

        # 目前接口只查询 favorite、download、rate 三个操作的数据，且必须是登录用户的数据
        if action_key in ["view", "download", "like", "favorite", "share", "comment", "rate"]:
            # actions = (
            #     UserActions.objects.annotate(
            #         rank=Window(
            #             expression=RowNumber(),
            #             partition_by=[F("user"), F("wall"), F("action_key")],
            #             order_by=F("updated_at").desc(),
            #         )
            #     )
            #     .filter(user=user, action_key=action_key, action_value__gt=0, rank=1)
            #     .order_by("-updated_at")
            # )
            actions = UserActions.objects.filter(user=user, action_key=action_key, action_value__gt=0).order_by("-updated_at")
        else:
            return Response({"error": "action_key参数错误"}, status=status.HTTP_400_BAD_REQUEST)

        # 处理数据，提取 wall 并添加 my_score 字段
        data = []
        serialized_actions = self.serializer_class(actions, many=True).data
        for act in serialized_actions:
            if act.get("wall"):
                wall_data = act.get("wall").copy()  # 复制 wall 数据以避免修改原始数据
                wall_data.pop("created_at", None)
                wall_data.pop("updated_at", None)
                wall_data["my_score"] = act.get("action_value") if act.get("action_key") == "rate" else None
                wall_data["action_updated_at"] = act.get("updated_at")
                data.append(wall_data)

        # 如果启用分页器，则返回分页信息
        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(data)

    def create(self, request, *args, **kwargs):
        """用户对壁纸的操作，如收藏、下载、评分等。"""
        user = request.user
        device_id = request.headers.get("Device-Id")
        wall_id = request.data.get("wall_id")
        action_key = request.data.get("action_key")
        action_value = request.data.get("action_value")

        if not device_id:
            return Response({"error": "无设备标识"}, status=status.HTTP_400_BAD_REQUEST)

        if not wall_id:
            return Response({"error": "缺少wall_id参数"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_authenticated:
            if action_key not in ["view", "download", "share"]:
                return Response({"error": "未登录用户只能浏览、下载和分享"}, status=status.HTTP_403_FORBIDDEN)

        user_id = user.id if user.is_authenticated else None

        obj = {
            "device_id": device_id,
            "user_id": user_id,
            "wall_id": wall_id,
            "action_key": action_key,
            "action_value": action_value,
        }

        # 如果多张表同时更新数据，需要开启事务保存
        with transaction.atomic():
            user_action, created = UserActions.objects.update_or_create(
                device_id=device_id, user_id=user_id, wall_id=wall_id, action_key=action_key, defaults=obj
            )

        return Response(
            UserActionsSerializer(user_action).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
