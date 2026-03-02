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
    1.生成图片描述，自然柔和的语言，30字以内。description字段的填充，description_en字段的填充
    2.标签生成，tag字段的填充
    3.图片分类，classify字段的填充
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

        records = [
            {"file_name": f.name, "file_path": str(f)}
            for f in input_dir.iterdir()
            if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
        ]
        new_records = []

        for record in records:
            # 去除水印
            # self._remove_watermark()

            # 利用 llm 生成图片相关信息
            info = self._generate_info(record["file_path"])
            record.update(info)
            record["picurl"] = f"{record['pic_path_prefix']}/{record['file_name']}"
            print(record)

            # 重置图片尺寸
            resize_path = resize_image(Path(record["file_path"]), Path(f"{ouput_dir}/{record['picurl']}"))

            # 生成缩略图
            generate_thumbs(resize_path)

            # # 上传到 s3
            upload_file_to_s3(resize_path, s3_prefix=f"{record['pic_path_prefix']}/")

            # 上传到 cos
            upload_file_to_cos(resize_path, cos_prefix=f"{record['pic_path_prefix']}/")

            # 上传到数据库
            # self._upload_to_db()
            obj, created = Wall.objects.get_or_create(
                picurl=record["picurl"],
                defaults={
                    "description": record["description"],
                    "tabs": record["tabs"],
                    "score": round(random.uniform(4, 5), 1),
                    "publisher": record.get("publisher"),
                    "is_active": True,
                    "is_locked": False,
                    # "created_at": datetime.now(),
                    # "updated_at": datetime.now(),
                    "classify_id": record["classify_id"],
                    "remark": None,
                },
            )

            if created:
                new_records.append(record)
                self.stdout.write(self.style.SUCCESS(f"成功导入 {record['file_name']}"))

        self.stdout.write(self.style.SUCCESS(f"成功导入 {len(new_records)} 条数据"))

    def _generate_info(self, img_path):
        with open(img_path, "rb") as img_file:
            img_base = base64.b64encode(img_file.read()).decode("utf-8")

        # exclude 取反 实现 notin 逻辑
        classify_objects = Classify.objects.all().exclude(name__in=("必应每日壁纸", "宝可梦官方壁纸", "宝可梦睡眠"))
        classcfy_name = [obj.name for obj in classify_objects]

        prompt = f"""根据图片内容，回答以下问题：
        1. 用自然柔和的语言，生成图片描述，30字以内
        2. 生成2到5个中文标签（tag），用英文逗号分隔，逗号之间不要有空格
        3. 在以下分类中选择最合适的一个作为图片分类：{", ".join(classcfy_name)}
        请将回答内容以json格式返回，key分别为：description, tabs, classify_name
        """

        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {"Authorization": f"Bearer {settings.DECOUPLE_CONFIG('ZHIPU_API_KEY')}", "Content-Type": "application/json"}
        data = {
            "model": "glm-4.6v",  # glm-4.6v-flash、glm-4.6v 付费
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
                            "text": prompt,
                        },
                    ],
                }
            ],
            # "thinking": {"type": "enabled"},
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))

        content = result["choices"][0]["message"]["content"].strip()
        info = json.loads(content)
        info["tabs"] = info.get("tabs").replace(", ", ",")
        info["pic_path_prefix"] = classify_objects.get(name=info["classify_name"]).pic_path_prefix
        info["classify_id"] = classify_objects.get(name=info["classify_name"]).id

        return info
