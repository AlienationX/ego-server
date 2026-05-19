from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from tqdm import tqdm
from utils.compare_image import get_file_md5, get_image_content_hash
from wallpaper.models import Wall

# python manage.py update_image_hash --wall-id 123


class Command(BaseCommand):
    help = "批量更新壁纸的 md5_hash 和 content_hash 字段"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")
        parser.add_argument("--force", action="store_true", help="强制提取特征")  # 布尔值，还有store_false

    def handle(self, *args, **options):
        wall_id = options.get("wall_id")
        force = options.get("force")

        if wall_id:
            walls = [Wall.objects.get(id=wall_id)]
        elif not force:
            # 排除 md5_hash 和 content_hash 都不为空的壁纸
            walls = Wall.objects.exclude(md5_hash__isnull=False, content_hash__isnull=False)
        else:
            walls = Wall.objects.all()

        for wall in tqdm(walls, desc="更新壁纸哈希值"):
            # 更新哈希值
            # TODO 一次性更新所有壁纸的哈希值
            wall.md5_hash = get_file_md5(Path(settings.MEDIA_ROOT, "wallpaper", wall.picurl))
            wall.content_hash = get_image_content_hash(Path(settings.MEDIA_ROOT, "wallpaper", wall.picurl))
            wall.save(update_fields=["md5_hash", "content_hash"])

        self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 成功更新 {len(walls)} 条壁纸 的哈希值"))
