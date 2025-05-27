import boto3
from pathlib import Path
from loguru import logger

output_dir = Path(__file__).parent / 's3_wallpaper_bucket'
output_dir.mkdir(parents=True, exist_ok=True)

s3_client = boto3.client('s3')

bucket_name = 'wallpaper-kpze6c'
response = s3_client.list_objects(Bucket=bucket_name)

# TODO 多进程下载
for content in response.get('Contents', [])[:10]:
    s3_key  = content['Key']
    local_path = output_dir / s3_key
    local_path.parent.mkdir(parents=True, exist_ok=True)  # 确保父目录存在
    s3_client.download_file(bucket_name, s3_key, local_path)
    logger.info(f"Downloaded s3://{bucket_name}/{s3_key} -> {local_path}")