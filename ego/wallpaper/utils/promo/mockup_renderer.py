import math
import os
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


def _find_font(font_names, default_size=32):
    """尝试加载系统中的字体，自动匹配可用路径"""
    search_dirs = [
        "/System/Library/Fonts",
        "/System/Library/Fonts/Supplemental",
        "/Library/Fonts",
    ]
    for name in font_names:
        for s_dir in search_dirs:
            full_path = os.path.join(s_dir, name)
            if os.path.exists(full_path):
                try:
                    return ImageFont.truetype(full_path, default_size)
                except Exception:
                    continue
    for name in font_names:
        try:
            return ImageFont.truetype(name, default_size)
        except Exception:
            continue
    return ImageFont.load_default()


def get_clock_font(size=120):
    """时钟与步骤大数字字体（Apple SF 风格）"""
    font_candidates = [
        "SFNS.ttf",
        "Helvetica.ttc",
        "Arial Bold.ttf",
        "STHeiti Medium.ttc",
    ]
    return _find_font(font_candidates, size)


def get_text_font(size=28, bold=False):
    """正文与中文字体"""
    if bold:
        font_candidates = [
            "STHeiti Medium.ttc",
            "Arial Bold.ttf",
            "Arial Unicode.ttf",
        ]
    else:
        font_candidates = [
            "STHeiti Light.ttc",
            "STHeiti Medium.ttc",
            "Arial Unicode.ttf",
            "Helvetica.ttc",
        ]
    return _find_font(font_candidates, size)


