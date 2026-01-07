import logging
import random

from django.db import connection, transaction
from django.db.models import Avg, F
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from ..models import Actions, Wall
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import ActionsSerializer

logger = logging.getLogger(__name__)


class ApiModelView(CreateModelMixin, UpdateModelMixin, GenericViewSet):

    queryset = Actions.objects.all()
    serializer_class = ActionsSerializer
    # authentication_classes = [JSONWebTokenAuthentication]  # JWT 认证, 已在settings中全局配置
    permission_classes = [HasAccessKey, IsAuthenticated]
    renderer_classes = [CustomJSONRenderer]

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
                update_payload[key] = request.data.get(key)

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
        """更新用户对壁纸的操作记录，如收藏、下载、评分等。其实应该使用 update 方法，因为是 upsert 操作。"""
        return super().update(request, *args, **kwargs)
