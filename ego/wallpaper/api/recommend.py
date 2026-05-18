import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import UserActions, Wall, WallSimilarities
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(ListModelMixin, GenericViewSet):
    queryset = Wall.objects.filter(is_active=True)
    serializer_class = WallSerializer
    permission_classes = [HasAccessKey]
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):
        """获取壁纸混合推荐列表"""
        user = request.user
        device_id = request.headers.get("Device-Id")
        exclude_ids_str = request.query_params.get("exclude_ids", "")

        exclude_ids = []
        if exclude_ids_str:
            exclude_ids = [int(i) for i in exclude_ids_str.split(",") if i.isdigit()]

        # 权重设置
        ALPHA = 0.2  # 协同过滤权重 (来自预计算表)
        BETA = 0.4  # 内容相似度权重
        GAMMA = 0.4  # 热度趋势权重

        interacted_wall_ids = set()

        # 1. 获取用户近期正向交互过的壁纸ID（点赞、收藏、下载）
        if user.is_authenticated:
            actions = UserActions.objects.filter(
                user=user,
                # action_key__in=["view", "like", "favorite", "download", "share", "comment", "rate"],
                action_value__gt=0,
            ).order_by("-updated_at")[:20]
            interacted_wall_ids = set(actions.values_list("wall_id", flat=True))
        elif device_id:
            actions = UserActions.objects.filter(
                device_id=device_id,
                # action_key__in=["view", "download", "share"],
                action_value__gt=0,
            ).order_by("-updated_at")[:20]
            interacted_wall_ids = set(actions.values_list("wall_id", flat=True))

        wall_scores = {}

        # 2. 预计算协同过滤召回 (CF Recall)
        from ..models import Recommendations

        if user.is_authenticated:
            pre_recs = Recommendations.objects.filter(user=user).exclude(wall_id__in=exclude_ids)
        elif device_id:
            pre_recs = Recommendations.objects.filter(device_id=device_id).exclude(wall_id__in=exclude_ids)
        else:
            pre_recs = []

        for rec in pre_recs:
            wall_scores[rec.wall_id] = wall_scores.get(rec.wall_id, 0) + (rec.score or 0) * ALPHA

        # 3. 相似内容召回 (Item-based Recall)
        if interacted_wall_ids:
            # 查找与这些壁纸相似的壁纸
            similarities = (
                WallSimilarities.objects.filter(source_wall_id__in=interacted_wall_ids)
                .exclude(target_wall_id__in=exclude_ids)
                .order_by("-similarity")[:50]
            )

            for sim in similarities:
                target_id = sim.target_wall_id
                if target_id not in interacted_wall_ids:
                    wall_scores[target_id] = wall_scores.get(target_id, 0) + (sim.similarity or 0) * BETA

        # 3. 热门召回 (Hot Recall)
        # 获取最热门的壁纸，补充召回池
        hot_walls = Wall.objects.filter(is_active=True).exclude(id__in=exclude_ids).order_by("-normalized_trends")[:100]

        for wall in hot_walls:
            if wall.id not in interacted_wall_ids:
                trend_score = (wall.normalized_trends or 0) * GAMMA
                wall_scores[wall.id] = wall_scores.get(wall.id, 0) + trend_score

        # 4. 排序和筛选
        # 按分数降序排列
        sorted_wall_ids = sorted(wall_scores.keys(), key=lambda k: wall_scores[k], reverse=True)

        # 获取当前页需要的数据
        # 这里为了配合 DRF 分页，我们可以构造一个有序的 queryset 或者直接手动分页
        page = self.paginate_queryset(sorted_wall_ids)
        if page is not None:
            # 使用 in 查询获取对象，并按照 sorted_wall_ids 重新排序
            walls = Wall.objects.filter(id__in=page)
            # 因为 filter(id__in) 出来的顺序是数据库默认的，我们需要按照 page 的顺序重排
            walls_dict = {wall.id: wall for wall in walls}
            ordered_walls = [walls_dict[wid] for wid in page if wid in walls_dict]

            serializer = self.get_serializer(ordered_walls, many=True)
            return self.get_paginated_response(serializer.data)

        # 如果没有开启分页，限制返回数量
        top_ids = sorted_wall_ids[:50]
        walls = Wall.objects.filter(id__in=top_ids)
        walls_dict = {wall.id: wall for wall in walls}
        ordered_walls = [walls_dict[wid] for wid in top_ids if wid in walls_dict]

        serializer = self.get_serializer(ordered_walls, many=True)
        return Response(serializer.data)
