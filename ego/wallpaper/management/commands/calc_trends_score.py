from datetime import datetime

import numpy as np
from django.core.management.base import BaseCommand
from django.db.models import Q
from loguru import logger
from tqdm import tqdm
from utils.feature_extractor import FeatureStorage
from wallpaper.models import Wall

# python manage.py calc_trends_score --wall-id 123


class Command(BaseCommand):
    help = "预计算壁纸的趋势分数"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")
        parser.add_argument("--force", action="store_true", help="强制重新计算所有壁纸")  # 布尔值，还有store_false

    def handle(self, *args, **options):
        wall_id = options.get("wall_id")
        force = options.get("force", False)

        start_time = datetime.now()

        if wall_id:
            # 计算指定壁纸的 TopN 相似度
            walls = [Wall.objects.get(id=wall_id)]
        elif not force:
            walls = Wall.objects.filter(Q(trends__isnull=True) | Q(trends=0))
        else:
            # 强制重新计算所有壁纸的趋势分数
            walls = Wall.objects.all()

        if not walls:
            logger.warning("没有找到需要计算的壁纸特征向量")
            return

        # 计算趋势分数
        logger.info(f"共 {len(walls)} 张 壁纸")
        for wall in tqdm(walls, desc=f"{datetime.now()} 正在计算趋势分数"):
            # calc_trends_score returns (trends, normalized_trends)
            trends, normalized_trends = wall.calc_trends_score(save=False)
            wall.trends = trends
            wall.normalized_trends = normalized_trends

        # 批量更新数据库
        Wall.objects.bulk_update(
            walls,
            fields=["trends", "normalized_trends"],
            batch_size=1000,
        )
        self.stdout.write(self.style.SUCCESS(f"{datetime.now()}: 已更新 {len(walls)} 条记录。"))
