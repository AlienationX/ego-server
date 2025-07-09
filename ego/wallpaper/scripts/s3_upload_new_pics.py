import boto3
import json
import random
from datetime import datetime
from PIL import Image
from pathlib import Path
from loguru import logger

# pip install Pillow

s3_client = boto3.client('s3')

bucket_name = 'wallpaper-kpze6c'
all_sql = []


with open(Path(__file__).parent / 'images/pics/classify_bing/bing_daily_data.json', "r") as f:
    bing_daily_data = json.load(f)


def get_files(local_dir):
    """
    获取指定目录下的所有图片文件
    :param local_dir: 本地目录路径
    :return: 图片文件列表
    """
    return [p for p in local_dir.rglob('*') if p.is_file() and p.suffix.lower() in {".jpg", ".png"} and not p.name.startswith(".")]


def generate_thumbs(file, max_size=(450, 450)):
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


def upload_files_to_s3(file, bucket_name, s3_prefix=''):
    try:
        files = [file, file.with_name(f"{file.stem}_small.webp")]
        for f in files:
            if not f.exists():
                logger.warning(f"File {f} does not exist, skipping upload.")
                continue

            filename = f.name
            s3_key = s3_prefix + filename
            s3_client.upload_file(
                Filename=file,
                Bucket=bucket_name,
                Key=s3_key
            )

            if f == file:
                generate_sql(file, s3_key)

            logger.info(f"Uploaded {f} -> s3://{bucket_name}/{s3_key}")
    except Exception as e:
        logger.error(f"Failed to upload {file}: {str(e)}")
        return ((file, str(e)))


def generate_sql(file, s3_key):
    target_date = file.name.split('-')[0]
    desc_bing_data = [
        f"{entry['date']} - {entry['title']}: {entry['description']}"
        for entry in bing_daily_data if entry['date'] == target_date
    ]

    classify_id = 62  # 必应壁纸分类ID
    subject_id = 'NULL'  # 必应壁纸主题ID
    picurl = s3_key
    description = desc_bing_data[0] if desc_bing_data else "和卡比兽一起睡觉吧！"
    tabs = '宝可梦,卡比兽,睡觉,pokemon,kabigon,sleep'
    score = round(random.uniform(4, 5), 1)
    publisher = ""

    sql = f"INSERT INTO wallpaper_wall (picurl, description, tabs, score, publisher, is_active, created_at, updated_at, classify_id) VALUES ('{picurl}', '{description}', '{tabs}', {score}, '{publisher}', TRUE, NOW(), NOW(), {classify_id});"
    all_sql.append(sql)


if __name__ == "__main__":
    folder_dir = 'pics/classify_pokemon_sleep/'
    incremental_time = '2021-06-03 10:03'  # 增量上传时间
    max_time = '1900-01-01'  # 最大时间戳
    newest_file = ''   # 最新文件名

    local_dir = Path(__file__).parent / 'images' / folder_dir
    files = get_files(local_dir)
    files.sort(key=lambda x: x.name.lower())  # 按文件名排序
    for file in files:
        mod_timestamp = file.stat().st_mtime
        mod_time = datetime.fromtimestamp(mod_timestamp).strftime('%Y-%m-%d %H:%M:%S')

        if mod_time < incremental_time:
            continue
        else:
            # print(f"Processing file: {file.name}, modified at {mod_time}")
            if max_time < mod_time:
                max_time = mod_time
                newest_file = file.name

        # 生成缩略图
        generate_thumbs(file)
        # 上传到 S3
        upload_files_to_s3(file, bucket_name, s3_prefix=folder_dir)

    with open(Path(__file__).parent / 's3_upload_new.sql', 'a') as f:
        if all_sql:
            f.write(f"-- {datetime.now()}\n")
            for sql in all_sql:
                f.write(sql + '\n')
            f.write(f"\n")

    with open(Path(__file__).parent / 's3_upload_new.log', 'a') as f:
        f.write(f"{datetime.now()}, {folder_dir}, {newest_file}, {max_time}\n",)

    # 单独生成分类封面的缩略图
    # generate_thumbs(Path(__file__).parent / 'images/pics' / 'classify_pokemon_sleep/0e3b294beb09239a0625d82a2e2c0561.jpg')
