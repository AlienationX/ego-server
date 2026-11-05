from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image
from tqdm import tqdm
from wallpaper.management.commands.utils import generate_thumbs
from wallpaper.models import Wall

# python manage.py bulk_generate_thumbs --wall-id 123


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
            file = Path(settings.MEDIA_ROOT, "wallpaper", wall.picurl)
            # 计算缩略图目标目录，保持分类子目录层级结构一致
            thumb_dir = Path(str(file.parent).replace("/wallpaper/pics", "/wallpaper/thumbs", 1))
            # 确保 thumbs 对应子目录存在
            thumb_dir.mkdir(parents=True, exist_ok=True)

            # 生成 small 缩略图
            output_file = thumb_dir / f"{file.stem}_small.webp"
            generate_thumbs(file, max_size=(520, 520), output_file=output_file)
            # 生成 medium 缩略图
            output_file = thumb_dir / f"{file.stem}_medium.webp"
            generate_thumbs(file, max_size=(1024, 1024), output_file=output_file)
            # 生成 large 缩略图
            output_file = thumb_dir / f"{file.stem}_large.webp"
            generate_thumbs(file, max_size=(2560, 2560), output_file=output_file)

        self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 成功生成 {len(walls)} 条壁纸 的缩略图"))
