import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from .copywriter import PromoCopywriter
from .curator import PromoCurator
from .mockup_renderer import PromoMockupRenderer


class PromoBuilder:
    """
    推广素材流水线总构建器
    - 每次生成自动清空之前的旧目录
    - 挑选 17 款壁纸：第 1 款做专属封面，第 2~17 款做内页展示图（彻底杜绝封面与第 1 张重复）
    - 渲染 18 张对标附件原色钛金属 iPhone 高精真机图 (实体按键、天线条、原厂灵动岛、悬浮羽化阴影、官方Logo)
    - 封面采用高质感 3D 双机错落排版 (Dual Phone Showcase)
    - 微信文案提供【贴图消息专用极简文本】与【长文章精简版】
    - 引导文案与尾图统一为在评论区或后台留言【体验码】
    """

    @classmethod
    def build_daily_package(
        cls,
        mode: str = "daily_free",
        category_name: str = None,
        theme_keyword: str = None,
        target_date: str = None,
        count: int = 16,  # 16 张壁纸展示图 + 1 封面 + 1 尾图 = 18 张图
        output_dir: str = None,
        show_clock: bool = False,
        show_dock_icons: bool = False,
        random_sample: bool = True,
        exclude_recent_days: int = 14,
        custom_cover_title: str = None,
        custom_xhs_title: str = None,
        custom_xhs_body: str = None,
        custom_wechat_text: str = None,
    ) -> dict:
        """
        全流程构建 18 图宣发素材包
        :param random_sample: 是否开启加权随机洗牌，避免每天选出完全一样的壁纸
        :param exclude_recent_days: 自动排除近 N 天已发布的壁纸，杜绝重复发布
        :param custom_cover_title: 自定义封面主标题
        :param custom_xhs_title: 自定义小红书主标题 (可由大模型生成)
        :param custom_xhs_body: 自定义小红书正文 (可由大模型生成)
        :param custom_wechat_text: 自定义公众号贴图配文 (可由大模型生成)
        """
        now = timezone.localtime(timezone.now())
        if not target_date:
            target_date = now.strftime("%Y-%m-%d")

        # 1. 确定输出目录，并清空旧目录内容
        if not output_dir:
            output_dir = os.path.join(settings.MEDIA_ROOT, "promo_output", target_date)

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        # 2. 选品：挑选 count + 1 (即 17 张) 真实存在的本地壁纸
        # 封面使用第 1 张，内页展示图使用后 16 张，绝不重复！
        total_needed = count + 1
        all_walls = PromoCurator.curate(
            mode=mode,
            category_name=category_name,
            theme_keyword=theme_keyword,
            target_date=target_date,
            count=total_needed,
            random_sample=random_sample,
            exclude_recent_days=exclude_recent_days,
        )

        if not all_walls:
            raise ValueError("未能找到符合条件的本地壁纸进行推广生成，请检查壁纸库数据。")

        hero_wall = all_walls[0]
        # 内页展示壁纸（从第 2 张开始取，共 count 张，如 16 张）
        inner_walls = all_walls[1:count + 1]
        if not inner_walls:
            inner_walls = [hero_wall]

        generated_files = []

        # 确定封面主标题
        if custom_cover_title:
            cover_title = custom_cover_title
        elif theme_keyword:
            cover_title = f"{theme_keyword} · 质感锁屏"
        elif category_name:
            cover_title = f"{category_name} · 质感锁屏"
        else:
            cover_title = "今 日 份 神 仙 锁 屏"

        # 3. 渲染 iPhone 样机图片素材 (总计 18 张)

        # (a) 第 01 张：3D 错落双机封面 (Cover) - 专属王牌壁纸 + 次选壁纸背景层次，大标牌与Logo
        sub_wall_path = inner_walls[0]["path"] if inner_walls else hero_wall["path"]
        cover_img = PromoMockupRenderer.render_cover_dual(
            wall_hero_path=hero_wall["path"],
            wall_sub_path=sub_wall_path,
            cover_title=cover_title,
            cover_subtitle="共 18 款精选 · 原图无损 · 附编号直达",
            show_clock=show_clock,
            show_dock_icons=show_dock_icons,
        )
        cover_file = os.path.join(output_dir, "01_cover.png")
        cover_img.save(cover_file, quality=95)
        generated_files.append({"type": "cover", "path": cover_file, "wall_id": hero_wall["id"]})

        # (b) 第 02 ~ 17 张：壁纸锁屏展示图 (Mockup Preview) - 展示另外 16 张完全不同的壁纸！
        for idx, item in enumerate(inner_walls, start=2):
            show_img = PromoMockupRenderer.render_phone_mockup(
                wall_image_path=item["path"],
                wall_id=item["id"],
                is_cover=False,
                show_clock=show_clock,
                show_dock_icons=show_dock_icons,
                date_text=None,
                time_text="09:41",
            )
            file_name = f"{idx:02d}_wall_#{item['id']}.png"
            file_path = os.path.join(output_dir, file_name)
            show_img.save(file_path, quality=95)
            generated_files.append({"type": "wall_mockup", "path": file_path, "wall_id": item["id"]})

        # (c) 第 18 张：引导尾图双版本 (小红书防限流专版 + 微信公众号专版)
        # 1. 小红书防限流专版尾图 (去除微信/小程序等敏感词，改为“主页简介/置顶入口直达”，防限流)
        tail_xhs = PromoMockupRenderer.render_guide_tail(total_count=18, platform="xhs")
        tail_xhs_file = os.path.join(output_dir, "18_guide_tail_xhs.png")
        tail_xhs.save(tail_xhs_file, quality=95)
        generated_files.append({"type": "guide_tail_xhs", "path": tail_xhs_file})

        # 默认 18_guide_tail.png 采用小红书防限流版本，确保用户直接选中 18 张图发布小红书时 100% 安全
        tail_file = os.path.join(output_dir, "18_guide_tail.png")
        tail_xhs.save(tail_file, quality=95)
        generated_files.append({"type": "guide_tail", "path": tail_file})

        # 2. 微信公众号专版尾图 (微信搜一搜小程序「本我壁纸」)
        tail_wechat = PromoMockupRenderer.render_guide_tail(total_count=18, platform="wechat")
        tail_wechat_file = os.path.join(output_dir, "18_guide_tail_wechat.png")
        tail_wechat.save(tail_wechat_file, quality=95)
        generated_files.append({"type": "guide_tail_wechat", "path": tail_wechat_file})

        # 4. 生成文案资产
        custom_theme = theme_keyword or category_name

        # (a) 小红书文案
        xhs_data = PromoCopywriter.generate_xhs_content(
            wall_items=inner_walls,
            custom_theme=custom_theme,
        )
        if custom_xhs_title:
            xhs_data["title"] = custom_xhs_title.strip()[:20]
        if custom_xhs_body:
            xhs_data["body"] = custom_xhs_body

        # 确保备选标题和主标题均不超过 20 字
        main_xhs_title = xhs_data['title'][:20]
        xhs_content_str = (
            f"【小红书推荐标题（选其一）】\n"
            f"1. {main_xhs_title}\n"
        )
        for i, alt in enumerate(xhs_data.get("alt_titles", []), start=2):
            xhs_content_str += f"{i}. {alt[:20]}\n"

        xhs_content_str += (
            f"\n----------------------------------------\n"
            f"【正文内容（直接复制）】\n"
            f"----------------------------------------\n\n"
            f"{xhs_data['body']}\n"
        )
        xhs_file = os.path.join(output_dir, "xhs_post.txt")
        with open(xhs_file, "w", encoding="utf-8") as f:
            f.write(xhs_content_str)
        generated_files.append({"type": "xhs_copy", "path": xhs_file})

        # (b) 微信公众号文案 (纯文本，最推荐贴图消息模式)
        if custom_wechat_text:
            wechat_str = custom_wechat_text
        else:
            wechat_str = PromoCopywriter.generate_wechat_gallery_content(
                wall_items=inner_walls,
                custom_theme=custom_theme,
            )
        wechat_file = os.path.join(output_dir, "wechat_post.txt")
        with open(wechat_file, "w", encoding="utf-8") as f:
            f.write(wechat_str)
        generated_files.append({"type": "wechat_copy", "path": wechat_file})

        # (c) 记录今日发布的壁纸 ID，供后续自动排重
        PromoCurator.record_published_ids(target_date, [w["id"] for w in all_walls])

        # 5. 保存元数据记录
        manifest = {
            "target_date": target_date,
            "mode": mode,
            "category_name": category_name,
            "theme_keyword": theme_keyword,
            "total_images": len([f for f in generated_files if f["type"] in ("cover", "wall_mockup", "guide_tail")]),
            "hero_wall_id": hero_wall["id"],
            "inner_wall_ids": [w["id"] for w in inner_walls],
            "show_clock": show_clock,
            "show_dock_icons": show_dock_icons,
            "files": generated_files,
            "generated_at": now.isoformat(),
        }
        manifest_file = os.path.join(output_dir, "manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        return {
            "output_dir": output_dir,
            "cover_wall": hero_wall,
            "inner_walls": inner_walls,
            "total_images": manifest["total_images"],
            "generated_files": generated_files,
            "xhs_data": xhs_data,
            "manifest": manifest,
            "files": generated_files,
        }
