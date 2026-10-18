import json
import os
import random
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from wallpaper.models import Wall, Classify
from wallpaper.utils.daily_featured import DailyFeaturedService


class PromoCurator:
    """
    推广壁纸选品服务
    - 确保 100% 本地图片真实可用
    - 支持智能随机洗牌与加权抽样 (避免天天发重复壁纸)
    - 支持发布历史记录与自动排重 (排除近 N 天已发壁纸)
    - 支持分类名智能模糊与标签降级匹配 (如输入'AI美女'自动回退按标签匹配)
    """

    @classmethod
    def get_history_file(cls) -> str:
        """获取推广发布历史记录 JSON 文件路径"""
        history_dir = os.path.join(settings.MEDIA_ROOT, "promo_output")
        os.makedirs(history_dir, exist_ok=True)
        return os.path.join(history_dir, "promo_history.json")

    @classmethod
    def load_recent_published_ids(cls, days: int = 14) -> set:
        """读取最近 N 天已发布的壁纸 ID 集合"""
        h_file = cls.get_history_file()
        if not os.path.exists(h_file):
            return set()
        try:
            with open(h_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # data 格式: {"YYYY-MM-DD": [id1, id2, ...]}
            # 按日期倒序取最近 days 天的 ID
            recent_ids = set()
            sorted_dates = sorted(data.keys(), reverse=True)
            for d in sorted_dates[:days]:
                for wid in data[d]:
                    recent_ids.add(wid)
            return recent_ids
        except Exception:
            return set()

    @classmethod
    def record_published_ids(cls, date_str: str, wall_ids: list):
        """记录指定日期发布的壁纸 ID 清单"""
        h_file = cls.get_history_file()
        data = {}
        if os.path.exists(h_file):
            try:
                with open(h_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[date_str] = [int(wid) for wid in wall_ids]
        try:
            with open(h_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def get_local_path(cls, wall: Wall) -> str:
        """获取壁纸本地可用路径，若不存在则返回 None"""
        if not wall.picurl:
            return None

        # 1. 尝试本地 MEDIA_ROOT
        local_path = os.path.join(settings.MEDIA_ROOT, "wallpaper", wall.picurl)
        if os.path.exists(local_path):
            return local_path

        # 2. 尝试本地 static 目录
        static_path = os.path.join(settings.BASE_DIR, "static", "wallpaper", "media", wall.picurl)
        if os.path.exists(static_path):
            return static_path

        return None

    @classmethod
    def is_wall_available_locally(cls, wall: Wall) -> bool:
        return cls.get_local_path(wall) is not None

    @classmethod
    def curate(
        cls,
        mode: str = "daily_free",
        category_name: str = None,
        theme_keyword: str = None,
        target_date: str = None,
        count: int = 17,
        random_sample: bool = True,
        exclude_recent_days: int = 14,
    ) -> list:
        """
        根据策略挑选用于推广的壁纸组合 (确保 100% 本地图片真实可用)
        :param random_sample: 是否开启加权随机抽样，避免每次同一个分类都选相同的壁纸
        :param exclude_recent_days: 排除最近 N 天已发壁纸，0 表示不排除
        """
        curated_items = []
        curated_ids = set()
        featured_info = DailyFeaturedService.get_daily_featured_ids(target_date)

        # 加载最近已发布的壁纸 ID 进行排重
        recent_published_ids = set()
        if exclude_recent_days > 0:
            recent_published_ids = cls.load_recent_published_ids(days=exclude_recent_days)

        def make_item(wall: Wall):
            p = cls.get_local_path(wall)
            if not p:
                return None
            tag_list = [t.strip() for t in (wall.tags or "").split(",") if t.strip()]
            return {
                "wall": wall,
                "id": wall.id,
                "path": p,
                "title": wall.description or f"壁纸 #{wall.id}",
                "description": wall.description or "",
                "classify_name": wall.classify.name if wall.classify else "精选",
                "tags": tag_list,
                "is_daily_free": wall.id in featured_info.get("daily_free_ids", set()),
                "is_daily_ad": wall.id in featured_info.get("daily_ad_ids", set()),
            }

        def pick_from_candidates(candidates_qs, needed: int):
            """从候选 QuerySet 中挑选有效且本地存在的壁纸，支持优先排除近期历史与随机采样"""
            if needed <= 0:
                return

            # 先过滤出本地存在的对象
            valid_pool = []
            for w in candidates_qs:
                if w.id in curated_ids:
                    continue
                if cls.is_wall_available_locally(w):
                    valid_pool.append(w)
                if len(valid_pool) >= needed * 5:  # 收集足够候选池即可
                    break

            # 优先选择未在近期发布的壁纸
            unseen_pool = [w for w in valid_pool if w.id not in recent_published_ids]
            # 如果未发布的壁纸不够，再使用近期已发布的补充
            active_pool = unseen_pool if len(unseen_pool) >= needed else valid_pool

            if random_sample and len(active_pool) > needed:
                # 随机采样，让每天选出的壁纸不重样
                selected = random.sample(active_pool, needed)
            else:
                selected = active_pool[:needed]

            for w in selected:
                item = make_item(w)
                if item:
                    curated_items.append(item)
                    curated_ids.add(w.id)

        # 1. 每日限免模式
        if mode == "daily_free":
            free_ids = list(featured_info.get("daily_free_ids", []))
            ad_ids = list(featured_info.get("daily_ad_ids", []))
            daily_candidates = Wall.objects.filter(id__in=free_ids + ad_ids, is_active=True)
            pick_from_candidates(daily_candidates, count)

        # 2. 分类模式 (支持智能模糊匹配与自动降级为标签检索)
        elif mode == "category" and category_name:
            cls_objs = Classify.objects.filter(name__icontains=category_name)
            if cls_objs.exists():
                candidates = Wall.objects.filter(classify__in=cls_objs, is_active=True).order_by("-trends", "-score")
                pick_from_candidates(candidates, count)
            else:
                # 智能降级：用户传入的可能是标签（如输入了 'AI美女'，实际在标签里）
                print(f"💡 [智能容错] 分类表中未直接找到【{category_name}】，已自动按壁纸标签与描述检索...")
                tag_candidates = Wall.objects.filter(is_active=True).filter(
                    tags__icontains=category_name
                ).order_by("-trends", "-score")
                pick_from_candidates(tag_candidates, count)

        # 3. 主题/标签搜索模式
        elif mode == "theme" and theme_keyword:
            tag_candidates = Wall.objects.filter(is_active=True).filter(
                tags__icontains=theme_keyword
            ).order_by("-trends", "-score")
            pick_from_candidates(tag_candidates, count)

            if len(curated_items) < count:
                desc_candidates = (
                    Wall.objects.filter(is_active=True, description__icontains=theme_keyword)
                    .exclude(id__in=curated_ids)
                    .order_by("-trends")
                )
                pick_from_candidates(desc_candidates, count - len(curated_items))

        # 4. 兜底与填充策略：若所选条件壁纸不足，优先挑选同类或全库高分壁纸
        if len(curated_items) < count:
            remaining = count - len(curated_items)
            fallback_candidates = (
                Wall.objects.filter(is_active=True)
                .exclude(id__in=curated_ids)
                .order_by("-trends", "-score")
            )
            pick_from_candidates(fallback_candidates, remaining)

        return curated_items
