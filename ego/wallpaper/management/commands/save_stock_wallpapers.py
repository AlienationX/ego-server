import os
import random
from pathlib import Path
from time import sleep

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from loguru import logger
from tqdm import tqdm
from utils.compare_image import get_file_md5, get_file_shape, get_image_content_hash
from wallpaper.management.commands.upload_cos import upload_file_to_cos
from wallpaper.management.commands.upload_s3 import upload_file_to_s3
from wallpaper.management.commands.utils import generate_thumbs, send_dingtalk
from wallpaper.models import Classify, Wall

# 命令用法: python manage.py save_stock_wallpapers
"""
STOKiE App 核心解决的是搜集各大手机品牌

数据源：
GitHub: kelecn/Built-in-wallpaper (全球主流厂商官方原生内置壁纸)
结构支持解析：
Apple / Samsung / Xiaomi / OnePlus / Pixel / Huawei / Sony / Nothing / Oppo / Vivo 等
"""

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/kelecn/Built-in-wallpaper/main"
GITHUB_API_BASE = "https://api.github.com/repos/kelecn/Built-in-wallpaper/contents"

# 默认分类 Mapping
BRAND_MAP = {
    "Apple": "苹果官方壁纸",
    "Samsung": "三星官方壁纸",
    "Xiaomi": "小米官方壁纸",
    "OnePlus": "一加官方壁纸",
    "Google": "Pixel官方壁纸",
    "Huawei": "华为官方壁纸",
    "Sony": "索尼官方壁纸",
}


class Command(BaseCommand):
    help = "抓取并入库各大手机厂商官方原生壁纸 (Stock Wallpapers)"

    def add_arguments(self, parser):
        parser.add_argument("--brand", type=str, default="", help="指定抓取的品牌名称，如 Apple, Samsung, Xiaomi")

    def handle(self, *args, **options):
        brand_filter = options.get("brand")
        logger.info(f"开始执行官方原厂壁纸抓取任务, 指定品牌: {brand_filter or '全部'}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/vnd.github.v3+json",
        }

        # 1. 获取品牌目录列表
        try:
            res = requests.get(GITHUB_API_BASE, headers=headers, timeout=15)
            if res.status_code != 200:
                logger.error(f"请求 GitHub API 失败: {res.status_code}")
                return
            brands = [item for item in res.json() if item["type"] == "dir" and not item["name"].startswith(".")]
        except Exception as e:
            logger.error(f"网络异常: {e}")
            return

        for brand_item in brands:
            brand_name = brand_item["name"]
            if brand_filter and brand_name.lower() != brand_filter.lower():
                continue

            classify_name = BRAND_MAP.get(brand_name, f"{brand_name}官方壁纸")
            # classify_obj, _ = Classify.objects.get_or_create(
            #     name=classify_name,
            #     defaults={
            #         "name_en": f"{brand_name} Stock Wallpapers",
            #         "classify_type": 1,
            #         "enable": True,
            #         "picurl": "https://img.ego8.space/wallpaper/default_cover.jpg",
            #     },
            # )

            logger.info(f"正在处理品牌: {brand_name} -> 对应分类: {classify_obj.name}")
            self.fetch_brand_wallpapers(brand_item["url"], brand_name, classify_obj, headers)

    def fetch_brand_wallpapers(self, brand_url, brand_name, classify_obj, headers):
        """递归遍历品牌目录下的机型子目录并抓取图片"""
        try:
            res = requests.get(brand_url, headers=headers, timeout=15)
            if res.status_code != 200:
                return
            items = res.json()
        except Exception as e:
            logger.error(f"获取子目录失败: {e}")
            return

        for item in items:
            if item["type"] == "dir":
                # 机型子目录 (如 iPhone 16 / Galaxy S24)
                model_name = item["name"]
                self.fetch_brand_wallpapers(item["url"], f"{brand_name}/{model_name}", classify_obj, headers)
            elif item["type"] == "file" and item["name"].lower().endswith((".jpg", ".png", ".webp", ".jpeg")):
                # 下载图片并存储
                download_url = item["download_url"]
                file_name = item["name"]

                # 检查 URL 是否已存在
                if Wall.objects.filter(remark=download_url).exists():
                    logger.debug(f"跳过已存在图片: {file_name}")
                    continue

                self.process_and_save_wallpaper(download_url, brand_name, file_name, classify_obj)

    def process_and_save_wallpaper(self, download_url, brand_name, file_name, classify_obj):
        """下载单张图片并完成落盘、COS/S3上传及 Wall 模型存储"""
        try:
            resp = requests.get(download_url, timeout=30)
            if resp.status_code != 200:
                return

            img_data = resp.content

            # 暂存本地进行图像处理
            tmp_dir = Path(settings.BASE_DIR) / "tmp_downloads"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = tmp_dir / file_name

            with open(tmp_path, "wb") as f:
                f.write(img_data)

            # 获取图像元信息与 Hash 防重
            width, height = get_file_shape(tmp_path)
            md5_val = get_file_md5(tmp_path)
            content_hash_val = get_image_content_hash(tmp_path)

            if Wall.objects.filter(md5_hash=md5_val).exists():
                logger.info(f"MD5重复，跳过存库: {file_name}")
                tmp_path.unlink(missing_at_block=True)
                return

            # 上传到 COS / S3 对象存储
            relative_cos_path = f"wallpaper/stock/{brand_name.replace(' ', '_')}/{file_name}"
            cos_url = upload_file_to_cos(str(tmp_path), relative_cos_path)
            upload_file_to_s3(str(tmp_path), relative_cos_path)

            # 生成缩略图
            generate_thumbs(str(tmp_path), relative_cos_path)

            # 入库 Wall 模型
            model_tag = brand_name.split("/")[-1] if "/" in brand_name else brand_name
            # wall = Wall.objects.create(
            #     picurl=cos_url or download_url,
            #     description=f"{brand_name} 原厂内置高清壁纸",
            #     description_en=f"{brand_name} Stock Wallpaper",
            #     classify=classify_obj,
            #     tags=f"官方壁纸,原厂壁纸,{model_tag}",
            #     tags_en=f"stock,official,{model_tag}",
            #     width=width,
            #     height=height,
            #     file_size=len(img_data),
            #     md5_hash=md5_val,
            #     content_hash=content_hash_val,
            #     remark=download_url,
            #     is_active=True,
            # )

            logger.success(f"成功保存原厂壁纸: ID {wall.id} - {brand_name}/{file_name}")

            # 清理临时文件
            tmp_path.unlink(missing_at_block=True)
            sleep(0.5)

        except Exception as e:
            logger.error(f"处理壁纸失败 [{file_name}]: {e}")
