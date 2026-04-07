import logging
import random

from django.db import connection, transaction
from django.db.models import Avg, F
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from ..models import Actions, Wall
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import ActionsSerializer, WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(CreateModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Actions.objects.all()
    serializer_class = ActionsSerializer
    # authentication_classes = [JSONWebTokenAuthentication]  # JWT 认证, 已在settings中全局配置
    permission_classes = [HasAccessKey, IsAuthenticated]
    pagination_class = CustomPageNumberPagination  # 使用自定义分页类
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):
        """获取用户对壁纸的操作记录列表，支持过滤和分页。"""
        user = request.user
        action_type = self.request.query_params.get("action_type")  # collect, download, rate

        # 使用 select_related 避免 N+1 查询
        if action_type == "collect":
            actions = self.queryset.filter(user_id=user.id, is_collect=True)
        elif action_type == "download":
            actions = Actions.objects.filter(user_id=user.id, is_download=True)
        elif action_type == "rate":
            actions = Actions.objects.filter(user_id=user.id, pic_score__isnull=False)
        else:
            return Response({"error": "action_type参数错误"}, status=status.HTTP_400_BAD_REQUEST)

        data = self._paginated_walls_response(actions.order_by("-updated_at"))
        if ApiModelView.pagination_class is not None:
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(data, request)
            return paginator.get_paginated_response(paginated_data)
        return Response(data)

    def _paginated_walls_response(self, actions):
        """对 Actions queryset 分页并返回当前页的 wall 列表的分页响应"""
        # 序列化 actions 数据
        serialized_actions = self.serializer_class(actions, many=True).data

        # 处理数据，提取 wall 并添加 my_score 字段
        data = []
        for act in serialized_actions:
            if act.get("wall"):
                wall_data = act["wall"].copy()  # 复制 wall 数据以避免修改原始数据
                wall_data.pop("created_at")
                wall_data.pop("updated_at")
                wall_data["my_score"] = act.get("pic_score")
                wall_data["action_updated_at"] = act.get("updated_at")
                data.append(wall_data)

        return data

    def create(self, request, *args, **kwargs):
        """用户对壁纸的操作，如收藏、下载、评分等。通过 user_id 和 wall_id 进行查找，存在则更新记录，否则创建新记录。"""
        user = request.user
        wall_id = request.data.get("wall_id")

        if not wall_id:
            return Response({"error": "缺少wall_id参数"}, status=status.HTTP_400_BAD_REQUEST)

        # 只接受以下可更新字段，其实只支持一种动作
        update_payload = {}
        for key in ("is_collect", "is_download", "pic_score"):
            if key in request.data:
                value = request.data.get(key)
                update_payload[key] = None if key == "pic_score" and value == 0 else value

        # 如果没有可更新字段，直接返回当前记录
        if not update_payload:
            return Response(
                {"error": "缺少 actions 相关参数 [is_collect, is_download, pic_score]"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 如果多张表同时更新数据，需要开启事务保存
        with transaction.atomic():
            # 使用 user/wall 创建或查找记录
            obj, created = Actions.objects.get_or_create(user_id=user.id, wall_id=wall_id)

            # partial=True 表示只更新部分字段，其他字段保持不变
            serializer = ActionsSerializer(obj, data=update_payload, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()

            # 如果评分被更新，重新计算该壁纸的平均分并保存。可能存在并发更新问题或者性能问题，每晚定时执行更新
            # if "pic_score" in update_payload:
            #     avg = (
            #         Actions.objects.filter(wall_id=wall_id, pic_score__isnull=False).aggregate(avg=Avg("pic_score")).get("avg")
            #     )
            #     Wall.objects.filter(pk=wall_id).update(score=avg)

        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """更新用户对壁纸的操作记录，如收藏、下载、评分等。其实应该使用 update 方法，因为是 upsert 操作。该接口暂时未使用"""
        return super().update(request, *args, **kwargs)
