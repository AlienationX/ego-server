"""本地水印检测（启发式，不依赖模型/OCR）。

思路：平台水印（小红书号、微博 ID、域名等）多为半透明文字，表现为
"边缘明显但局部灰度差不大"的细笔画，并且集中在图片底部/右下角；
部分图库水印则是同一组字形在全图平铺。这里用 cv2 的 top-hat 提取这类
细笔画，再按位置先验和成行规则打分。

局限：无法理解语义，画面自带的底部文案/低对比小字可能误报；
顶部水印、不透明角标、与背景几乎同色的淡字可能漏报。
仅用于上传预览提示，不参与入库。
"""

import cv2
import numpy as np

# 分析前缩放到的最长边，兼顾速度与稳定
MAX_SIDE = 1024

# 命中阈值（score >= 阈值判定为有水印）
SCORE_THRESHOLD = 0.5

# 细笔画响应阈值：top-hat 提取比背景更亮/更暗的细结构（水印笔画通常 2-6px）
STROKE_THRESH = 12
STROKE_KERNEL = (7, 7)

# 半透明文字的补充特征：边缘有响应，但和局部背景的灰度差不大
EDGE_MIN = 20
DIFF_MAX = 80

# 候选文字行：高度、宽高比、宽度、笔画密度约束
LINE_MIN_HEIGHT = 8
LINE_MAX_HEIGHT = 90
LINE_MIN_ASPECT = 2.0
LINE_MIN_WIDTH = 25
LINE_MIN_DENSITY = 0.6
LINE_MAX_DENSITY = 0.95
LINE_MIN_AREA = 60
# 水印文字行通常只占图片宽度的一小段，且为半透明（与局部背景灰度差适中）
LINE_MIN_WIDTH_RATIO = 0.05
LINE_MAX_WIDTH_RATIO = 0.55
LINE_MAX_MEAN_DIFF = 45

# 位置先验区域 (x0, y0, x1, y1)，按图片宽高的比例。
# 平台水印集中在底部与右下角，限制在低位可显著降低画面自带文案的误报。
WEIGHTED_BANDS = (
    (0.0, 0.88, 1.0, 1.0),  # 底部整条
    (0.6, 0.82, 1.0, 1.0),  # 右下角
    (0.0, 0.82, 0.4, 1.0),  # 左下角
)


def _read_gray(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法读取图片: {path}")
    height, width = image.shape[:2]
    scale = MAX_SIDE / max(height, width)
    if scale < 1:
        image = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _stroke_mask(gray):
    """提取"水印笔画"候选：细亮/细暗结构 + 半透明文字的低对比边缘。"""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, STROKE_KERNEL)
    bright = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    dark = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    response = cv2.max(bright, dark)

    background = cv2.medianBlur(gray, 15)
    diff = cv2.absdiff(gray, background)
    edge = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))

    thin = response > STROKE_THRESH
    translucent = (edge > EDGE_MIN) & (diff < DIFF_MAX)
    mask = np.where(thin | translucent, 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return mask, diff


def _text_lines(mask, diff):
    """把笔画横向连接成"文字行"，返回候选行 (x, y, w, h, aspect)。"""
    height, width = mask.shape
    min_width = max(LINE_MIN_WIDTH, width * LINE_MIN_WIDTH_RATIO)
    max_width = width * LINE_MAX_WIDTH_RATIO
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((1, 11), np.uint8))
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(closed, connectivity=8)

    lines = []
    for i in range(1, count):
        x, y, w, h, area = stats[i]
        if area < LINE_MIN_AREA:
            continue
        if h < LINE_MIN_HEIGHT or h > LINE_MAX_HEIGHT:
            continue
        if w < min_width or w > max_width:
            continue
        aspect = w / max(h, 1)
        if aspect < LINE_MIN_ASPECT:
            continue
        density = area / (w * h)
        if density < LINE_MIN_DENSITY or density > LINE_MAX_DENSITY:
            continue
        # 水印是半透明叠加：行内与局部背景的灰度差不会太大
        if float(diff[y : y + h, x : x + w].mean()) > LINE_MAX_MEAN_DIFF:
            continue
        lines.append((x, y, w, h, aspect))
    return lines, (height, width)


def _in_band(line, band, shape):
    x, y, w, h, _ = line
    height, width = shape
    bx0, by0, bx1, by1 = band
    band_x0, band_y0, band_x1, band_y1 = bx0 * width, by0 * height, bx1 * width, by1 * height
    cx, cy = x + w / 2, y + h / 2
    return band_x0 <= cx <= band_x1 and band_y0 <= cy <= band_y1


def analyze_watermark(path):
    """返回 {"has_watermark": bool, "score": float, "lines": int}。"""
    try:
        gray = _read_gray(path)
        mask, diff = _stroke_mask(gray)
        lines, shape = _text_lines(mask, diff)

        score = 0.0
        hit_bands = set()
        for line in lines:
            for index, band in enumerate(WEIGHTED_BANDS):
                if _in_band(line, band, shape):
                    if index not in hit_bands:
                        # 第一条落在位置先验区域内权重最高，后续递减
                        score += 0.5 if not hit_bands else 0.15
                        hit_bands.add(index)
                    break

        # 多处出现同类文字行，通常是平铺/重复水印
        if len(hit_bands) >= 2:
            score += 0.2

        score = min(score, 1.0)
        return {"has_watermark": score >= SCORE_THRESHOLD, "score": round(score, 2), "lines": len(lines)}
    except Exception:  # noqa: BLE001 检测失败不影响上传流程，统一降级为"无水印"
        return {"has_watermark": False, "score": 0.0, "lines": 0}


def detect_watermark(path):
    """判断图片是否带水印。"""
    return analyze_watermark(path)["has_watermark"]
