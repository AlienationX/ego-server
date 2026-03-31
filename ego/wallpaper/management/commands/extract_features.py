from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from tqdm import tqdm
from utils.feature_extractor import FeatureStorage, ImageFeatureExtractor
from wallpaper.models import Wall, WallFeatures

# python manage.py extract_features --wall-id 123


class Command(BaseCommand):
    help = "批量提取壁纸的特征及特征向量存储"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")
        parser.add_argument("--force", action="store_true", help="强制提取特征")  # 布尔值，还有store_false

    def handle(self, *args, **options):
        wall_id = options.get("wall_id")
        force = options.get("force", False)  # 获取 force 参数

        walls = Wall.objects.select_related("wall_features")
        if wall_id:
            # 指定壁纸ID，不管是否已有特征向量，都提取
            walls = walls.filter(id=wall_id)
        elif not force:
            # 不强制提取，且未指定壁纸ID，只提取没有特征向量的壁纸
            walls = walls.exclude(wall_features__isnull=False, wall_features__feature_vector__isnull=False)

        # for wall in walls:
        #     # 遍历所有属性
        #     print(f"\n=== 壁纸id={wall.id} ===")
        #     print(dir(wall))
        #     for attr in dir(wall):
        #         if not attr.startswith("_"):
        #             try:
        #                 value = getattr(wall, attr)
        #                 if not callable(value):
        #                     print(f"  {attr}: {value}")
        #             except Exception as e:
        #                 print(f"  {attr}: <Error: {e}>")

        extractor = ImageFeatureExtractor()

        # for wall in tqdm(walls, desc="提取特征"):
        for wall in walls:
            # 提取特征向量
            feature_vector_list, feature_dim, model_name = extractor.extract_features(Path(settings.MEDIA_ROOT, wall.picurl))
            feature_vector = FeatureStorage.vector_to_blob(feature_vector_list)
            # 没有创建，存在更新
            wall_features, created = WallFeatures.objects.update_or_create(
                wall=wall, defaults={"feature_vector": feature_vector, "feature_dim": feature_dim, "model_name": model_name}
            )
            self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 成功提取 壁纸id={wall.id} 的特征"))

        self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 成功提取 {len(walls)} 条壁纸 的特征"))
