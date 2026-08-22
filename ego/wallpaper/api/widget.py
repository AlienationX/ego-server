import hashlib
import logging
import random
from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Wall
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import WallSerializer

logger = logging.getLogger(__name__)

WEEKDAYS_ZH = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DAILY_QUOTES = [
    {
        "quote": "生活明朗，万物可爱，人间值得，未来可期。",
        "author": "汪曾祺",
        "quote_en": "Keep life bright and lovely; the world is worthy of your love.",
    },
    {
        "quote": "愿你眼中有光，心中有爱，一路春暖花开。",
        "author": "席慕蓉",
        "quote_en": "May your eyes hold light, your heart hold love, and blossoms greet you along the way.",
    },
    {
        "quote": "向阳而生，逐光而行，不负每一次热爱。",
        "author": "林清玄",
        "quote_en": "Grow towards the sun, chase the light, cherish every passion.",
    },
    {
        "quote": "山海自有归期，风雨自有相逢，未来皆是坦途。",
        "author": "余光中",
        "quote_en": "Mountains and seas meet in time; the journey ahead is wide and bright.",
    },
    {
        "quote": "保持热爱，奔赴山海，星光不问赶路人。",
        "author": "佚名",
        "quote_en": "Stay passionate, chase the horizon, stars always shine on travelers.",
    },
    {
        "quote": "心之所向，素履以往；生如逆旅，一苇以航。",
        "author": "七堇年",
        "quote_en": "Go where your heart points; life is a journey, sail across with courage.",
    },
    {
        "quote": "万物皆有裂痕，那是光照进来的地方。",
        "author": "莱昂纳德·科恩",
        "quote_en": "There is a crack in everything, that's how the light gets in.",
    },
    {
        "quote": "静守时光，以待流年，漫步于诗意与画卷之间。",
        "author": "白落梅",
        "quote_en": "Cherish the quiet moments, stroll between poetry and picturesque landscapes.",
    },
    {
        "quote": "每一次日落，都是星辰大海的开篇序章。",
        "author": "史铁生",
        "quote_en": "Every sunset is a prelude to the vast sea of stars.",
    },
]


class ApiModelView(GenericViewSet):
    """
    桌面小组件 (AppWidget / HarmonyOS Card) 专用高性能接口
    """

    queryset = Wall.objects.filter(is_active=True)
    serializer_class = WallSerializer
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    def _build_date_info(self, now=None):
        if now is None:
            now = timezone.localtime(timezone.now())

        weekday_idx = now.weekday()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "year": str(now.year),
            "month": f"{now.month:02d}",
            "day": f"{now.day:02d}",
            "time": now.strftime("%H:%M"),
            "weekday": WEEKDAYS_ZH[weekday_idx],
            "weekday_en": WEEKDAYS_EN[weekday_idx],
        }

    def _get_daily_quote(self, seed_str):
        seed_hash = hashlib.md5(f"widget_quote_{seed_str}".encode()).hexdigest()
        seed_int = int(seed_hash[:8], 16)
        rng = random.Random(seed_int)
        return rng.choice(DAILY_QUOTES)

    def _format_widget_response(self, wall, now=None):
        if now is None:
            now = timezone.localtime(timezone.now())

        date_str = now.strftime("%Y-%m-%d")
        date_info = self._build_date_info(now)
        quote_info = self._get_daily_quote(date_str)

        wall_serializer = WallSerializer(wall, context={"request": self.request})
        wall_data = wall_serializer.data

        # 小组件需要最精炼、直观、高可用格式
        return {
            "id": wall.id,
            "title": wall_data.get("title") or "每日精选灵感",
            "description": wall_data.get("description") or quote_info["quote"],
            "quote": quote_info["quote"],
            "quote_author": quote_info["author"],
            "quote_en": quote_info["quote_en"],
            "picurl": wall_data.get("picurl") or "",
            "small_picurl": wall_data.get("smallPicurl") or wall_data.get("picurl") or "",
            "score": wall_data.get("score") or 9.5,
            "classify_name": wall_data.get("classify_name") or "精选",
            "date_info": date_info,
            "scheme_url": f"egowall://preview?id={wall.id}",
            "update_interval_minutes": 360,  # 建议小组件 6 小时刷新一次
        }

    def list(self, request, *args, **kwargs):
        """默认调用 daily 每日精选小组件接口"""
        return self.daily(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def daily(self, request):
        """
        获取每日精选小组件数据（当日内所有用户算出的精选壁纸与日签恒定一致）
        """
        now = timezone.localtime(timezone.now())
        date_str = now.strftime("%Y-%m-%d")

        # 优先选取高分且激活的壁纸
        walls = list(Wall.objects.filter(is_active=True, score__gte=7.5).order_by("-score", "-created_at")[:100])
        if not walls:
            walls = list(Wall.objects.filter(is_active=True)[:50])

        if not walls:
            return Response({"error": "暂无可供小组件展示的壁纸"}, status=status.HTTP_404_NOT_FOUND)

        # 每日确定性随机种子
        seed_hash = hashlib.md5(f"widget_daily_wall_{date_str}".encode()).hexdigest()
        seed_int = int(seed_hash[:8], 16)
        rng = random.Random(seed_int)
        selected_wall = rng.choice(walls)

        return Response(self._format_widget_response(selected_wall, now))

    @action(detail=False, methods=["get"])
    def random(self, request):
        """
        桌面小组件点击“换一张”快捷刷新接口（随机获取一张高分精选壁纸）
        """
        now = timezone.localtime(timezone.now())
        exclude_id = request.query_params.get("exclude_id")

        queryset = Wall.objects.filter(is_active=True)
        if exclude_id and str(exclude_id).isdigit():
            queryset = queryset.exclude(id=int(exclude_id))

        # 随机从前 200 张高分壁纸中抽取
        high_score_walls = list(queryset.order_by("-score", "-created_at")[:200])
        if not high_score_walls:
            high_score_walls = list(queryset[:50])

        if not high_score_walls:
            return Response({"error": "暂无可供小组件展示的壁纸"}, status=status.HTTP_404_NOT_FOUND)

        selected_wall = random.choice(high_score_walls)
        return Response(self._format_widget_response(selected_wall, now))
