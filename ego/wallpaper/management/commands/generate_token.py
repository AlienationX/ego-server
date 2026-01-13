from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "下载最近8天的bing壁纸"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="过期日期")

    def handle(self, *args, **options):
        expire_date = options.get("date")

        self.stdout.write(self.style.SUCCESS(f"成功 {expire_date}"))
