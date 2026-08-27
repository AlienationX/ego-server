import logging
import random
import secrets
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Board, BoardWall, UserAutoRotateConfig, Wall
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import UserAutoRotateConfigSerializer, WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(GenericViewSet):
    """
    VIP 自动更换壁纸 (Auto Rotate) API 视图集
    自动注册路由：/api/wallpaper/rotate/
    """
    queryset = UserAutoRotateConfig.objects.all()
    serializer_class = UserAutoRotateConfigSerializer
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    @action(detail=False, methods=["get"])
    def config(self, request):
        """获取当前用户的自动轮播配置"""
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "未登录"}, status=status.HTTP_401_UNAUTHORIZED)

        config, created = UserAutoRotateConfig.objects.get_or_create(user=user)
        if not config.rotate_token:
            config.rotate_token = secrets.token_hex(16)
            config.save(update_fields=["rotate_token"])

        serializer = self.serializer_class(config)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def save_config(self, request):
        """保存当前用户的自动轮播配置 (VIP 专享)"""
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "未登录"}, status=status.HTTP_401_UNAUTHORIZED)

        config, created = UserAutoRotateConfig.objects.get_or_create(user=user)
        if not config.rotate_token:
            config.rotate_token = secrets.token_hex(16)

        data = request.data
        if "enabled" in data:
            config.enabled = bool(data["enabled"])
        if "mode" in data and data["mode"] in ["bing", "board"]:
            config.mode = data["mode"]
        if "board_id" in data:
            board_id = data["board_id"]
            if board_id:
                try:
                    config.board = Board.objects.get(id=board_id, user=user)
                except Board.DoesNotExist:
                    config.board = None
            else:
                config.board = None
        if "target" in data and data["target"] in ["both", "lock", "home"]:
            config.target = data["target"]
        if "frequency" in data:
            config.frequency = data["frequency"]
        if "strategy" in data:
            config.strategy = data["strategy"]
        if "wifi_only" in data:
            config.wifi_only = bool(data["wifi_only"])

        config.save()
        serializer = self.serializer_class(config)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def feed(self, request):
        """
        专供 iOS 快捷指令 / Android 原生后台 Worker 自动拉取下一张壁纸数据
        URL: GET /api/wallpaper/rotate/feed/?token=xxx
        """
        token = request.query_params.get("token")
        mode = request.query_params.get("mode", "bing")
        wall = None

        if token:
            config = (
                UserAutoRotateConfig.objects.filter(rotate_token=token)
                .select_related("board", "user")
                .first()
            )
            if config:
                user = config.user
                is_vip = False
                if user and hasattr(user, "profile") and user.profile.vip_expire_time:
                    is_vip = user.profile.vip_expire_time > timezone.now()

                if not is_vip:
                    return Response({
                        "code": 403,
                        "error": "VIP会员已到期，画板自动轮播已暂停",
                        "vip_expired": True,
                    }, status=status.HTTP_403_FORBIDDEN)

                mode = config.mode
                if config.mode == "board" and config.board:
                    # 从指定画板中选取壁纸
                    board_wall_items = list(
                        BoardWall.objects.filter(board=config.board).order_by("id").select_related("wall")
                    )
                    if board_wall_items:
                        if config.strategy == "random":
                            selected_bw = random.choice(board_wall_items)
                        else:
                            # 顺序循环轮播逻辑：查找上次位置，推进到下一张
                            last_wall_id = config.last_wall_id
                            next_idx = 0
                            if last_wall_id:
                                wall_ids = [bw.wall_id for bw in board_wall_items]
                                if last_wall_id in wall_ids:
                                    curr_idx = wall_ids.index(last_wall_id)
                                    next_idx = (curr_idx + 1) % len(board_wall_items)
                            selected_bw = board_wall_items[next_idx]
                        wall = selected_bw.wall
                        config.last_wall = wall

                # 更新最近切换时间与上次壁纸
                config.last_rotated_at = timezone.now()
                config.save(update_fields=["last_rotated_at", "last_wall"])

        # 若未选定壁纸，默认降级拉取最新必应壁纸
        if not wall:
            wall = (
                Wall.objects.filter(classify_id=30, is_active=True)
                .order_by("-id")
                .first()
            )
        if not wall:
            wall = Wall.objects.filter(is_active=True).order_by("-id").first()

        if not wall:
            return Response({"error": "暂无可用壁纸"}, status=status.HTTP_404_NOT_FOUND)

        serializer = WallSerializer(wall)
        wall_data = serializer.data
        image_url = wall_data.get("picurl", "")
        if image_url and not image_url.startswith("http"):
            image_url = f"https://api.wp.ego8.space/static/wallpaper/media/{image_url.lstrip('/')}"

        board_name = config.board.name if (config and config.board) else ""
        target = config.target if config else "lock"

        return Response({
            "id": wall.id,
            "title": getattr(wall, "title", "") or getattr(wall, "name", ""),
            "image_url": image_url,
            "mode": mode,
            "board_name": board_name,
            "target": target,
            "wall": wall_data,
            "rotated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
