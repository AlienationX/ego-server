from pathlib import Path

import boto3
from django.conf import settings
from loguru import logger

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.DECOUPLE_CONFIG("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=settings.DECOUPLE_CONFIG("AWS_SECRET_ACCESS_KEY"),
    region_name="eu-north-1",
)

bucket_name = "wallpaper-kpze6c"


def upload_file_to_s3(file: Path, bucket_name=bucket_name, s3_prefix=""):
    try:
        files = [file, file.with_name(f"{file.stem}_small.webp")]
        for f in files:
            if not f.exists():
                logger.warning(f"File {f} does not exist, skipping upload.")
                continue

            filename = f.name
            s3_key = s3_prefix + filename

            try:
                # 检查文件是否已存在, 不存在报错 An error occurred (404) when calling the HeadObject operation: Not Found
                response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    logger.warning(f"File {f} already exists in s3, skipping upload.")
            except Exception:
                s3_client.upload_file(Bucket=bucket_name, Key=s3_key, Filename=f)
                logger.info(f"Uploaded {f} -> s3://{bucket_name}/{s3_key}")

    except Exception as e:
        logger.error(f"Failed to upload {file}: {str(e)}")
        return (file, str(e))
