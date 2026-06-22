import re
import time
from datetime import datetime

import translators as ts
from django.core.management.base import BaseCommand
from django.db.models import Q
from loguru import logger
from wallpaper.models import Wall


class Command(BaseCommand):
    help = "批量翻译壁纸的 description 和 tags"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")
        parser.add_argument("--force", action="store_true", help="强制重新计算所有壁纸")  # 布尔值，还有store_false

    def handle(self, *args, **options):
        if ts is None:
            self.stdout.write(self.style.ERROR("请先安装翻译库: uv add translators"))
            return

        wall_id = options.get("wall_id")
        force = options.get("force", False)

        if wall_id:
            walls = Wall.objects.filter(id=wall_id)
        elif not force:
            walls = Wall.objects.filter(Q(description_en__isnull=True) | Q(tags_en__isnull=True))
        else:
            walls = Wall.objects.all()

        total = walls.count()
        logger.info(f"总计找到 {total} 条壁纸数据待处理...")

        walls_to_update = []
        batch_size = 50

        for i, wall in enumerate(walls):
            changed = False

            # 1. 翻译 description
            if wall.description and not wall.description_en:
                en_desc = self.translate_text(wall.description)
                if en_desc:
                    wall.description_en = en_desc
                    changed = True

            # 2. 处理和翻译 tags
            if wall.tags:
                new_cn_tags, new_en_tags = self.process_tags(wall.tags)
                if new_cn_tags != wall.tags or new_en_tags != wall.tags_en:
                    wall.tags = new_cn_tags
                    wall.tags_en = new_en_tags
                    changed = True

            if changed:
                walls_to_update.append(wall)

            if len(walls_to_update) >= batch_size:
                Wall.objects.bulk_update(walls_to_update, ["description_en", "tags", "tags_en"])
                self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 已成功更新处理 {i + 1}/{total} 条..."))
                walls_to_update = []

        if walls_to_update:
            Wall.objects.bulk_update(walls_to_update, ["description_en", "tags", "tags_en"])
            self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 已成功更新处理 {total}/{total} 条..."))

        self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 所有翻译与拆分任务完成！"))

    def is_english(self, text):
        """简单的启发式检测：如果大部分是英文字符，则认为已经是英文"""
        if not text:
            return True
        # 移除标点和空格
        clean_text = re.sub(r"[^a-zA-Z\u4e00-\u9fa5]", "", text)
        if not clean_text:
            return True
        en_chars = len(re.findall(r"[a-zA-Z]", clean_text))
        return en_chars / len(clean_text) > 0.5

    def translate_text(self, text):
        if not text or self.is_english(text):
            return text
        try:
            # 使用 google 或 bing 翻译，避免封禁加了一点延迟
            time.sleep(0.5)
            # 你也可以换成你自己调用的第三方大模型 API
            return ts.translate_text(text, translator="google", from_language="zh-CN", to_language="en")
        except Exception as e:
            self.stderr.write(f"翻译失败: {text} - Error: {e}")
            return None

    def process_tags(self, tags_str):
        if not tags_str:
            return "", ""
        tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
        cn_tags = []
        en_tags = []
        for tag in tags_list:
            if self.is_english(tag):
                en_tags.append(tag)
            else:
                cn_tags.append(tag)
                # 翻译中文 tag
                translated_tag = self.translate_text(tag)
                if translated_tag:
                    en_tags.append(translated_tag)

        # 去重（忽略大小写，保留首次出现的格式）
        seen_lower = set()
        unique_en_tags = []
        for tag in en_tags:
            tag_lower = tag.lower()
            if tag_lower not in seen_lower:
                seen_lower.add(tag_lower)
                unique_en_tags.append(tag)
        en_tags = unique_en_tags
        return ",".join(cn_tags), ",".join(en_tags)
