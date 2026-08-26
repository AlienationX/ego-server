import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..models import Board, BoardWall, Wall
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import BoardSerializer, WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(ModelViewSet):
    """
    用户画板 (Boards) API 视图集
    默认 5 个 RESTful 标准方法：
    1. list: 获取当前用户的所有画板 (GET /api/wallpaper/board/)
    2. create: 创建新画板 (POST /api/wallpaper/board/)
    3. retrieve: 获取单个画板详情 (GET /api/wallpaper/board/{id}/)
    4. update / partial_update: 更新画板信息 (PUT / PATCH /api/wallpaper/board/{id}/)
    5. destroy: 删除画板 (DELETE /api/wallpaper/board/{id}/)

    自定义 actions：
    - walls: GET /api/wallpaper/board/{id}/walls/ 获取画板内的壁纸列表
    - add_walls: POST /api/wallpaper/board/{id}/add_walls/ 批量/单个添加壁纸到画板
    - del_walls: POST /api/wallpaper/board/{id}/del_walls/ 批量/单个从画板移除壁纸
    - set_rotate: POST /api/wallpaper/board/{id}/set_rotate/ 设为/取消自动轮播源
    """
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [HasAccessKey]
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_authenticated", False):
            return self.queryset.filter(user=user).order_by("-updated_at")
        return self.queryset.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        创建新画板：
        支持传入 name, description, 以及可选的 wall_id / wall_ids (创建后立即存入壁纸)
        """
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return Response({"error": "未登录"}, status=status.HTTP_401_UNAUTHORIZED)

        name = request.data.get("name", "").strip()
        if not name:
            return Response({"error": "画板名称不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        description = request.data.get("description", "").strip()
        board = Board.objects.create(user=user, name=name, description=description)

        # 若同时传了壁纸 ID，一并关联存入
        wall_id = request.data.get("wall_id")
        wall_ids = request.data.get("wall_ids")
        target_wall_ids = []
        if wall_ids and isinstance(wall_ids, list):
            target_wall_ids = wall_ids
        elif wall_id:
            target_wall_ids = [wall_id]

        if target_wall_ids:
            for wid in target_wall_ids:
                try:
                    wall = Wall.objects.get(id=wid)
                    BoardWall.objects.get_or_create(board=board, wall=wall)
                except Wall.DoesNotExist:
                    continue
            board.save(update_fields=["updated_at"])

        serializer = self.serializer_class(board)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def walls(self, request, pk=None):
        """获取指定画板内的壁纸列表（支持分页）"""
        board = self.get_object()
        board_walls = (
            BoardWall.objects.filter(board=board)
            .select_related("wall")
            .order_by("-added_at")
        )
        page = self.paginate_queryset(board_walls)
        if page is not None:
            walls = [bw.wall for bw in page if bw.wall]
            serializer = WallSerializer(walls, many=True)
            return self.get_paginated_response(serializer.data)

        walls = [bw.wall for bw in board_walls if bw.wall]
        serializer = WallSerializer(walls, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_walls(self, request, pk=None):
        """批量/单个添加壁纸到指定画板"""
        board = self.get_object()
        wall_id = request.data.get("wall_id")
        wall_ids = request.data.get("wall_ids")

        target_wall_ids = []
        if wall_ids and isinstance(wall_ids, list):
            target_wall_ids = wall_ids
        elif wall_id:
            target_wall_ids = [wall_id]

        if not target_wall_ids:
            return Response({"error": "请提供壁纸 ID"}, status=status.HTTP_400_BAD_REQUEST)

        for wid in target_wall_ids:
            try:
                wall = Wall.objects.get(id=wid)
                BoardWall.objects.get_or_create(board=board, wall=wall)
            except Wall.DoesNotExist:
                continue

        board.save(update_fields=["updated_at"])
        return Response(
            {"message": "已添加至画板", "items_count": board.items_count},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def del_walls(self, request, pk=None):
        """批量/单个从画板中移除壁纸"""
        board = self.get_object()
        wall_id = request.data.get("wall_id") or request.query_params.get("wall_id")
        wall_ids = request.data.get("wall_ids")

        target_wall_ids = []
        if wall_ids and isinstance(wall_ids, list):
            target_wall_ids = wall_ids
        elif wall_id:
            target_wall_ids = [wall_id]

        if not target_wall_ids:
            return Response({"error": "请提供要移除的壁纸 ID"}, status=status.HTTP_400_BAD_REQUEST)

        BoardWall.objects.filter(board=board, wall_id__in=target_wall_ids).delete()
        board.save(update_fields=["updated_at"])
        return Response(
            {"message": "已从画板移除壁纸", "items_count": board.items_count},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def set_rotate(self, request, pk=None):
        """设为/取消自动轮播画板"""
        board = self.get_object()
        # 取消其他画板的轮播状态
        Board.objects.filter(user=request.user).exclude(id=board.id).update(is_auto_rotate=False)
        board.is_auto_rotate = not board.is_auto_rotate
        board.save(update_fields=["is_auto_rotate", "updated_at"])

        return Response({"id": board.id, "is_auto_rotate": board.is_auto_rotate})
