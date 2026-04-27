import random
from datetime import datetime
from math import ceil
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from loguru import logger
from tqdm import tqdm
from utils.compare_image import get_file_md5, get_file_shape, get_image_content_hash
from wallpaper.management.commands.upload_cos import upload_file_to_cos
from wallpaper.management.commands.upload_s3 import upload_file_to_s3
from wallpaper.management.commands.utils import generate_thumbs, send_dingtalk
from wallpaper.models import Wall

# python manage.py save_bing_history

"""
官方壁纸API：https://services.bingapis.com/ge-apps/api/v2/bwc/hpimages?mkt=zh-cn&theme=bing&defaultBrowser=ME&dhpSetToBing=True&dseSetToBing=True

第三方壁纸API：
获取壁纸数量
https://api.bimg.cc/total?mkt=zh-CN
参数名	类型	是否必要	备注
mkt	    String	否	    地区，默认zh-CN

获取壁纸JSON数据
https://api.bimg.cc/all?page=1&order=asc&limit=30&w=1080&h=1920&mkt=zh-CN
参数名	类型	是否必要	备注
page	Int	    否	    页数，默认1
limit	Int	    否	    每页数据量，默认10（1-20）
w	    Int	    否	    图片宽度，默认1920
h	    Int	    否	    图片高度，默认1080
order	string	否	    排序，默认降序desc，升序asc
mkt	    String	否	    地区，默认zh-CN

// 已知分辨率
resolutions: [
    '1920x1200',
    '1920x1080',
    '1080x1920',
    '1366x768',
    '1280x768',
    '1024x768',
    '800x600',
    '800x480',
    '768x1280',
    '720x1280',
    '640x480',
    '480x800',
    '400x240',
    '320x240',
    '240x320'
]
// 已知国家地区
locations: [
    "zh-CN",
    "en-US",
    "ja-JP",
    "de-DE",
    "en-CA",
    "en-GB",
    "en-IN",
    "fr-FR",
    "it-IT",
]

locations: [
    "zh-CN",
    "en-US",
    "ja-JP",
    "de-DE",
    "en-CA",
    "en-GB",
    "en-IN",
    "fr-FR",
    "it-IT",
]
"""

MKTS = [
    "en-US",  # "United States",
    "en-CA",  # "Canada (English)",
    "it-IT",  # "Italy",
    "es-ES",  # "Spain",
    "fr-FR",  # "France",
    "de-DE",  # "Germany",
    "en-GB",  # "United Kingdom",
    "fr-CA",  # "Canada (French)",
    "en-IN",  # "India",
    "zh-CN",  # "China",
    "ja-JP",  # "Japan",
    "pt-BR",  # "Brazil",
]


class Command(BaseCommand):
    help = "下载Bing必应历史壁纸"

    def add_arguments(self, parser):
        parser.add_argument("--mkt", type=str, default="zh-CN", help=f"地区, 参数值{MKTS}, 默认为zh-CN")

    def handle(self, *args, **options):
        mkt = options.get("mkt")
        if mkt not in MKTS:
            self.stdout.write(self.style.ERROR(f"地区 {mkt} 不存在"))
            return

        mkt_list = []
        if mkt == "all":
            mkt_list = MKTS
        else:
            mkt_list = [mkt]

        # step1：下载 image 到本地
        local_bing_path = Path(settings.MEDIA_ROOT) / "wallpaper/pics/classify_bing/"

        location_records = {}
        for location in mkt_list:
            records = self._downloads(local_bing_path, location)
            location_records[location] = records

        for location, records in location_records.items():
            new_records = []
            for record in records:
                file_path = local_bing_path / record["file_name"]

                # step2：生成缩略图
                # 生成 small 缩略图
                output_file = file_path.with_name(f"{file_path.stem}_small.webp")
                generate_thumbs(file_path, max_size=(520, 520), output_file=output_file)
                # 生成 medium 缩略图
                output_file = file_path.with_name(f"{file_path.stem}_medium.webp")
                generate_thumbs(file_path, max_size=(1024, 1024), output_file=output_file)

                # 上传到 s3
                # upload_file_to_s3(file_path, s3_prefix="pics/classify_bing/")

                # 上传到 cos
                # upload_file_to_cos(file_path, cos_prefix="pics/classify_bing/")

                # step3：上传到数据库
                md5_hash = get_file_md5(file_path)
                content_hash = get_image_content_hash(file_path)
                width, height = get_file_shape(file_path)
                new_record = {
                    **record,
                    "md5_hash": md5_hash,
                    "content_hash": content_hash,
                    "width": width,
                    "height": height,
                }
                new_records.append(new_record)

            # 批量插入
            Wall.objects.bulk_create(
                [
                    Wall(
                        picurl=f"pics/classify_bing/{record['file_name']}",
                        description=f"{record['date']} - {record['title']}: {record['description']}",
                        tabs="必应,每日壁纸,风景,Bing,微软",
                        score=round(random.uniform(4, 5), 1),
                        publisher="Bing",
                        is_active=True,
                        is_locked=False,
                        md5_hash=record["md5_hash"],
                        content_hash=record["content_hash"],
                        created_at=datetime(2026, 1, 1, 0, 0, 0),
                        updated_at=datetime(2026, 1, 1, 0, 0, 0),
                        classify_id=30,
                        remark=f"{record['image_url']},{location}",
                        width=record["width"],
                        height=record["height"],
                    )
                    for record in new_records
                ],
                ignore_conflicts=True,  # 遇到冲突时忽略
                batch_size=1000,
            )

            self.stdout.write(self.style.SUCCESS(f"{location} 成功导入 {len(new_records)} 条数据"))

    def _downloads(self, local_bing_path, mkt):
        limit = 100
        total_url = f"https://api.bimg.cc/total?mkt={mkt}"
        response = requests.get(total_url)
        response.raise_for_status()
        total = response.json()["data"]
        pages = ceil(total / limit)
        logger.info(f"{mkt} Total: {total}, Pages: {pages}")

        batch_records = []
        for page in range(1, pages + 1):
            records = self._download_bing_image(local_bing_path, page=page, limit=limit, mkt=mkt)
            batch_records.extend(records)

        return batch_records

    def _download_bing_image(self, local_bing_path, page=1, limit=30, order="asc", w=1080, h=1920, mkt="zh_CN"):
        params = {"page": page, "limit": limit, "order": order, "w": w, "h": h, "mkt": mkt}
        api_url = "https://api.bimg.cc/all"
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        # data = json.loads(response.text)
        data = response.json()
        images = data["data"]

        records = []
        # 反转列表，顺序下载确保最新的壁纸在最后处理
        for image in tqdm(images, desc=f"Downloading {mkt} page {page}"):
            file_name = image["datetime"] + "-" + image["title"]

            # 下载图片
            image_data = requests.get(image["url"]).content

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
                "date": image["datetime"],
                "title": image["title"],
                "description": image["copyright"],
                "image_url": image["url"],
            }
            records.append(record)

        # print(records)
        return records