class PromoMockupRenderer:
    """
    小红书 / 微信公众号营销视觉素材渲染引擎
    输出尺寸：1080 x 1440 (3:4 黄金画幅)
    - 4x SSAA 亚像素级超采样：彻底消除黑框与圆角锯齿
    - 严格 15px 全等宽同心圆角黑边：上下左右与 4 个圆角厚度完全恒定为 15px
    - 底部手电筒 & 相机图标采用 4x SSAA 极清矢量重绘，彻底解决发虚问题
    - 支持时钟/底部图标可选配置 (默认开启)
    - 黄金垂直呼吸间距与扁平化底部微标
    - 顶级科技美学质感尾图 (深邃星云渐变 + 高清晰黑金微标 + 毛玻璃 + 立体黄金按钮)
    """

    CANVAS_WIDTH = 1080
    CANVAS_HEIGHT = 1440

    @classmethod
    def get_assets_dir(cls) -> str:
        return os.path.join(os.path.dirname(__file__), "assets")

    @classmethod
    def get_app_logo_image(cls, size: int = 26) -> Image.Image:
        """读取并生成带圆角的官方 App Logo"""
        logo_path = os.path.join(cls.get_assets_dir(), "logo.png")
        if not os.path.exists(logo_path):
            return None
        try:
            raw_logo = Image.open(logo_path).convert("RGBA")
            resized = raw_logo.resize((size, size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            m_draw = ImageDraw.Draw(mask)
            m_draw.rounded_rectangle((0, 0, size, size), radius=max(4, size // 4), fill=255)
            logo_rounded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            logo_rounded.paste(resized, (0, 0), mask)
            return logo_rounded
        except Exception:
            return None

    @classmethod
    def render_dock_button(cls, icon_type: str, diameter: int = 52) -> Image.Image:
        """
        基于 4x SSAA 极清锐利绘制 iOS 锁屏底部毛玻璃按钮 (手电筒 / 相机)
        - 去掉白色外边框，保持深色毛玻璃半透明底盘
        - 内部图标按比例适度缩小，圆圈大小保持不变，精致舒展高级
        """
        SSAA = 4
        dim = diameter * SSAA
        btn = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
        draw = ImageDraw.Draw(btn)

        # 1. 毛玻璃深色圆盘底 (无外白边，纯净深色)
        draw.ellipse((0, 0, dim - 1, dim - 1), fill=(24, 25, 32, 175))

        cx, cy = dim // 2, dim // 2

        if icon_type == "flashlight":
            # 苹果原生手电筒图标 (适度缩小，居中精致)
            head_top_w = int(20 * SSAA)
            head_bot_w = int(14 * SSAA)
            head_h = int(10 * SSAA)
            head_y = cy - int(13 * SSAA)

            trap = [
                (cx - head_top_w // 2, head_y),
                (cx + head_top_w // 2, head_y),
                (cx + head_bot_w // 2, head_y + head_h),
                (cx - head_bot_w // 2, head_y + head_h),
            ]
            draw.polygon(trap, fill=(255, 255, 255, 255))

            body_w = int(11.5 * SSAA)
            body_h = int(15.5 * SSAA)
            body_y = head_y + head_h + int(1 * SSAA)
            draw.rounded_rectangle(
                (cx - body_w // 2, body_y, cx + body_w // 2, body_y + body_h),
                radius=int(2 * SSAA),
                fill=(255, 255, 255, 255),
            )
            # 开关小滑块
            switch_w = int(4 * SSAA)
            switch_h = int(5.5 * SSAA)
            switch_y = body_y + int(3 * SSAA)
            draw.rounded_rectangle(
                (cx - switch_w // 2, switch_y, cx + switch_w // 2, switch_y + switch_h),
                radius=int(1.2 * SSAA),
                fill=(60, 65, 75, 255),
            )

        elif icon_type == "camera":
            # 苹果原生相机图标 (适度缩小，居中精致)
            cam_w = int(26 * SSAA)
            cam_h = int(17.5 * SSAA)
            cam_y = cy - int(6 * SSAA)
            draw.rounded_rectangle(
                (cx - cam_w // 2, cam_y, cx + cam_w // 2, cam_y + cam_h),
                radius=int(3.8 * SSAA),
                fill=(255, 255, 255, 255),
            )
            # 顶部棱镜凸起
            prism_w = int(10 * SSAA)
            prism_h = int(4 * SSAA)
            prism_y = cam_y - prism_h + 1
            draw.rounded_rectangle(
                (cx - prism_w // 2, prism_y, cx + prism_w // 2, cam_y + 1),
                radius=int(1.5 * SSAA),
                fill=(255, 255, 255, 255),
            )
            # 中央大镜头 (双层同心圆)
            lens_r = int(5.5 * SSAA)
            lens_cy = cam_y + int(9.5 * SSAA)
            draw.ellipse(
                (cx - lens_r, lens_cy - lens_r, cx + lens_r, lens_cy + lens_r),
                fill=(30, 32, 40, 255),
                outline=(255, 255, 255, 255),
                width=int(1.2 * SSAA),
            )
            # 镜头内部小反光点
            draw.ellipse(
                (cx - int(1.2 * SSAA), lens_cy - int(1.2 * SSAA), cx + int(1.2 * SSAA), lens_cy + int(1.2 * SSAA)),
                fill=(120, 135, 155, 255),
            )
            # 右上角闪光灯小点
            flash_r = int(1.3 * SSAA)
            flash_x = cx + int(8 * SSAA)
            flash_y = cam_y + int(3 * SSAA)
            draw.ellipse((flash_x - flash_r, flash_y - flash_r, flash_x + flash_r, flash_y + flash_r), fill=(40, 42, 50, 255))

        # 高质量平滑降采样回目标像素
        return btn.resize((diameter, diameter), Image.Resampling.LANCZOS)

    @classmethod
    def render_status_bar(cls, sw: int, scale: float = 1.0) -> Image.Image:
        """
        4x SSAA 极清锐利绘制 iPhone 原生锁屏顶部状态栏 (参考官方原生设计 1:1 还原)
        - 中央：深黑灵动岛跑道圆角药丸 (含前置摄像头蓝紫微反光镜头孔 + FaceID 传感器微孔)
        - 右侧状态栏三件套 (从左至右紧凑排列: 4阶蜂窝信号柱 -> Wi-Fi无线网 -> 电池胶囊)
        - 左侧留空 (还原原生锁屏开阔通透感)
        """
        SSAA = 4
        bar_h = int(44 * scale)
        bar = Image.new("RGBA", (sw * SSAA, bar_h * SSAA), (0, 0, 0, 0))
        draw = ImageDraw.Draw(bar)

        cx = (sw * SSAA) // 2
        cy = int(22 * scale * SSAA)

        # 1. 中央灵动岛 (Dynamic Island 跑道圆角胶囊 + 前置镜头孔)
        pill_w = int(96 * scale * SSAA)
        pill_h = int(26 * scale * SSAA)
        pill_r = pill_h // 2
        draw.rounded_rectangle(
            (cx - pill_w // 2, cy - pill_h // 2, cx + pill_w // 2, cy + pill_h // 2),
            radius=pill_r,
            fill=(0, 0, 0, 255),
        )
        # 前置摄像头镜片细节 (深蓝紫双层微反光镜头孔)
        lens_x = cx + int(24 * scale * SSAA)
        lens_r = int(5.2 * scale * SSAA)
        draw.ellipse(
            (lens_x - lens_r, cy - lens_r, lens_x + lens_r, cy + lens_r),
            fill=(12, 14, 25, 255),
        )
        draw.ellipse(
            (lens_x - int(2.2 * scale * SSAA), cy - int(2.2 * scale * SSAA), lens_x + int(1.2 * scale * SSAA), cy + int(1.2 * scale * SSAA)),
            fill=(36, 46, 78, 255),
        )
        # Face ID 传感器小孔 (深灰微孔)
        sensor_x = cx - int(20 * scale * SSAA)
        sensor_r = int(3.6 * scale * SSAA)
        draw.ellipse(
            (sensor_x - sensor_r, cy - sensor_r, sensor_x + sensor_r, cy + sensor_r),
            fill=(18, 18, 22, 255),
        )

        # 2. 右侧状态栏三件套: 从右向左排布 (电池 -> Wi-Fi -> 蜂窝网络信号) 1:1 还原官方截图
        right_margin = sw * SSAA - int(24 * scale * SSAA)

        # (a) 电池图标 (Battery)
        bat_w = int(21 * scale * SSAA)
        bat_h = int(10.5 * scale * SSAA)
        tab_w = int(1.8 * scale * SSAA)
        tab_h = int(4.2 * scale * SSAA)

        bat_right = right_margin - tab_w - 1
        bat_x = bat_right - bat_w
        bat_y = cy - bat_h // 2

        # 电池外壳
        draw.rounded_rectangle(
            (bat_x, bat_y, bat_x + bat_w, bat_y + bat_h),
            radius=int(3 * SSAA),
            outline=(255, 255, 255, 215),
            width=int(1.3 * SSAA),
        )
        # 电池正极极耳
        tab_x = bat_x + bat_w + 1
        tab_y = cy - tab_h // 2
        draw.rounded_rectangle(
            (tab_x, tab_y, tab_x + tab_w, tab_y + tab_h),
            radius=int(0.8 * SSAA),
            fill=(255, 255, 255, 215),
        )
        # 满电电池填充格
        pad = int(1.8 * scale * SSAA)
        fill_w = bat_w - pad * 2
        fill_h = bat_h - pad * 2
        draw.rounded_rectangle(
            (bat_x + pad, bat_y + pad, bat_x + pad + fill_w, bat_y + pad + fill_h),
            radius=int(1.5 * SSAA),
            fill=(255, 255, 255, 245),
        )

        # (b) Wi-Fi 图标 (还原 iOS 原生满格 3 阶：底部实心扇形小楔形 + 中阶粗圆弧 + 外阶粗圆弧)
        gap_bat_wifi = int(7.0 * scale * SSAA)
        wifi_w = int(15 * scale * SSAA)
        wifi_right = bat_x - gap_bat_wifi
        wifi_cx = wifi_right - wifi_w // 2
        bar_base_y = cy + int(5.0 * scale * SSAA)
        wifi_cy = bar_base_y - int(1.0 * scale * SSAA)

        # 底部圆锥小扇形 (满格底层基底)
        r0 = int(3.2 * scale * SSAA)
        draw.pieslice((wifi_cx - r0, wifi_cy - r0, wifi_cx + r0, wifi_cy + r0), start=225, end=315, fill=(255, 255, 255, 255))
        # 中阶粗弧线 (加粗 2.2px)
        r1 = int(6.8 * scale * SSAA)
        w_arc = int(2.2 * SSAA)
        draw.arc((wifi_cx - r1, wifi_cy - r1, wifi_cx + r1, wifi_cy + r1), start=223, end=317, fill=(255, 255, 255, 255), width=w_arc)
        # 外阶粗弧线 (加粗 2.2px)
        r2 = int(10.8 * scale * SSAA)
        draw.arc((wifi_cx - r2, wifi_cy - r2, wifi_cx + r2, wifi_cy + r2), start=223, end=317, fill=(255, 255, 255, 255), width=w_arc)

        # (c) 蜂窝网络信号柱 (Cellular Signal) - 4格满格阶梯圆角粗矩形 (加粗 3.4px)
        gap_wifi_cell = int(7.5 * scale * SSAA)
        cell_right = wifi_right - wifi_w - gap_wifi_cell

        bar_w = int(3.4 * scale * SSAA)
        bar_gap = int(1.8 * scale * SSAA)
        cell_total_w = 4 * bar_w + 3 * bar_gap
        cell_left = cell_right - cell_total_w

        for i in range(4):
            bx = cell_left + i * (bar_w + bar_gap)
            bh = int((3.8 + i * 2.5) * scale * SSAA)
            draw.rounded_rectangle(
                (bx, bar_base_y - bh, bx + bar_w, bar_base_y),
                radius=int(1.0 * SSAA),
                fill=(255, 255, 255, 255),
            )

        return bar.resize((sw, bar_h), Image.Resampling.LANCZOS)

    @classmethod
    def render_iphone_device(
        cls,
        wall_image_path: str,
        target_height: int = 1180,
        show_clock: bool = False,
        show_dock_icons: bool = False,
        time_text: str = "09:41",
        date_text: str = None,
        bezel_thick: int = 15,
    ) -> Image.Image:
        """
        高精度渲染原色钛金属 iPhone 机身 (透明底 RGBA)
        - 4x SSAA 亚像素超采样平滑无锯齿
        - 严格等于 15px 的全等宽同心圆角黑边 (上下、左右与 4 个圆角厚度完全恒定)
        - 4x 极清手电筒与相机图标 (彻底不发虚)
        - 顶部状态栏与灵动岛/前置摄像头孔 (原生旗舰质感)
        - 可选时钟与底部图标组件 (默认开启)
        """
        src_path = os.path.join(cls.get_assets_dir(), "iphone_frame_titanium.png")
        if not os.path.exists(src_path):
            raise FileNotFoundError("Mockup 基础资产未就绪，请检查 assets 目录。")

        src = Image.open(src_path).convert("RGBA")

        # 1. 目标分辨率与等比缩放
        scale = target_height / 1024
        target_width = int(600 * scale)
        src_high = src.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # 2. 严格 15px 全等宽同心圆角计算
        outer_l = int(92 * scale)
        outer_r = int(507 * scale)
        outer_t = int(55 * scale)
        outer_b = int(929 * scale)
        R_outer = int(65 * scale)

        # 钛金属倒角内沿 (原图金属倒角约 5.5px，在内沿处将原图挖空，清除残留杂色灰边与缝隙)
        metal_inset = int(5.5 * scale)
        metal_inner_l = outer_l + metal_inset
        metal_inner_r = outer_r - metal_inset
        metal_inner_t = outer_t + metal_inset
        metal_inner_b = outer_b - metal_inset
        R_metal_inner = max(8, R_outer - metal_inset)

        # 严格使用 15px 边框厚度
        s_left = outer_l + bezel_thick
        s_right = outer_r - bezel_thick
        s_top = outer_t + bezel_thick
        s_bottom = outer_b - bezel_thick
        # 几何同心公式: 内圆角半径严格等于外圆角减去边框厚度
        s_radius = max(8, R_outer - bezel_thick)

        sw = s_right - s_left
        sh = s_bottom - s_top

        # 3. 4x SSAA 亚像素级生成超平滑屏幕蒙版
        SSAA = 4
        hi_mask = Image.new("L", (sw * SSAA, sh * SSAA), 0)
        draw = ImageDraw.Draw(hi_mask)
        draw.rounded_rectangle((0, 0, sw * SSAA, sh * SSAA), radius=s_radius * SSAA, fill=255)
        smooth_screen_mask = hi_mask.resize((sw, sh), Image.Resampling.LANCZOS)

        # 4. 4x SSAA 生成机身纯黑实体底板 (杜绝透视穿透，彻底消除透明缝隙，奠定纯黑 15px 边框)
        hi_cmask = Image.new("RGBA", (target_width * SSAA, target_height * SSAA), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(hi_cmask)
        cdraw.rounded_rectangle(
            (outer_l * SSAA, outer_t * SSAA, outer_r * SSAA, outer_b * SSAA),
            radius=R_outer * SSAA,
            fill=(10, 10, 12, 255),
        )
        chassis_backplate = hi_cmask.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # 5. 4x SSAA 挖空外框平滑蒙版 (在金属内倒角处挖空，保留金属质感与高光，消除原图屏幕内侧杂色)
        hi_fmask = Image.new("L", (target_width * SSAA, target_height * SSAA), 255)
        fdraw = ImageDraw.Draw(hi_fmask)
        fdraw.rounded_rectangle(
            (metal_inner_l * SSAA, metal_inner_t * SSAA, metal_inner_r * SSAA, metal_inner_b * SSAA),
            radius=R_metal_inner * SSAA,
            fill=0,
        )
        smooth_fmask = hi_fmask.resize((target_width, target_height), Image.Resampling.LANCZOS)

        frame_high = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
        frame_high.paste(src_high, (0, 0), smooth_fmask)

        # 6. 壁纸在屏幕高分辨率下直接裁剪
        orig_wall = Image.open(wall_image_path).convert("RGBA")
        ww, wh = orig_wall.size

        w_scale = max(sw / ww, sh / wh)
        nw = int(ww * w_scale)
        nh = int(wh * w_scale)
        wall_scaled = orig_wall.resize((nw, nh), Image.Resampling.LANCZOS)

        left = (nw - sw) // 2
        top = (nh - sh) // 2
        screen_content = wall_scaled.crop((left, top, left + sw, top + sh))

        # 7. 顶部羽化渐变暗层 (保护状态栏、灵动岛与浅色壁纸时钟吃色)
        gradient_h = int(sh * 0.32)
        gradient = Image.new("RGBA", (sw, gradient_h), (0, 0, 0, 0))
        grad_draw = ImageDraw.Draw(gradient)
        for i in range(gradient_h):
            alpha = int(75 * (1 - (i / gradient_h) ** 0.8))
            grad_draw.line([(0, i), (sw, i)], fill=(0, 0, 0, alpha))
        screen_content.paste(gradient, (0, 0), gradient)

        # 8. 渲染锁屏顶部状态栏 (灵动岛药丸 + 摄像头孔 + 蜂窝信号 + Wi-Fi + 电池)
        status_bar = cls.render_status_bar(sw=sw, scale=scale)
        screen_content.paste(status_bar, (0, 0), status_bar)

        # 9. 渲染锁屏大时钟组件 (可选，默认显示)
        if show_clock:
            s_draw = ImageDraw.Draw(screen_content)

            # 日期文字
            if not date_text:
                now = datetime.now()
                weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                date_text = f"{now.month}月{now.day}日 {weekdays[now.weekday()]}"

            date_font = get_text_font(size=int(20 * scale), bold=True)
            db = s_draw.textbbox((0, 0), date_text, font=date_font)
            dw = db[2] - db[0]
            dx = (sw - dw) // 2
            dy = int(76 * scale)
            # 柔和投影 + 文字
            s_draw.text((dx + 1, dy + 2), date_text, font=date_font, fill=(0, 0, 0, 150))
            s_draw.text((dx, dy), date_text, font=date_font, fill=(255, 255, 255, 245))

            # 大时钟文字
            clock_font = get_clock_font(size=int(96 * scale))
            cb = s_draw.textbbox((0, 0), time_text, font=clock_font)
            cw = cb[2] - cb[0]
            cx = (sw - cw) // 2
            cy = int(102 * scale)
            s_draw.text((cx + 2, cy + 3), time_text, font=clock_font, fill=(0, 0, 0, 160))
            s_draw.text((cx, cy), time_text, font=clock_font, fill=(255, 255, 255, 255))

        # 10. 渲染底部手电筒 & 相机图标组件 (可选，默认显示)
        if show_dock_icons:
            btn_diameter = int(44 * scale)  # 约 51px
            btn_y = sh - int(82 * scale)
            left_btn_x = int(36 * scale)
            right_btn_x = sw - int(36 * scale) - btn_diameter

            # 4x SSAA 极清锐利生成手电筒与相机按钮 (无外边框，精致小巧比例)
            torch_btn = cls.render_dock_button("flashlight", diameter=btn_diameter)
            cam_btn = cls.render_dock_button("camera", diameter=btn_diameter)

            screen_content.paste(torch_btn, (left_btn_x, btn_y), torch_btn)
            screen_content.paste(cam_btn, (right_btn_x, btn_y), cam_btn)

            # 底部 Home 指示条
            bar_w = int(140 * scale)
            bar_h = int(4.5 * scale)
            bar_x = (sw - bar_w) // 2
            bar_y = sh - int(16 * scale)
            home_bar = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
            hb_draw = ImageDraw.Draw(home_bar)
            hb_draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=3, fill=(255, 255, 255, 200))
            screen_content = Image.alpha_composite(screen_content, home_bar)

        # 11. 精密合成设备各图层
        device = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
        # (1) 贴入 4x SSAA 纯黑实体机身底板 (彻底杜绝透光与边框杂色，奠定纯黑边框基础)
        device.paste(chassis_backplate, (0, 0), chassis_backplate)
        # (2) 贴入屏幕壁纸与组件 (内含状态栏、灵动岛摄像头孔、时钟与Dock图标)
        device.paste(screen_content, (s_left, s_top), smooth_screen_mask)

        # (3) 屏幕边缘贴入 1.5px 平滑微黑圈 (消除壁纸裁切微边缘，确保交界极致平滑)
        border_mask = Image.new("RGBA", (sw * SSAA, sh * SSAA), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(border_mask)
        bdraw.rounded_rectangle(
            (0, 0, sw * SSAA, sh * SSAA),
            radius=s_radius * SSAA,
            outline=(10, 10, 12, 240),
            width=int(1.6 * SSAA),
        )
        smooth_border = border_mask.resize((sw, sh), Image.Resampling.LANCZOS)
        device.paste(smooth_border, (s_left, s_top), smooth_border)

        # (4) 贴入钛金属外框 (外侧保留原装高光与倒角，内侧已完全挖空由纯黑底板接管)
        device.paste(frame_high, (0, 0), frame_high)

        return device

    @classmethod
    def render_phone_mockup(
        cls,
        wall_image_path: str,
        wall_id: int = None,
        is_cover: bool = False,
        show_clock: bool = False,
        show_dock_icons: bool = False,
        date_text: str = None,
        time_text: str = "09:41",
    ) -> Image.Image:
        """
        渲染标准内页展示图：
        - 严格 15px 全等宽同心圆角黑框
        - 4x SSAA 极清锐利手电筒与相机图标
        - 黄金三段式垂直间距 (顶部留白充足，手机高度 1180px，底部扁平微标)
        - 可选时钟与底部图标
        """
        canvas = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (20, 20, 24, 255))

        # 1. 背景层：壁纸大景深高斯模糊氛围
        orig_wall = Image.open(wall_image_path).convert("RGBA")
        ww, wh = orig_wall.size

        bg_scale = max(cls.CANVAS_WIDTH / ww, cls.CANVAS_HEIGHT / wh)
        bg_w = int(ww * bg_scale)
        bg_h = int(wh * bg_scale)
        bg_img = orig_wall.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
        b_left = (bg_w - cls.CANVAS_WIDTH) // 2
        b_top = (bg_h - cls.CANVAS_HEIGHT) // 2
        bg_crop = bg_img.crop((b_left, b_top, b_left + cls.CANVAS_WIDTH, b_top + cls.CANVAS_HEIGHT))
        bg_blurred = bg_crop.filter(ImageFilter.GaussianBlur(radius=55))

        dim_mask = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 115))
        bg_composite = Image.alpha_composite(bg_blurred, dim_mask)
        canvas.paste(bg_composite, (0, 0))

        # 2. 渲染高保真真机样机 (高度 1180px，留出开阔优雅的上下空间)
        device_h = 1180
        device_img = cls.render_iphone_device(
            wall_image_path=wall_image_path,
            target_height=device_h,
            show_clock=show_clock,
            show_dock_icons=show_dock_icons,
            time_text=time_text,
            date_text=date_text,
            bezel_thick=15,  # 严格设定 15px
        )
        dev_w, dev_h = device_img.size

        # 垂直黄金布局：手机放置在 y=125，底部到 1305
        dev_x = (cls.CANVAS_WIDTH - dev_w) // 2
        dev_y = 125
        canvas.paste(device_img, (dev_x, dev_y), device_img)

        canvas_draw = ImageDraw.Draw(canvas)

        # 3. 顶部品牌徽标：[官方 Logo] + Ego Wallpapers · 本我壁纸 (y=52，舒缓大气)
        logo_img = cls.get_app_logo_image(size=26)
        top_brand = "Ego Wallpapers · 本我壁纸"
        tb_font = get_text_font(size=20, bold=True)
        tb_b = canvas_draw.textbbox((0, 0), top_brand, font=tb_font)
        tb_w = tb_b[2] - tb_b[0]

        total_brand_w = tb_w + (36 if logo_img else 0)
        brand_start_x = (cls.CANVAS_WIDTH - total_brand_w) // 2
        brand_y = 52

        if logo_img:
            canvas.paste(logo_img, (brand_start_x, brand_y - 3), logo_img)
            canvas_draw.text((brand_start_x + 36, brand_y), top_brand, font=tb_font, fill=(255, 255, 255, 205))
        else:
            canvas_draw.text((brand_start_x, brand_y), top_brand, font=tb_font, fill=(255, 255, 255, 205))

        # 4. 底部信息扁平化微标 (扁平轻透处理)
        wid_text = f"# {wall_id}   ·   Ego Wallpapers" if wall_id else "Ego Wallpapers"
        w_font = get_text_font(size=20, bold=False)
        wb = canvas_draw.textbbox((0, 0), wid_text, font=w_font)
        ww = wb[2] - wb[0]
        wh = wb[3] - wb[1]

        pill_px = 24
        pill_py = 8
        pill_w = ww + pill_px * 2
        pill_h = wh + pill_py * 2
        pill_x = (cls.CANVAS_WIDTH - pill_w) // 2
        pill_y = 1358

        pill_layer = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pill_layer)
        p_draw.rounded_rectangle(
            (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
            radius=pill_h // 2,
            fill=(0, 0, 0, 110),
            outline=(255, 255, 255, 45),
            width=1,
        )
        p_draw.text((pill_x + pill_px, pill_y + pill_py - 2), wid_text, font=w_font, fill=(255, 255, 255, 215))
        canvas = Image.alpha_composite(canvas, pill_layer)

        return canvas.convert("RGB")

    @classmethod
    def render_cover_dual(
        cls,
        wall_hero_path: str,
        wall_sub_path: str,
        cover_title: str = "今 日 份 神 仙 锁 屏",
        cover_subtitle: str = "共 18 款精选 · 原图无损 · 附编号直达",
        show_clock: bool = False,
        show_dock_icons: bool = False,
    ) -> Image.Image:
        """
        渲染高质感 3D 双机错落爆款封面 (Dual Phone Showcase, 参考附件2)
        - 左后方：1000px 高度（约前机的 89%），错落靠后摆放，景深空间感真实自然
        - 右前方：1120px 高度，挺立在右前方，高清展示主打壁纸
        - 阴影优化：轻薄细腻的接触落影，紧贴右机左边缘，纯净柔和，绝不大面积污染左机画面
        - 默认无时钟和底部图标，状态栏信号与Wi-Fi全满格加粗
        """
        canvas = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (20, 20, 24, 255))

        # 1. 背景层：主打壁纸高斯模糊氛围
        orig_wall = Image.open(wall_hero_path).convert("RGBA")
        ww, wh = orig_wall.size
        bg_scale = max(cls.CANVAS_WIDTH / ww, cls.CANVAS_HEIGHT / wh)
        bg_w = int(ww * bg_scale)
        bg_h = int(wh * bg_scale)
        bg_img = orig_wall.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
        b_left = (bg_w - cls.CANVAS_WIDTH) // 2
        b_top = (bg_h - cls.CANVAS_HEIGHT) // 2
        bg_crop = bg_img.crop((b_left, b_top, b_left + cls.CANVAS_WIDTH, b_top + cls.CANVAS_HEIGHT))
        bg_blurred = bg_crop.filter(ImageFilter.GaussianBlur(radius=60))
        dim_mask = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 115))
        bg_composite = Image.alpha_composite(bg_blurred, dim_mask)
        canvas.paste(bg_composite, (0, 0))

        # 2. 渲染两台真机样机 (参考附件2：后机小一些，前机挺拔在前，错落有致)
        # (a) 左后方机身 (Sub Device, 高度 1000px，约前机的 89%，产生经典景深透视)
        sub_h = 1000
        sub_device = cls.render_iphone_device(
            wall_image_path=wall_sub_path,
            target_height=sub_h,
            show_clock=show_clock,
            show_dock_icons=show_dock_icons,
            time_text="09:41",
            bezel_thick=15,
        )
        sub_x = 70
        sub_y = 255

        # 左机柔和底影
        sub_alpha = sub_device.split()[3]
        sub_shadow_layer = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 0))
        sub_phone_shadow = Image.new("RGBA", sub_device.size, (0, 0, 0, 75))
        sub_phone_shadow.putalpha(sub_alpha)
        sub_shadow_layer.paste(sub_phone_shadow, (sub_x - 6, sub_y + 6), sub_alpha)
        sub_soft_shadow = sub_shadow_layer.filter(ImageFilter.GaussianBlur(radius=10))
        canvas = Image.alpha_composite(canvas, sub_soft_shadow)

        # 贴入左后方机身
        canvas.paste(sub_device, (sub_x, sub_y), sub_device)

        # (b) 右前方机身 (Hero Device, 高度 1120px，挺立在右前方)
        hero_h = 1120
        hero_device = cls.render_iphone_device(
            wall_image_path=wall_hero_path,
            target_height=hero_h,
            show_clock=show_clock,
            show_dock_icons=show_dock_icons,
            time_text="09:41",
            bezel_thick=15,
        )
        hero_x = 430
        hero_y = 205

        # 3. 轻薄自然的前后机接触落影 (参考附件2：紧贴右机左边缘，纯净柔和，绝不污染遮盖后机画面)
        hero_alpha = hero_device.split()[3]
        hero_shadow_layer = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 0))
        hero_phone_shadow = Image.new("RGBA", hero_device.size, (0, 0, 0, 95))
        hero_phone_shadow.putalpha(hero_alpha)
        hero_shadow_layer.paste(hero_phone_shadow, (hero_x - 8, hero_y + 6), hero_alpha)
        hero_soft_shadow = hero_shadow_layer.filter(ImageFilter.GaussianBlur(radius=12))
        canvas = Image.alpha_composite(canvas, hero_soft_shadow)

        # 贴入右前方主机身 (100% 实心底板，完全遮蔽底层画面)
        canvas.paste(hero_device, (hero_x, hero_y), hero_device)

        # 4. 顶部标题排版
        canvas_draw = ImageDraw.Draw(canvas)

        # 顶部品牌徽章
        logo_img = cls.get_app_logo_image(size=26)
        top_brand = "Ego Wallpapers · 本我壁纸"
        tb_font = get_text_font(size=20, bold=True)
        tb_b = canvas_draw.textbbox((0, 0), top_brand, font=tb_font)
        tb_w = tb_b[2] - tb_b[0]
        total_brand_w = tb_w + (36 if logo_img else 0)
        brand_start_x = (cls.CANVAS_WIDTH - total_brand_w) // 2
        brand_y = 42

        if logo_img:
            canvas.paste(logo_img, (brand_start_x, brand_y - 3), logo_img)
            canvas_draw.text((brand_start_x + 36, brand_y), top_brand, font=tb_font, fill=(255, 255, 255, 215))
        else:
            canvas_draw.text((brand_start_x, brand_y), top_brand, font=tb_font, fill=(255, 255, 255, 215))

        # 封面大标牌 (高级香槟金发光卡片)
        main_title = cover_title or "今 日 份 神 仙 锁 屏"
        t_font = get_text_font(size=42, bold=True)
        tb = canvas_draw.textbbox((0, 0), main_title, font=t_font)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]

        card_pad_x = 40
        card_pad_y = 12
        card_w = tw + card_pad_x * 2
        card_h = th + card_pad_y * 2
        card_x = (cls.CANVAS_WIDTH - card_w) // 2
        card_y = 86

        canvas_draw.rounded_rectangle(
            (card_x, card_y, card_x + card_w, card_y + card_h),
            radius=card_h // 2,
            fill=(24, 26, 34, 240),
            outline=(255, 215, 120, 180),
            width=2,
        )
        canvas_draw.text((card_x + card_pad_x, card_y + card_pad_y - 2), main_title, font=t_font, fill=(255, 225, 130, 255))

        # 副标题
        sub_font = get_text_font(size=22, bold=False)
        sub_b = canvas_draw.textbbox((0, 0), cover_subtitle, font=sub_font)
        sub_w = sub_b[2] - sub_b[0]
        canvas_draw.text(((cls.CANVAS_WIDTH - sub_w) // 2, card_y + card_h + 10), cover_subtitle, font=sub_font, fill=(220, 225, 240, 230))

        # 5. 底部滑动提示条
        footer_tip = "右 滑 查 看 18 款 全 套 上 屏 效 果  >>>"
        ft_font = get_text_font(size=21, bold=True)
        ft_b = canvas_draw.textbbox((0, 0), footer_tip, font=ft_font)
        ft_w = ft_b[2] - ft_b[0]
        canvas_draw.text(((cls.CANVAS_WIDTH - ft_w) // 2, cls.CANVAS_HEIGHT - 38), footer_tip, font=ft_font, fill=(255, 255, 255, 210))

        return canvas.convert("RGB")

    @classmethod
    def render_guide_tail(
        cls,
        total_count: int = 18,
    ) -> Image.Image:
        """
        生成顶级科技美学质感尾图：
        - 暗夜星云微光渐变背景
        - 修复顶部徽章颜色：采用高对比度黑金发光胶囊，纯净清晰，彻底解决泛白看不清问题
        - 毛玻璃质感 3 步指南卡片
        - 至尊黑金 VIP 礼包与立体发光黄金按钮
        """
        # 1. 创建深邃高级暗夜星云渐变底图
        canvas = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (15, 17, 24, 255))
        grad = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(grad)

        for y in range(cls.CANVAS_HEIGHT):
            factor = y / cls.CANVAS_HEIGHT
            r = int(14 * (1 - factor) + 20 * factor)
            g = int(18 * (1 - factor) + 18 * factor)
            b = int(28 * (1 - factor) + 28 * factor)
            g_draw.line([(0, y), (cls.CANVAS_WIDTH, y)], fill=(r, g, b, 255))
        canvas = Image.alpha_composite(canvas, grad)

        # 顶部和中间添加紫金环境光晕
        glow = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((cls.CANVAS_WIDTH // 2 - 350, -100, cls.CANVAS_WIDTH // 2 + 350, 450), fill=(45, 55, 95, 120))
        glow_draw.ellipse((cls.CANVAS_WIDTH // 2 - 400, 750, cls.CANVAS_WIDTH // 2 + 400, 1400), fill=(65, 38, 85, 95))
        glow = glow.filter(ImageFilter.GaussianBlur(110))
        canvas = Image.alpha_composite(canvas, glow)

        # 2. 绘制卡片层 (使用 alpha_composite 确保毛玻璃透明度 100% 正确)
        cards_layer = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(cards_layer)

        # (a) 顶部高清晰黑金微胶囊 (深黑金底 + 鲜明金边 + 纯净高对比度)
        tag_text = "★   4K  ULTRA  HD   ·   无 损 原 图 获 取   ★"
        tag_font = get_text_font(size=20, bold=True)
        tag_b = c_draw.textbbox((0, 0), tag_text, font=tag_font)
        tag_w = tag_b[2] - tag_b[0]
        tag_h = tag_b[3] - tag_b[1]
        t_pad_x = 28
        t_pad_y = 8
        t_w = tag_w + t_pad_x * 2
        t_h = tag_h + t_pad_y * 2
        t_x = (cls.CANVAS_WIDTH - t_w) // 2
        t_y = 100

        c_draw.rounded_rectangle(
            (t_x, t_y, t_x + t_w, t_y + t_h),
            radius=t_h // 2,
            fill=(32, 28, 42, 235),
            outline=(245, 205, 120, 220),
            width=1,
        )

        # (b) 中间三大步骤毛玻璃卡片
        card_x = 65
        card_w = cls.CANVAS_WIDTH - card_x * 2
        card_h = 165
        gap = 20
        card_start_y = 285

        steps = [
            ("01", "打开微信搜索小程序", "在微信搜一搜输入「本我壁纸」即可进入应用"),
            ("02", "输入壁纸编号直达", "在首页搜索框输入笔记/贴图上标注的「#编号」"),
            ("03", "无损保存即刻上屏", "4K超清原图一键保存，支持沉浸式时钟与灵动岛预览"),
        ]

        num_font = get_clock_font(size=64)
        step_t_font = get_text_font(size=28, bold=True)
        step_d_font = get_text_font(size=21, bold=False)

        for i, (num, stitle, sdesc) in enumerate(steps):
            cy = card_start_y + i * (card_h + gap)
            c_draw.rounded_rectangle(
                (card_x, cy, card_x + card_w, cy + card_h),
                radius=24,
                fill=(28, 32, 46, 210),
                outline=(255, 255, 255, 45),
                width=1,
            )
            c_draw.text((card_x + 38, cy + 45), num, font=num_font, fill=(255, 215, 120, 245))
            c_draw.line([(card_x + 130, cy + 40), (card_x + 130, cy + card_h - 40)], fill=(255, 255, 255, 35), width=1)
            c_draw.text((card_x + 155, cy + 42), stitle, font=step_t_font, fill=(255, 255, 255, 245))
            c_draw.text((card_x + 155, cy + 92), sdesc, font=step_d_font, fill=(170, 178, 195, 215))

        # (c) 下方至尊 VIP 礼遇卡片
        benefit_y = card_start_y + 3 * (card_h + gap) + 16
        benefit_h = 360

        c_draw.rounded_rectangle(
            (card_x, benefit_y, card_x + card_w, benefit_y + benefit_h),
            radius=28,
            fill=(35, 28, 48, 225),
            outline=(210, 160, 255, 110),
            width=1,
        )

        canvas = Image.alpha_composite(canvas, cards_layer)

        # 3. 绘制文字与前景层
        draw = ImageDraw.Draw(canvas)

        # 顶部品牌微标带 Logo
        logo_img = cls.get_app_logo_image(size=26)
        top_brand = "Ego Wallpapers · 本我壁纸"
        tb_font = get_text_font(size=20, bold=True)
        tb_b = draw.textbbox((0, 0), top_brand, font=tb_font)
        tb_w = tb_b[2] - tb_b[0]
        total_brand_w = tb_w + (36 if logo_img else 0)
        brand_start_x = (cls.CANVAS_WIDTH - total_brand_w) // 2
        brand_y = 52

        if logo_img:
            canvas.paste(logo_img, (brand_start_x, brand_y - 3), logo_img)
            draw.text((brand_start_x + 36, brand_y), top_brand, font=tb_font, fill=(255, 255, 255, 190))
        else:
            draw.text((brand_start_x, brand_y), top_brand, font=tb_font, fill=(255, 255, 255, 190))

        # 顶部徽章文字 (鲜明香槟金，带柔和微暗影，极度清晰醒目)
        draw.text((t_x + t_pad_x + 1, t_y + t_pad_y - 1), tag_text, font=tag_font, fill=(0, 0, 0, 180))
        draw.text((t_x + t_pad_x, t_y + t_pad_y - 2), tag_text, font=tag_font, fill=(255, 232, 150, 255))

        # 主标题与副标题
        m_title = "三 步 直 达 超 清 锁 屏"
        mt_font = get_text_font(size=44, bold=True)
        mt_b = draw.textbbox((0, 0), m_title, font=mt_font)
        draw.text(((cls.CANVAS_WIDTH - (mt_b[2] - mt_b[0])) // 2, 160), m_title, font=mt_font, fill=(255, 255, 255, 255))

        sub_title = "一键设为锁屏  ·  4K无损画质  ·  适配iOS锁屏与灵动岛"
        st_font = get_text_font(size=22, bold=False)
        st_b = draw.textbbox((0, 0), sub_title, font=st_font)
        draw.text(((cls.CANVAS_WIDTH - (st_b[2] - st_b[0])) // 2, 222), sub_title, font=st_font, fill=(160, 168, 190, 210))

        # VIP 礼遇标题
        b_head = "★   读 者 专 属 限 时 礼 遇   ★"
        bh_font = get_text_font(size=24, bold=True)
        bh_b = draw.textbbox((0, 0), b_head, font=bh_font)
        draw.text(((cls.CANVAS_WIDTH - (bh_b[2] - bh_b[0])) // 2, benefit_y + 40), b_head, font=bh_font, fill=(235, 205, 255, 240))

        # 核心 CTA 黄金按钮胶囊 (发光立体按钮)
        cta_w = card_w - 70
        cta_h = 96
        cta_x = card_x + 35
        cta_y = benefit_y + 95

        # 按钮发光阴影
        b_shadow = Image.new("RGBA", (cls.CANVAS_WIDTH, cls.CANVAS_HEIGHT), (0, 0, 0, 0))
        bs_draw = ImageDraw.Draw(b_shadow)
        bs_draw.rounded_rectangle((cta_x + 10, cta_y + 12, cta_x + cta_w - 10, cta_y + cta_h + 16), radius=cta_h // 2, fill=(255, 210, 90, 80))
        b_shadow = b_shadow.filter(ImageFilter.GaussianBlur(16))
        canvas = Image.alpha_composite(canvas, b_shadow)

        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            (cta_x, cta_y, cta_x + cta_w, cta_y + cta_h),
            radius=cta_h // 2,
            fill=(255, 225, 130, 255),
            outline=(255, 245, 190, 255),
            width=2,
        )

        cta_title = "在评论区 / 后台留言【体验码】"
        cta_font = get_text_font(size=33, bold=True)
        ct_b = draw.textbbox((0, 0), cta_title, font=cta_font)
        draw.text(((cls.CANVAS_WIDTH - (ct_b[2] - ct_b[0])) // 2, cta_y + 16), cta_title, font=cta_font, fill=(28, 20, 10, 255))

        cta_sub = "私信自动发放 3 天 VIP 专属兑换码"
        cs_font = get_text_font(size=20, bold=False)
        cs_b = draw.textbbox((0, 0), cta_sub, font=cs_font)
        draw.text(((cls.CANVAS_WIDTH - (cs_b[2] - cs_b[0])) // 2, cta_y + 58), cta_sub, font=cs_font, fill=(75, 52, 22, 230))

        v_tip1 = "全站 4K 超清壁纸无限制畅享 · 每日数量有限先到先得"
        vt_font = get_text_font(size=21, bold=False)
        vt_b = draw.textbbox((0, 0), v_tip1, font=vt_font)
        draw.text(((cls.CANVAS_WIDTH - (vt_b[2] - vt_b[0])) // 2, benefit_y + 225), v_tip1, font=vt_font, fill=(200, 195, 225, 220))

        v_tip2 = "换一张壁纸，换一个好心情 · 感谢每一位朋友的支持与喜欢"
        vt2_font = get_text_font(size=20, bold=False)
        vt2_b = draw.textbbox((0, 0), v_tip2, font=vt2_font)
        draw.text(((cls.CANVAS_WIDTH - (vt2_b[2] - vt2_b[0])) // 2, benefit_y + 270), v_tip2, font=vt2_font, fill=(150, 145, 175, 190))

        # 底部页脚
        bot_brand = "Ego Wallpapers · 本我壁纸"
        bb_font = get_text_font(size=19, bold=True)
        bb_b = draw.textbbox((0, 0), bot_brand, font=bb_font)
        draw.text(((cls.CANVAS_WIDTH - (bb_b[2] - bb_b[0])) // 2, cls.CANVAS_HEIGHT - 60), bot_brand, font=bb_font, fill=(110, 115, 135, 160))

        return canvas.convert("RGB")
