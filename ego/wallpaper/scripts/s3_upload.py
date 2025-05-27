import boto3
from pathlib import Path
from loguru import logger

# 目前3个地方需要使用的图片 banner、classify、pics

s3_client = boto3.client('s3')
bucket_name = 'wallpaper-kpze6c'
input_dir = Path(__file__).parent / 'images'

error_list = []


def upload_files_to_s3(local_dir, bucket_name, s3_prefix=''):
    """
    上传本地目录下的所有文件到 S3
    :param local_dir: 本地目录路径（需以斜杠结尾）
    :param bucket_name: S3 存储桶名称
    :param s3_prefix: S3 目标前缀（如 'data/'）
    """
    for p in local_dir.rglob('*'):
        if p.is_file() and p.suffix.lower() in {".jpg", ".png", ".webp"} and not p.name.startswith("."):
            local_path = str(p)
            filename = p.name
            s3_key = s3_prefix + filename
            try:
                s3_client.upload_file(
                    Filename=local_path,
                    Bucket=bucket_name,
                    Key=s3_key
                )
                logger.info(f"Uploaded {local_path} -> s3://{bucket_name}/{s3_key}")
            except Exception as e:
                logger.error(f"Failed to upload {local_path}: {str(e)}")
                error_list.append((local_path, str(e)))

    if error_list:
        logger.error("Some files failed to upload:")
        for local_path, error in error_list:
            logger.error(f"{local_path}: {error}")


if __name__ == "__main__":
    # 上传 banner 目录下的图片
    # upload_files_to_s3(input_dir / 'banner', bucket_name, 'banner/')

    # 上传 classify 目录下的图片
    upload_files_to_s3(input_dir / 'classify', bucket_name, 'classify/')

    # 上传 pics 目录下的图片
    # for i in range(1, 16):
    #     logger.info(f'Uploading classify_{i} images to S3...')
    #     upload_files_to_s3(input_dir / f'classify_{i}', bucket_name, f'pics/classify_{i}/')
