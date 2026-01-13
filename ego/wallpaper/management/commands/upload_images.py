import base64
import json
import random
from datetime import datetime
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from wallpaper.management.commands.upload_cos import upload_file_to_cos
from wallpaper.management.commands.upload_s3 import upload_file_to_s3
from wallpaper.management.commands.utils import generate_thumbs, resize_image
from wallpaper.models import Classify, Wall

# python manage.py save_images_with_llm


class Command(BaseCommand):
    help = """
    上传图片到服务器
    """

    def add_arguments(self, parser):
        parser.add_argument("--input-dir", type=str, help="指定需上传图片所在的目录", required=True)

    def handle(self, *args, **options):
        input_dir = options.get("input_dir")
        # if not input_dir:
        #     self.stdout.write(self.style.ERROR("请指定需上传图片所在的目录"))
        #     return

        input_dir = Path(__file__).parent.parent.parent / "scripts/images/pics/classify_bing/"
        ouput_dir = Path(__file__).parent.parent.parent / "scripts/output/"

        self.stdout.write(self.style.SUCCESS(f"成功上传  张图片"))

    def _upload_image(self, file):
        url = "/"
        requests
