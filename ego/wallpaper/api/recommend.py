import logging

from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Recommendations, UserActions, Wall, WallSimilarities
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(CreateModelMixin, GenericViewSet):
    queryset = Wall.objects.filter(is_active=True)
    serializer_class = WallSerializer
    permission_classes = [HasAccessKey]
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def create(self, request, *args, **kwargs):
        """获取壁纸混合推荐列表（POST，exclude_ids 放 body 避免 URL 超长）"""
        user = request.user
        device_id = request.headers.get("Device-Id")

        # exclude_ids 支持列表（前端传数组）或逗号分隔字符串（兼容旧调用）
        raw_exclude = request.data.get("exclude_ids", [])
        if isinstance(raw_exclude, str):
            exclude_ids = [int(i) for i in raw_exclude.split(",") if i.strip().isdigit()]
        elif isinstance(raw_exclude, list):
            exclude_ids = [int(i) for i in raw_exclude if str(i).isdigit()]
        else:
            exclude_ids = []

        # 权重设置
        ALPHA = 0.2  # 协同过滤权重 (来自预计算表)
        BETA = 0.4  # 内容相似度权重
        GAMMA = 0.4  # 热度趋势权重

        interacted_wall_ids = set()

        # 1. 获取用户近期正向交互过的壁纸 ID（点赞、收藏、下载）
        if user.is_authenticated:
            actions = UserActions.objects.filter(user=user, action_value__gt=0).order_by("-updated_at")[:20]
            interacted_wall_ids = set(actions.values_list("wall_id", flat=True))
        elif device_id:
            actions = UserActions.objects.filter(device_id=device_id, action_value__gt=0).order_by("-updated_at")[:20]
            interacted_wall_ids = set(actions.values_list("wall_id", flat=True))

        wall_scores = {}

        # 2. 预计算协同过滤召回 (CF Recall)
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
            similarities = (
                WallSimilarities.objects.filter(source_wall_id__in=interacted_wall_ids)
                .exclude(target_wall_id__in=exclude_ids)
                .order_by("-similarity")[:50]
            )
            for sim in similarities:
                target_id = sim.target_wall_id
                if target_id not in interacted_wall_ids:
                    wall_scores[target_id] = wall_scores.get(target_id, 0) + (sim.similarity or 0) * BETA

        # 4. 热门召回 (Hot Recall)，补充召回池
        # 召回数量随 exclude_ids 动态扩展，防止用户翻多页后召回池枯竭
        # 基础 100 条 + 已排除数量，上限 500 避免全表扫描
        hot_limit = min(max(100, len(exclude_ids) + 50), 500)
        hot_walls = Wall.objects.filter(is_active=True).exclude(id__in=exclude_ids).order_by("-normalized_trends")[:hot_limit]
        for wall in hot_walls:
            if wall.id not in interacted_wall_ids:
                wall_scores[wall.id] = wall_scores.get(wall.id, 0) + (wall.normalized_trends or 0) * GAMMA

        # 5. 按分数降序排列
        sorted_wall_ids = sorted(wall_scores.keys(), key=lambda k: wall_scores[k], reverse=True)

        # 6. 分页返回
        page = self.paginate_queryset(sorted_wall_ids)
        if page is not None:
            walls = Wall.objects.filter(id__in=page).select_related("classify")
            walls_dict = {wall.id: wall for wall in walls}
            ordered_walls = [walls_dict[wid] for wid in page if wid in walls_dict]
            serializer = self.get_serializer(ordered_walls, many=True)
            return self.get_paginated_response(serializer.data)

        # 未开启分页时兜底
        top_ids = sorted_wall_ids[:50]
        walls = Wall.objects.filter(id__in=top_ids).select_related("classify")
        walls_dict = {wall.id: wall for wall in walls}
        ordered_walls = [walls_dict[wid] for wid in top_ids if wid in walls_dict]
        serializer = self.get_serializer(ordered_walls, many=True)
        return Response(serializer.data)
