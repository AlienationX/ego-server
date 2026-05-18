from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from loguru import logger
from tqdm import tqdm
from wallpaper.models import Recommendations, UserActions, WallSimilarities


class Command(BaseCommand):
    help = "离线计算用户/设备的预推荐壁纸数据"

    def handle(self, *args, **options):
        # 1. 扫描最近 N 天内有正向交互行为的用户或设备
        days_ago = timezone.now() - timedelta(days=7)
        recent_actions = UserActions.objects.filter(
            action_key__in=["view", "like", "favorite", "download", "comment", "share", "rate"],
            action_value__gt=0,
            updated_at__gte=days_ago,
        )

        user_actions_map = {}
        device_actions_map = {}

        for action in recent_actions:
            if action.user_id:
                if action.user_id not in user_actions_map:
                    user_actions_map[action.user_id] = set()
                user_actions_map[action.user_id].add(action.wall_id)
            elif action.device_id:
                if action.device_id not in device_actions_map:
                    device_actions_map[action.device_id] = set()
                device_actions_map[action.device_id].add(action.wall_id)

        logger.info(f"扫描到 {len(user_actions_map)} 个活跃用户和 {len(device_actions_map)} 个活跃设备。")

        # 2. 为每个对象计算基于物品相似度的推荐分数
        recommendations_to_create = []

        def generate_recommendations_for(identifier_key, identifier_value, interacted_wall_ids):
            similarities = WallSimilarities.objects.filter(source_wall_id__in=interacted_wall_ids).order_by("-similarity")

            score_map = {}
            for sim in similarities:
                target_id = sim.target_wall_id
                if target_id in interacted_wall_ids:
                    continue  # 不推荐已经交互过的壁纸
                score_map[target_id] = score_map.get(target_id, 0) + (sim.similarity or 0)

            # 取 top 50 存入预计算表
            sorted_targets = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:50]

            for target_id, score in sorted_targets:
                rec = Recommendations(
                    wall_id=target_id,
                    score=score,
                    reason="基于您近期的交互计算",
                )
                if identifier_key == "user_id":
                    rec.user_id = identifier_value
                else:
                    rec.device_id = identifier_value
                recommendations_to_create.append(rec)

        for user_id, wall_ids in tqdm(user_actions_map.items(), desc="计算用户推荐"):
            generate_recommendations_for("user_id", user_id, wall_ids)

        for device_id, wall_ids in tqdm(device_actions_map.items(), desc="计算设备推荐"):
            generate_recommendations_for("device_id", device_id, wall_ids)

        # 3. 批量删除旧推荐，并插入新推荐
        if recommendations_to_create:
            with transaction.atomic():
                if user_actions_map:
                    Recommendations.objects.filter(user_id__in=user_actions_map.keys()).delete()
                if device_actions_map:
                    Recommendations.objects.filter(device_id__in=device_actions_map.keys()).delete()

                Recommendations.objects.bulk_create(recommendations_to_create, batch_size=2000)

            logger.info(f"成功生成并插入 {len(recommendations_to_create)} 条预计算推荐记录。")
        else:
            logger.info("近期没有足够的活跃数据来生成新的推荐记录。")

        self.stdout.write(self.style.SUCCESS("离线推荐计算完成！"))
