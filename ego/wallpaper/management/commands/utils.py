from loguru import logger
from PIL import Image

# pip install Pillow


def generate_thumbs(file, max_size=(520, 520)):
    # 设置缩略图的最大宽度和高度（单位：像素）。例如 (200, 200) 表示缩略图最长边不超过 200 像素。
    with Image.open(file) as img:
        # 保持宽高比时自动计算尺寸
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 保存缩略图（支持JPEG/PNG等格式）
        output_file = file.with_name(f"{file.stem}_small.webp")
        logger.info(f"Generating thumbnail {output_file}")

        # ​​quality​​（仅适用于有损压缩格式）：
        # ​​JPEG​​：范围 1-95（值越大质量越高，默认 75）。
        # ​​WEBP​​：范围 0-100（默认 80）。
        # ​​optimize​​（适用于 PNG）：
        # 启用优化压缩（True/False），减小文件体积。
        img.save(output_file, "WEBP", quality=85)
