import json
from django.core.management.base import BaseCommand
from wallpaper.models import Classify, Wall
from wallpaper.utils.promo import PromoBuilder, PromoCurator


class Command(BaseCommand):
    help = "一键生成小红书和微信公众号的每日 18 图壁纸推荐素材包 (含大标封面、16张iPhone样机展示图、互动尾图与定制文案)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            type=str,
            default="daily_free",
            choices=["daily_free", "trending", "category", "theme"],
            help="选品模式：daily_free(每日限免，默认) | trending(热门趋势) | category(分类) | theme(主题/标签)",
        )
        parser.add_argument(
            "--category",
            type=str,
            default=None,
            help="当 mode 为 category 时指定的分类名称，如 'AI美图'、'可爱萌宠' 或 '自然风光'",
        )
        parser.add_argument(
            "--theme",
            type=str,
            default=None,
            help="当 mode 为 theme 时指定的主题关键词，如 'AI美女'、'治愈' 或 '极简'",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=16,
            help="推荐壁纸展示图数量，默认 16 张 (加上封面与尾图正好 18 张)",
        )
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="生成指定日期的推广素材 (格式: YYYY-MM-DD)，默认为今日",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="自定义素材输出目录路径",
        )
        parser.add_argument(
            "--with-clock",
            action="store_true",
            dest="show_clock",
            default=False,
            help="显示锁屏时钟组件（默认不显示）",
        )
        parser.add_argument(
            "--with-dock",
            action="store_true",
            dest="show_dock",
            default=False,
            help="显示底部手电筒和相机图标（默认不显示）",
        )
        parser.add_argument(
            "--no-random",
            action="store_false",
            dest="random_sample",
            default=True,
            help="关闭加权随机采样（默认开启随机，确保每天选品不重复）",
        )
        parser.add_argument(
            "--exclude-days",
            type=int,
            default=14,
            help="自动排除近 N 天已发布的壁纸（默认 14 天，设为 0 关闭排重）",
        )
        parser.add_argument(
            "--custom-title",
            type=str,
            default=None,
            help="自定义封面主标题文字 (如 '高颜值动漫精选')",
        )
        parser.add_argument(
            "--custom-xhs-title",
            type=str,
            default=None,
            help="自定义小红书主标题",
        )
        parser.add_argument(
            "--custom-xhs-body-file",
            type=str,
            default=None,
            help="包含自定义小红书正文的文件路径",
        )
        parser.add_argument(
            "--custom-wechat-file",
            type=str,
            default=None,
            help="包含自定义微信贴图配文的文件路径",
        )
        parser.add_argument(
            "--list-categories",
            action="store_true",
            help="列出当前壁纸库中所有可用分类及壁纸数量",
        )
        parser.add_argument(
            "--preview-walls",
            action="store_true",
            help="仅预览当日选中的壁纸清单及标签，不渲染大图（方便文案构思）",
        )

    def handle(self, *args, **options):
        # 1. 查询所有可用分类
        if options["list_categories"]:
            self.stdout.write(self.style.NOTICE("📦 壁纸库分类列表与壁纸总数："))
            classifies = Classify.objects.all().order_by("sort", "id")
            for c in classifies:
                total = c.wall_set.filter(is_active=True).count()
                self.stdout.write(f"  • 分类名称: {c.name:<12} (分类ID: {c.id:<4} 壁纸数: {total})")
            self.stdout.write(self.style.NOTICE("\n💡 提示：若需按标签精准检索，可以使用 --mode theme --theme <标签名> (如 --theme 'AI美女')"))
            return

        mode = options["mode"]
        category = options["category"]
        theme = options["theme"]
        count = options["count"]
        target_date = options["date"]
        output_dir = options["output_dir"]
        show_clock = options["show_clock"]
        show_dock = options["show_dock"]
        random_sample = options["random_sample"]
        exclude_days = options["exclude_days"]
        custom_title = options["custom_title"]

        # 2. 仅预览选品清单
        if options["preview_walls"]:
            self.stdout.write(self.style.NOTICE(f"🔍 预览选品... 模式: {mode}, 分类: {category}, 主题: {theme}"))
            walls = PromoCurator.curate(
                mode=mode,
                category_name=category,
                theme_keyword=theme,
                target_date=target_date,
                count=count + 1,
                random_sample=random_sample,
                exclude_recent_days=exclude_days,
            )
            preview_data = [
                {
                    "index": i + 1,
                    "id": w["id"],
                    "title": w["title"],
                    "classify": w["classify_name"],
                    "tags": w["tags"],
                    "role": "封面展示" if i == 0 else f"展示图 #{i}",
                }
                for i, w in enumerate(walls)
            ]
            self.stdout.write(json.dumps(preview_data, ensure_ascii=False, indent=2))
            return

        custom_xhs_title = options["custom_xhs_title"]
        custom_xhs_body = None
        if options["custom_xhs_body_file"]:
            try:
                with open(options["custom_xhs_body_file"], "r", encoding="utf-8") as f:
                    custom_xhs_body = f.read()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ 无法读取 custom_xhs_body_file: {e}"))

        custom_wechat_text = None
        if options["custom_wechat_file"]:
            try:
                with open(options["custom_wechat_file"], "r", encoding="utf-8") as f:
                    custom_wechat_text = f.read()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ 无法读取 custom_wechat_file: {e}"))

        self.stdout.write(self.style.NOTICE(f"🚀 开始生成 18 图宣发素材包... 模式: {mode} (随机采样: {random_sample}, 排重天数: {exclude_days}天)"))

        try:
            res = PromoBuilder.build_daily_package(
                mode=mode,
                category_name=category,
                theme_keyword=theme,
                target_date=target_date,
                count=count,
                output_dir=output_dir,
                show_clock=show_clock,
                show_dock_icons=show_dock,
                random_sample=random_sample,
                exclude_recent_days=exclude_days,
                custom_cover_title=custom_title,
                custom_xhs_title=custom_xhs_title,
                custom_xhs_body=custom_xhs_body,
                custom_wechat_text=custom_wechat_text,
            )

            out_path = res["output_dir"]
            cover_wall = res["cover_wall"]
            inner_walls = res["inner_walls"]
            images = [f for f in res["generated_files"] if f["type"] in ("cover", "wall_mockup", "guide_tail")]

            self.stdout.write(self.style.SUCCESS(f"\n宣发素材包生成成功！输出目录: {out_path}"))
            self.stdout.write(self.style.SUCCESS(f"渲染图片总数: {len(images)} 张 (1 封面 + {len(inner_walls)} 内页展示图 + 1 尾图)"))
            self.stdout.write(self.style.SUCCESS(f"封面壁纸: #{cover_wall['id']}"))
            self.stdout.write(self.style.SUCCESS(f"内页展示壁纸清单: {[w['id'] for w in inner_walls]} (与封面完全不重样)"))

            self.stdout.write(self.style.NOTICE("\n生成文件清单："))
            for f in res["generated_files"]:
                self.stdout.write(f"  - [{f['type']}] {f['path']}")

            self.stdout.write(self.style.NOTICE("\n小红书推荐标题："))
            self.stdout.write(f"   > {res['xhs_data']['title']}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 生成失败: {e}"))
            raise e
