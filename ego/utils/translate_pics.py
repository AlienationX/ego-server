from pathlib import Path
from PIL import Image

from loguru import logger


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    units = ("B", "KB", "MB", "GB", "TB")
    unit_index = 0
    while size_bytes >= 1024 and unit_index < 4:
        size_bytes /= 1024
        unit_index += 1
    return f"{size_bytes:.2f} {units[unit_index]}"


def save_image_with_metadata(file, output_path):
    with Image.open(file) as img:
        # 1. 提取原始元数据
        exif_data = img.info.get("exif", b"")
        # 2. 保存图片参数设置
        save_params = {
            "format": "JPEG",
            "quality": 95,         # # 最高质量（1-95范围）95是PIL中公认的视觉无损质量级别，高于95时，文件大小显著增加但几乎看不出质量提升
            "optimize": True,      # 启用压缩优化
            "subsampling": 0,      # 4:4:4 色彩采样（最高质量）
            "exif": exif_data      # 包含所有元数据
        }
        # 3. 保存图片
        img.save(output_path / file.name, **save_params)


def translate_pics(input_path: Path, output_path: Path):

    for p in input_path.iterdir():
        if p.is_file() and p.suffix.lower() in {".jpg", ".png"} and not p.name.startswith("."):
            size_bytes = p.stat().st_size
            human_size = convert_size(size_bytes)
            # logger.info(f"{p.name}  {size_bytes} 字节, {human_size}")
            if size_bytes > 1024 * 1024 * 2:
                # 大于 2M 的照片才进行转换
                logger.info(f"{p.name}  {size_bytes} 字节, {human_size}")
                save_image_with_metadata(p, output_path)

    files = [p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".png"} and not p.name.startswith(".") and p.stat().st_size > 1024*1024*2]
    # files.sort(key=lambda x: x.stat().st_size)
    total_size = sum(file.stat().st_size for file in files)
    print("raw", convert_size(total_size))

    files = [p for p in output_path.iterdir() if p.is_file()]
    total_size = sum(file.stat().st_size for file in files)
    print("new", convert_size(total_size))


if __name__ == "__main__":
    input_path = Path("/Users/tangzy/baby")
    output_path = Path(__file__).parent / "output_pics"
    output_path.mkdir(parents=True, exist_ok=True)

    translate_pics(input_path, output_path)
