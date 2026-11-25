import logging
import random
import secrets
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Board, BoardWall, Classify, UserAutoRotateConfig, Wall, Versions
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import UserAutoRotateConfigSerializer, WallSerializer

logger = logging.getLogger(__name__)


def is_pay_enabled(request=None):
    """检查系统后台是否开启了支付与VIP验证，若关闭则全员放行"""
    try:
        channel = None
        if request:
            channel = (
                request.headers.get("Channel")
                or request.META.get("HTTP_CHANNEL")
                or (hasattr(request, "query_params") and request.query_params.get("channel"))
            )
        ver = None
        if channel:
            ver = Versions.objects.filter(channel=channel).first()
        if not ver:
            ver = Versions.objects.filter(channel="default").first() or Versions.objects.first()

        if ver is not None and ver.pay_enabled is False:
            return False
    except Exception as e:
        logger.warning(f"Failed to check pay_enabled: {e}")
    return True


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
            new_enabled = bool(data["enabled"])
            if new_enabled and is_pay_enabled(request):
                is_vip = False
                if hasattr(user, "profile") and user.profile.vip_expire_time:
                    is_vip = user.profile.vip_expire_time > timezone.now()
                if not is_vip:
                    return Response(
                        {"code": 403, "error": "自动更换壁纸为 VIP 专享特权，请先开通会员"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            config.enabled = new_enabled
        if "mode" in data and data["mode"] in ["bing", "board", "theme"]:
            config.mode = data["mode"]
        if "light_wallpaper" in data:
            config.light_wallpaper = data["light_wallpaper"]
        if "dark_wallpaper" in data:
            config.dark_wallpaper = data["dark_wallpaper"]
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
        专供 iOS 快捷指令 / Android 原生后台 Worker / 页面测试 自动拉取壁纸数据
        URL: GET /api/wallpaper/rotate/feed/?token=xxx&mode=bing/theme/board&theme=light/dark&board_id=xxx
        """
        token = request.query_params.get("token")
        requested_mode = request.query_params.get("mode")  # 客户端显式指定的模式
        req_theme = request.query_params.get("theme")      # "light" 或 "dark"
        req_board_id = request.query_params.get("board_id")

        config = None
        user = None

        if token:
            config = (
                UserAutoRotateConfig.objects.filter(rotate_token=token)
                .select_related("board", "user")
                .first()
            )
            if config:
                user = config.user
                if is_pay_enabled(request):
                    is_vip = False
                    if user and hasattr(user, "profile") and user.profile.vip_expire_time:
                        is_vip = user.profile.vip_expire_time > timezone.now()

                    if not is_vip:
                        if config.enabled:
                            config.enabled = False
                            config.save(update_fields=["enabled"])
                        return Response({
                            "code": 403,
                            "error": "VIP会员已到期，自动更换壁纸已暂停",
                            "vip_expired": True,
                        }, status=status.HTTP_403_FORBIDDEN)

        # 决定生效模式：优先使用客户端请求显式传入的 mode，未传入时使用 config.mode，最终兜底 "bing"
        effective_mode = requested_mode or (config.mode if config else "bing")
        if effective_mode not in ["bing", "theme", "board"]:
            effective_mode = "bing"

        wall = None
        custom_wall_data = None
        board_name = ""
        target = config.target if config else "lock"

        # ════════════════════════════════════════════════════════════════
        # 1. 深浅双色自适应模式 (theme)
        # ════════════════════════════════════════════════════════════════
        if effective_mode == "theme":
            target_theme = req_theme if req_theme in ["light", "dark"] else "light"
            wall_dict = None
            if config:
                wall_dict = config.dark_wallpaper if target_theme == "dark" else config.light_wallpaper

            if wall_dict and isinstance(wall_dict, dict):
                custom_wall_data = wall_dict
                wall_id = wall_dict.get("id")
                if wall_id and isinstance(wall_id, int):
                    wall = Wall.objects.filter(id=wall_id, is_active=True).first()

            if custom_wall_data:
                img_url = custom_wall_data.get("url") or custom_wall_data.get("thumb") or ""
                if img_url and not img_url.startswith("http") and not img_url.startswith("file://"):
                    img_url = f"{settings.NGINX_MEDIA_URL}/wallpaper/{img_url.lstrip('/')}"

                if config:
                    config.last_rotated_at = timezone.now()
                    config.save(update_fields=["last_rotated_at"])

                return Response({
                    "id": custom_wall_data.get("id") or (wall.id if wall else 0),
                    "title": custom_wall_data.get("title") or ("深色模式壁纸" if target_theme == "dark" else "浅色模式壁纸"),
                    "image_url": img_url,
                    "mode": "theme",
                    "theme": target_theme,
                    "board_name": "",
                    "target": target,
                    "wall": custom_wall_data,
                    "rotated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            else:
                return Response({
                    "error": f"未设置{'深色' if target_theme == 'dark' else '浅色'}自适应壁纸，请先在 App 中选定",
                    "mode": "theme",
                    "theme": target_theme,
                }, status=status.HTTP_404_NOT_FOUND)

        # ════════════════════════════════════════════════════════════════
        # 2. 画板自定义轮播模式 (board)
        # ════════════════════════════════════════════════════════════════
        elif effective_mode == "board":
            target_board = None
            if req_board_id:
                target_board = Board.objects.filter(id=req_board_id).first()
            if not target_board and config and config.board:
                target_board = config.board

            if not target_board:
                return Response({"error": "请先选择要轮播的画板", "mode": "board"}, status=status.HTTP_404_NOT_FOUND)

            board_name = target_board.name
            board_wall_items = list(
                BoardWall.objects.filter(board=target_board).order_by("id").select_related("wall")
            )
            if not board_wall_items:
                return Response({
                    "error": f"画板「{board_name}」内暂无壁纸，请先添加壁纸到该画板",
                    "mode": "board",
                    "board_name": board_name,
                }, status=status.HTTP_404_NOT_FOUND)

            strategy = config.strategy if config else "random"
            if strategy == "random":
                selected_bw = random.choice(board_wall_items)
            else:
                # 顺序循环
                last_wall_id = config.last_wall_id if config else None
                next_idx = 0
                if last_wall_id:
                    wall_ids = [bw.wall_id for bw in board_wall_items]
                    if last_wall_id in wall_ids:
                        curr_idx = wall_ids.index(last_wall_id)
                        next_idx = (curr_idx + 1) % len(board_wall_items)
                selected_bw = board_wall_items[next_idx]

            wall = selected_bw.wall
            if config:
                config.last_wall = wall
                config.last_rotated_at = timezone.now()
                config.save(update_fields=["last_rotated_at", "last_wall"])

        # ════════════════════════════════════════════════════════════════
        # 3. 每日必应最新壁纸模式 (bing)
        # ════════════════════════════════════════════════════════════════
        else:
            # 动态检索必应分类，杜绝写死 classify_id 带来的环境错位
            bing_classify = Classify.objects.filter(name__icontains="必应").first()
            classify_id = bing_classify.id if bing_classify else 30
            wall = (
                Wall.objects.filter(classify_id=classify_id, is_active=True)
                .order_by("-id")
                .first()
            )
            if not wall:
                wall = Wall.objects.filter(is_active=True).order_by("-id").first()

            if config:
                config.last_wall = wall
                config.last_rotated_at = timezone.now()
                config.save(update_fields=["last_rotated_at", "last_wall"])

        if not wall:
            return Response({"error": "暂无可用的精美壁纸"}, status=status.HTTP_404_NOT_FOUND)

        serializer = WallSerializer(wall)
        wall_data = serializer.data
        image_url = wall_data.get("picurl", "")
        if image_url and not image_url.startswith("http"):
            image_url = f"{settings.NGINX_MEDIA_URL}/wallpaper/{image_url.lstrip('/')}"

        wall_title = getattr(wall, "title", "") or getattr(wall, "name", "")
        if not wall_title and hasattr(wall, "description") and wall.description:
            wall_title = wall.description.split("(")[0].strip()

        return Response({
            "id": wall.id,
            "title": wall_title or ("每日最新必应壁纸" if effective_mode == "bing" else "超清壁纸"),
            "image_url": image_url,
            "mode": effective_mode,
            "board_name": board_name,
            "target": target,
            "wall": wall_data,
            "rotated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
