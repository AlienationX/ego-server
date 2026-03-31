from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from utils.compare_image import get_file_md5, get_image_content_hash
from wallpaper.models import Wall

# python manage.py update_image_hash --wall-id 123


class Command(BaseCommand):
    help = "批量更新壁纸的 md5_hash 和 content_hash 字段"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")

    def handle(self, *args, **options):
        wall_id = options.get("wall_id")

        walls = [Wall.objects.get(id=wall_id)] if wall_id else Wall.objects.all()

        for wall in walls:
            # 更新哈希值
            wall.md5_hash = get_file_md5(Path(settings.MEDIA_ROOT, wall.picurl))
            wall.content_hash = get_image_content_hash(Path(settings.MEDIA_ROOT, wall.picurl))
            wall.save(update_fields=["md5_hash", "content_hash"])
            self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 成功更新 壁纸id={wall.id} 的哈希值"))

        self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 成功更新 {len(walls)} 条壁纸 的哈希值"))
