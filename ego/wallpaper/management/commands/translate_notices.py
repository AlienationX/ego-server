import time
from datetime import datetime

import translators as ts
from django.core.management.base import BaseCommand
from django.db.models import Q
from wallpaper.models import Notice


class Command(BaseCommand):
    help = "批量翻译公告的 title 和 content"

    def add_arguments(self, parser):
        parser.add_argument("--notice-id", type=int, help="壁纸ID")
        parser.add_argument("--force", action="store_true", help="强制重新计算所有壁纸")  # 布尔值，还有store_false

    def handle(self, *args, **options):
        if ts is None:
            self.stdout.write(self.style.ERROR("请先安装翻译库: uv add translators"))
            return

        notice_id = options.get("notice_id")
        force = options.get("force", False)

        if notice_id:
            notices = Notice.objects.filter(id=notice_id)
        elif not force:
            notices = Notice.objects.filter(Q(title_en__isnull=True) | Q(content_en__isnull=True))
        else:
            notices = Notice.objects.all()

        total = notices.count()
        self.stdout.write(f"{datetime.now()} 总计找到 {total} 条公告数据待处理...")

        notices_to_update = []
        batch_size = 1

        for i, notice in enumerate(notices):
            changed = False

            # 1. 翻译 title
            if notice.title:
                en_title = self.translate_text(notice.title)
                if en_title:
                    notice.title_en = en_title
                    changed = True

            # 2. 翻译 content
            if notice.content:
                en_content = self.translate_text(notice.content)
                if en_content:
                    notice.content_en = en_content
                    changed = True

            if changed:
                notices_to_update.append(notice)

            if len(notices_to_update) >= batch_size:
                Notice.objects.bulk_update(notices_to_update, ["title_en", "content_en"])
                self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 已成功更新处理 {i + 1}/{total} 条..."))
                notices_to_update = []

        if notices_to_update:
            Notice.objects.bulk_update(notices_to_update, ["title_en", "content_en"])
            self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 已成功更新处理 {total}/{total} 条公告..."))

        self.stdout.write(self.style.SUCCESS(f"{datetime.now()} 所有公告翻译任务完成！"))

    def translate_text(self, text):
        try:
            # 使用 google 翻译，避免封禁加了一点延迟
            time.sleep(0.5)
            return ts.translate_text(text, translator="google", from_language="zh-CN", to_language="en")
        except Exception as e:
            self.stderr.write(f"翻译失败: {text[:30]}... - Error: {e}")
            return None
