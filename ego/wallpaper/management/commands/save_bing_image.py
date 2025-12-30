import random
from datetime import datetime
from pathlib import Path

import requests
from django.core.management.base import BaseCommand
from wallpaper.management.commands.upload_cos import upload_file_to_cos
from wallpaper.management.commands.upload_s3 import upload_file_to_s3
from wallpaper.management.commands.utils import generate_thumbs, send_dingtalk
from wallpaper.models import Wall

# python manage.py save_bing_image


class Command(BaseCommand):
    help = "下载最近8天的bing壁纸"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="日期")

    def handle(self, *args, **options):
        current_date = options.get("date")

        # step1：下载 image 到本地
        local_bing_path = Path(__file__).parent.parent.parent / "scripts/images/pics/classify_bing/"
        records = self._download_bing_image(local_bing_path)
        new_records = []

        for record in records:
            file_path = local_bing_path / record["file_name"]

            # step2：生成缩略图
            generate_thumbs(file_path)

            # 上传到 s3
            upload_file_to_s3(file_path, s3_prefix="pics/classify_bing/")

            # 上传到 cos
            upload_file_to_cos(file_path, cos_prefix="pics/classify_bing/")

            # step3：上传到数据库

            # 方式1: 创建后再保存
            # wallObj = Wall(
            #     picurl=record["picurl"],
            #     description=record["description"],
            #     tabs=record["tabs"],
            #     score=record["score"],
            #     publisher=record["publisher"],
            #     is_active=record["is_active"],
            #     is_locked=record["is_locked"],
            #     created_at=record["created_at"],
            #     updated_at=record["updated_at"],
            #     classify_id=record["classify_id"]
            # )
            # wallObj.save()

            # 方式2: 直接创建并保存
            # Wall.objects.create(field1="xxx", field2="aaa")

            # 方式3: 不存在则插入数据
            obj, created = Wall.objects.get_or_create(
                picurl=f"pics/classify_bing/{record['file_name']}",
                defaults={
                    "description": f"{record['date']} - {record['title']}: {record['description']}",
                    "tabs": "必应,每日壁纸,风景,Bing,微软",
                    "score": round(random.uniform(4, 5), 1),
                    "publisher": "Bing",
                    "is_active": True,
                    "is_locked": False,
                    # "created_at": datetime.now(),
                    # "updated_at": datetime.now(),
                    "classify_id": 30,
                    "remark": record["image_url"],
                },
            )

            if created:
                new_records.append(record)
                self.stdout.write(self.style.SUCCESS(f"成功导入 {record['file_name']}"))

        self.stdout.write(self.style.SUCCESS(f"成功导入 {len(new_records)} 条数据"))
        send_dingtalk(f"成功导入 {len(new_records)} 条必应壁纸数据")

    def _download_bing_image(self, local_bing_path):
        # 请求API数据: https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN
        # 参数说明
        # format：返回格式，js 表示JSON，xml 表示XML。
        # idx：起始索引（0表示当天，1表示前一天，最多7天前的数据）。
        # n：返回的图片数量（最大值为8）。
        # mkt：区域代码（例如 zh-CN 为中国，en-US 为美国，不同地区可能返回不同图片）(en-US设置无效，和ip有关)。

        # params = {"format": "js", "idx": 0, "n": 8, "mkt": "zh_CN"}
        params = {"format": "js", "idx": 0, "n": 8, "mkt": "zh_CN"}
        api_url = "https://www.bing.com/HPImageArchive.aspx"
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        # data = json.loads(response.text)
        data = response.json()

        records = []
        # 反转列表，顺序下载确保最新的壁纸在最后处理
        for image in reversed(data["images"]):
            file_name = image["enddate"] + "-" + image["title"]
            # 解析并拼接图片URL
            image_url = "https://www.bing.com" + image["url"]
            # image_url = image_url.replace("1920x1080", "UHD")  # 改为超高清分辨率
            image_url = image_url.replace("1920x1080", "1080x1920")  # 改为手机分辨率

            # 下载图片
            image_data = requests.get(image_url).content

            # 检查图片是否存在，如果存在则跳过
            file_path = local_bing_path / f"{file_name}.jpg"
            if file_path.exists():
                print(f"Already exist, skip {file_name}.jpg")
            else:
                with open(file_path, "wb") as f:
                    f.write(image_data)
                print(f"Save {file_name}.jpg")

            # 保存数据
            record = {
                "file_name": f"{file_name}.jpg",
                "date": image["enddate"],
                "title": image["title"],
                "description": image["copyright"],
                "image_url": image_url,
            }
            records.append(record)

        # print(records)
        return records
