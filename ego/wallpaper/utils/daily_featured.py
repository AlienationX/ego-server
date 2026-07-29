import hashlib
import random
from datetime import datetime
from django.utils import timezone
from wallpaper.models import Wall


class DailyFeaturedService:
    """
    每日壁纸限免/体验服务：
    - 每日固定随机 2 张 VIP 壁纸 (access_level=2) 降级为 纯免费 (effective_access_level=0)
    - 每日固定随机 10 张 VIP 壁纸 (access_level=2) 降级为 可看广告/VIP体验 (effective_access_level=1)
    """

    @classmethod
    def get_daily_featured_ids(cls, target_date=None):
        if target_date is None:
            target_date = timezone.now().strftime("%Y-%m-%d")

        # 使用日期字符串作为随机种子，确保当天内全网用户算出的随机结果恒定一致
        seed_hash = hashlib.md5(f"daily_featured_{target_date}".encode("utf-8")).hexdigest()
        seed_int = int(seed_hash[:8], 16)
        rng = random.Random(seed_int)

        # 获取所有 access_level = 2 (VIP专属) 的活跃壁纸 ID
        vip_wall_ids = list(
            Wall.objects.filter(is_active=True, access_level=2).values_list("id", flat=True)
        )

        if not vip_wall_ids:
            return {"daily_free_ids": set(), "daily_ad_ids": set()}

        # 复制并打乱顺序
        shuffled_ids = vip_wall_ids.copy()
        rng.shuffle(shuffled_ids)

        daily_free_ids = set(shuffled_ids[:2])
        daily_ad_ids = set(shuffled_ids[2:12])

        return {
            "daily_free_ids": daily_free_ids,
            "daily_ad_ids": daily_ad_ids,
        }

    @classmethod
    def get_effective_access_level(cls, wall, daily_featured=None):
        """
        计算壁纸针对当日的有效访问级别 (effective_access_level) 与标记
        """
        if daily_featured is None:
            daily_featured = cls.get_daily_featured_ids()

        wall_id = wall.id if hasattr(wall, "id") else wall
        raw_access_level = wall.access_level if hasattr(wall, "access_level") else 0

        is_daily_free = wall_id in daily_featured.get("daily_free_ids", set())
        is_daily_ad = wall_id in daily_featured.get("daily_ad_ids", set())

        if is_daily_free:
            effective_level = 0
        elif is_daily_ad:
            effective_level = 1
        else:
            effective_level = raw_access_level

        # 判定最终解构状态类型
        if effective_level == 0:
            unlock_type = "free"
        elif effective_level == 1:
            unlock_type = "ad_or_vip"
        else:
            unlock_type = "vip_only"

        return {
            "effective_access_level": effective_level,
            "unlock_type": unlock_type,
            "is_daily_free": is_daily_free,
            "is_daily_ad": is_daily_ad,
        }
