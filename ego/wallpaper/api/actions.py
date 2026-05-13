import logging
import random

from django.db import connection, transaction
from django.db.models import Avg, F, Window
from django.db.models.functions import RowNumber
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
    permission_classes = [HasAccessKey, IsAuthenticated]
    pagination_class = CustomPageNumberPagination  # 使用自定义分页类
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):
        """获取用户对壁纸的操作记录列表，支持过滤和分页。"""
        user = request.user
        action_key = self.request.query_params.get("action_key")

        if action_key in ["view", "download", "like", "favorite", "share", "comment", "rate"]:
            # actions = (
            #     self.queryset.filter(user_id=user.id, action_key=action_key)
            #     # .annotate(
            #     #     row_number=Window(expression=RowNumber(), partition_by=[F("wall_id")], order_by=F("created_at").desc())
            #     # )
            #     # .filter(row_number=1)
            #     .order_by("-created_at")
            # )
            actions = (
                self.queryset.filter(user_id=user.id, action_key=action_key).filter(action_value__gt=0).order_by("-updated_at")
            )
        else:
            return Response({"error": "action_key参数错误"}, status=status.HTTP_400_BAD_REQUEST)

        # 处理数据，提取 wall 并添加 my_score 字段
        data = []
        serialized_actions = self.serializer_class(actions, many=True).data
        for act in serialized_actions:
            if act.get("wall"):
                wall_data = act["wall"].copy()  # 复制 wall 数据以避免修改原始数据
                wall_data.pop("created_at")
                wall_data.pop("updated_at")
                wall_data["my_score"] = act.get("action_value") if act.get("action_key") == "rate" else None
                wall_data["action_updated_at"] = act.get("updated_at")
                data.append(wall_data)

        # 如果启用分页器，则返回分页信息
        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(data)

        # if ApiModelView.pagination_class is not None:
        #     paginator = self.pagination_class()
        #     paginated_data = paginator.paginate_queryset(data, request)
        #     return paginator.get_paginated_response(paginated_data)
        # return Response(data)

    def create(self, request, *args, **kwargs):
        """用户对壁纸的操作，如收藏、下载、评分等。"""
        user = request.user
        wall_id = request.data.get("wall_id")

        if not wall_id:
            return Response({"error": "缺少wall_id参数"}, status=status.HTTP_400_BAD_REQUEST)

        obj = {
            "user_id": user.id,
            "wall_id": wall_id,
            "action_key": request.data.get("action_key"),
            "action_value": request.data.get("action_value"),
        }

        # 如果多张表同时更新数据，需要开启事务保存
        with transaction.atomic():
            # 使用 user/wall 创建或查找记录
            user_action, created = UserActions.objects.update_or_create(
                user_id=user.id, wall_id=wall_id, action_key=request.data.get("action_key"), defaults=obj
            )

            # 如果评分被更新，重新计算该壁纸的平均分并保存。可能存在并发更新问题或者性能问题，每晚定时执行更新
            # if "pic_score" in update_payload:
            #     avg = (
            #         UserActions.objects.filter(wall_id=wall_id, pic_score__isnull=False).aggregate(avg=Avg("pic_score")).get("avg")
            #     )
            #     Wall.objects.filter(pk=wall_id).update(score=avg)

        return Response(
            UserActionsSerializer(user_action).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
