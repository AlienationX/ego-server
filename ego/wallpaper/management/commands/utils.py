import boto3
from loguru import logger
from PIL import Image

# pip install Pillow

s3_client = boto3.client("s3")

bucket_name = "wallpaper-kpze6c"


def generate_thumbs(file, max_size=(520, 520)):
    # 设置缩略图的最大宽度和高度（单位：像素）。例如 (200, 200) 表示缩略图最长边不超过 200 像素。
    with Image.open(file) as img:
        # 保持宽高比时自动计算尺寸
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 保存缩略图（支持JPEG/PNG等格式）
        output_file = file.with_name(f"{file.stem}_small.webp")
        logger.info(f"Generating thumbnail for {file.name} to {output_file}")
        # ​​quality​​（仅适用于有损压缩格式）：
        # ​​JPEG​​：范围 1-95（值越大质量越高，默认 75）。
        # ​​WEBP​​：范围 0-100（默认 80）。
        # ​​optimize​​（适用于 PNG）：
        # 启用优化压缩（True/False），减小文件体积。
        img.save(output_file, "WEBP", quality=85)


def upload_files_to_s3(file, bucket_name=bucket_name, s3_prefix=""):
    try:
        files = [file, file.with_name(f"{file.stem}_small.webp")]
        for f in files:
            if not f.exists():
                logger.warning(f"File {f} does not exist, skipping upload.")
                continue

            filename = f.name
            s3_key = s3_prefix + filename
            s3_client.upload_file(Filename=f, Bucket=bucket_name, Key=s3_key)

            logger.info(f"Uploaded {f} -> s3://{bucket_name}/{s3_key}")
    except Exception as e:
        logger.error(f"Failed to upload {file}: {str(e)}")
        return (file, str(e))
