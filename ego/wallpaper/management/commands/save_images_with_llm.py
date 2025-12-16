import base64
import json
import random
from datetime import datetime
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from wallpaper.management.commands.utils import generate_thumbs, upload_files_to_s3
from wallpaper.models import Wall

# python manage.py save_images_with_llm


class Command(BaseCommand):
    help = """
    1.生成图片描述，自然柔和的语言，30字以内。description字段的填充，description_en字段的填充
    2.图片分类，classify字段的填充
    3.标签生成，tag字段的填充
    """

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="日期")

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS(f"成功导入  条数据"))

    def _download_bing_image(self, img_path):
        with open(img_path, "rb") as img_file:
            img_base = base64.b64encode(img_file.read()).decode("utf-8")

        prompt = "生成图片描述，自然柔和的语言，30字以内"

        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {"Authorization": f"Bearer {settings.DECOUPLE_CONFIG("ZHIPU_API_KEY")}", "Content-Type": "application/json"}
        data = {
            "model": "glm-4.6v-flash",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                # "url": "https://cloudcovert-1305175928.cos.ap-guangzhou.myqcloud.com/%E5%9B%BE%E7%89%87grounding.PNG"
                                "url": img_base
                            },
                        },
                        {
                            "type": "text",
                            "text": "生成图片描述，自然柔和的语言，30字以内",
                        },
                    ],
                }
            ],
            "thinking": {"type": "enabled"},
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
