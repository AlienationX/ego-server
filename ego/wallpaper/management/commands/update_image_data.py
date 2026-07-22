from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from tqdm import tqdm
from loguru import logger
from utils.compare_image import get_file_md5, get_file_shape, get_image_content_hash
from wallpaper.models import Wall

# python manage.py update_image_data --wall-id 123


class Command(BaseCommand):
    help = "批量更新壁纸相关数据字段， md5_hash、content_hash、width、height、file_size"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")
        parser.add_argument("--force", action="store_true", help="强制提取特征与更新数据")

    def handle(self, *args, **options):
        wall_id = options.get("wall_id")
        force = options.get("force")

        if wall_id:
            walls = [Wall.objects.get(id=wall_id)]
        elif not force:
            walls = Wall.objects.filter(
                Q(md5_hash__isnull=True)
                | Q(content_hash__isnull=True)
                | Q(width__isnull=True)
                | Q(height__isnull=True)
                | Q(file_size__isnull=True)
            )
        else:
            walls = Wall.objects.all()

        updated_count = 0
        for wall in tqdm(walls, desc="更新壁纸数据"):
            img_path = Path(settings.MEDIA_ROOT, "wallpaper", wall.picurl)
            if not img_path.exists():
                logger.error(f"wall id:{wall.id}, 图片不存在: {img_path}")
                continue

            try:
                wall.md5_hash = get_file_md5(img_path)
                wall.content_hash = get_image_content_hash(img_path)
                wall.width, wall.height = get_file_shape(img_path)
                wall.file_size = img_path.stat().st_size
                wall.save(update_fields=["md5_hash", "content_hash", "width", "height", "file_size"])
                updated_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"更新壁纸 {wall.id} 失败: {e}"))

        self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 成功更新 {updated_count} 条壁纸 的数据字段"))
