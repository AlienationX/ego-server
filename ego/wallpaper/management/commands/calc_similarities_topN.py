from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from utils.feature_extractor import FeatureStorage, ImageFeatureExtractor
from wallpaper.models import Wall, WallFeatures, WallSimilarities

# python manage.py calc_similarities_topN --wall-id 123


class Command(BaseCommand):
    help = "预计算壁纸的TopN相似度"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")
        parser.add_argument("--topN", type=int, default=10, help="TopN相似度")
        parser.add_argument("--force", action="store_true", help="强制重新计算")  # 布尔值，还有store_false

    def handle(self, *args, **options):
        wall_id = options["wall_id"]
        topN = options["topN"]
        force = options["force"]
        # TODO: 实现预计算壁纸的TopN相似度
        # 1. 从数据库中获取壁纸的特征向量
        # 2. 计算所有壁纸的TopN相似度
        # 3. 存储到数据库中
        pass
