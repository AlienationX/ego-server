# yourapp/management/commands/bulk_add_data.py

"""使用csv数据批量导入到数据库中，自动生成主键，其实直接用csv导入数据库也差不多？"""

from django.core.management.base import BaseCommand
from wallpaper.models import Product
import csv

class Command(BaseCommand):
    help = '从 CSV 文件批量导入商品数据'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSV 文件路径')

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            products = [
                Product(name=row['name'], price=row['price'])
                for row in reader
            ]
            Product.objects.bulk_create(products)
            self.stdout.write(self.style.SUCCESS(f'成功导入 {len(products)} 条数据'))