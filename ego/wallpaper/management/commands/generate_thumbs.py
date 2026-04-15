from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from tqdm import tqdm
from wallpaper.management.commands.utils import generate_thumbs
from wallpaper.models import Wall

# python manage.py generate_thumbs --wall-id 123


class Command(BaseCommand):
    help = "批量生成壁纸的缩略图"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")

    def handle(self, *args, **options):
        wall_id = options.get("wall_id")

        walls = Wall.objects.all()
        if wall_id:
            walls = walls.filter(id=wall_id)

        for wall in tqdm(walls, desc="生成缩略图"):
            file = Path(settings.MEDIA_ROOT, wall.picurl)
            # 生成 small 缩略图
            output_file = file.with_name(f"{file.stem}_small.webp")
            generate_thumbs(file, max_size=(520, 520), output_file=output_file)
            # 生成 medium 缩略图
            output_file = file.with_name(f"{file.stem}_medium.webp")
            generate_thumbs(file, max_size=(1024, 1024), output_file=output_file)

        self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 成功生成 {len(walls)} 条壁纸 的缩略图"))
