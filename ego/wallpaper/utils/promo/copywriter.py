import random
from datetime import datetime


class PromoCopywriter:
    """
    小红书与微信公众号营销文案生成引擎
    支持：
    1. 小红书极简爆款笔记 (xhs_post.txt)
    2. 微信公众号贴图发布极简配文 (wechat_gallery_post.txt) - 专为公众号图片动态设计，80~120字
    3. 微信公众号长图文 Markdown (wechat_post.md) - 精简排版版
    """

    # 小红书爆款标题模板库 (严格不超过 20 字，包含 emoji 与标点)
    XHS_TITLE_TEMPLATES = [
        "换上新壁纸被治愈了✨私藏18款神仙锁屏",
        "被问爆的18款神仙锁屏！高级感拉满📱",
        "每一张都心动！私藏18款iPhone超清壁纸🤍",
        "审美在线！精选18款高级感治愈锁屏合辑✨",
        "手机颜值翻倍！沉浸感超强的18款壁纸🔥",
        "干净又高级！18款治愈系iPhone锁屏🌿",
        "今日份审美充能！18款超耐看神仙壁纸🫧",
    ]

    # 小红书极简呼吸感正文前言
    XHS_INTROS = [
        "换壁纸真的会让人开心一整天！\n精选 18 款高质感锁屏壁纸，每一张都经过 iPhone 真机测算，极简无遮挡，干净又高级🌿\n直接右滑挑选心动同款，每张都标有专属编号～",
        "好看的壁纸很多，但懂呼吸感的很少。\n今天整理了 18 款治愈系超清壁纸，色调温柔耐看，不挡时钟与灵动岛，亮屏瞬间就被治愈了✨\n右滑即可查看全套上屏效果～",
        "手机屏幕是每天陪伴我们最久的窗口。\n拒绝千篇一律，一口气收录 18 款超清锁屏，深浅色系一应俱全，直接右滑选你的心动壁纸📱",
        "今日份视觉治愈！\n精选 18 款 4K 无损画质手机壁纸，干净透气高级感拉满，右滑查看全部 18 张上屏效果～✨",
    ]

    @classmethod
    def generate_xhs_content(
        cls,
        wall_items: list,
        custom_theme: str = None,
    ) -> dict:
        """
        生成小红书笔记文本（精炼极简版，100-150字，标题严格限制 <= 20字）
        """
        primary_title = random.choice(cls.XHS_TITLE_TEMPLATES)
        if custom_theme:
            candidate = f"{custom_theme}壁纸｜{primary_title}"
            if len(candidate) > 20:
                primary_title = f"{custom_theme}壁纸｜精选18款神仙锁屏✨"
            else:
                primary_title = candidate

        # 严格截断确保绝对不超过 20 字
        primary_title = primary_title[:20]
        alt_titles = [t[:20] for t in cls.XHS_TITLE_TEMPLATES if t[:20] != primary_title][:3]
        intro = random.choice(cls.XHS_INTROS)

        interaction_text = "💬 你最喜欢第几款？在评论区留下心动的编号吧～"

        base_tags = [
            "#手机壁纸",
            "#高清壁纸",
            "#锁屏壁纸",
            "#iPhone壁纸",
            "#本我壁纸",
            "#治愈系壁纸",
            "#小红书爆款壁纸",
        ]
        if custom_theme:
            base_tags.insert(0, f"#{custom_theme}壁纸")
        tags_str = " ".join(base_tags[:7])

        full_body = (
            f"{intro}\n\n"
            f"{interaction_text}\n\n"
            f"{tags_str}"
        )

        return {
            "title": primary_title,
            "alt_titles": alt_titles,
            "body": full_body,
            "tags": tags_str,
        }

    @classmethod
    def generate_wechat_gallery_content(
        cls,
        wall_items: list,
        custom_theme: str = None,
    ) -> str:
        """
        生成微信公众号【贴图/图片消息】极简配文 (纯文本，图18自带完整指引)
        """
        # 收集所有壁纸的编号
        ids = [f"#{item['id']}" for item in wall_items]
        ids_str = ", ".join(ids[:10])
        if len(ids) > 10:
            ids_str += f" 等 {len(ids)} 款"

        theme_text = f"【{custom_theme}】" if custom_theme else "【今日精选】"

        gallery_text = (
            f"{theme_text} 18款高质感手机锁屏壁纸合辑✨\n\n"
            f"色调温柔，干净通透，滑动上方图片即可查看全套 iPhone 锁屏效果～\n\n"
            f"📌 本期精选编号：{ids_str}\n\n"
            f"喜欢本期壁纸的话，欢迎在留言区告诉我心动的编号～"
        )
        return gallery_text

    @classmethod
    def generate_wechat_content(
        cls,
        wall_items: list,
        date_str: str = None,
        custom_theme: str = None,
    ) -> dict:
        """
        生成微信公众号传统长图文精简版 Markdown
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        theme_title = f"{custom_theme} · " if custom_theme else ""
        title = f"{theme_title}今日壁纸精选 | 18款4K超清锁屏合辑"
        digest = "审美在线的治愈系手机壁纸合辑，每款均已适配上屏效果，微信搜小程序「本我壁纸」输入编号直达。"

        # 生成精简贴图条目
        items_lines = []
        for idx, item in enumerate(wall_items, start=1):
            wid = item["id"]
            desc = item.get("description") or f"精选壁纸 #{wid}"
            clean_desc = desc.split("。")[0].split("图源")[0].strip()

            line = (
                f"**P{idx:02d} ｜ #{wid} · {clean_desc}**\n\n"
                f"*(配图建议：上传 0{idx+1}_wall_#{wid}.png 样机图)*\n"
            )
            items_lines.append(line)

        items_block = "\n".join(items_lines)

        markdown_body = (
            f"# {title}\n\n"
            f"> 今日精选 18 款质感手机锁屏，适配 iPhone / iOS 锁屏与灵动岛，干净通透，高级感拉满。\n\n"
            f"---\n\n"
            f"{items_block}\n"
            f"---\n\n"
            f"### 📱 如何保存 4K 无损原图？\n\n"
            f"1. 微信搜索小程序 **「本我壁纸」** 进入应用；\n"
            f"2. 首页输入上方对应的 **壁纸编号** 即可一键保存超清原图；\n"
            f"3. 🎁 **读者专属福利**：在公众号后台留言 **【体验码】**，免费领取 3 天 VIP 兑换码，畅享全站图库！\n\n"
            f"喜欢本期壁纸的话，欢迎点击文末的 **「点赞」** 与 **「在看」** 支持一下～"
        )

        return {
            "title": title,
            "digest": digest,
            "markdown": markdown_body,
        }
