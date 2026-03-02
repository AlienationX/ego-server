from pathlib import Path

from django.conf import settings
from loguru import logger
from qcloud_cos import CosConfig, CosS3Client

# 用户的 SecretId，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
secret_id = settings.DECOUPLE_CONFIG("COS_SECRET_ID")

# 用户的 SecretKey，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
secret_key = settings.DECOUPLE_CONFIG("COS_SECRET_KEY")

# 替换为用户的 region，已创建桶归属的 region 可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
region = "ap-beijing"

# COS 支持的所有 region 列表参见 https://cloud.tencent.com/document/product/436/6224
token = None  # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
scheme = "https"  # 指定使用 http/https 协议来访问 COS，默认为 https，可不填

cos_config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
cos_client = CosS3Client(cos_config)

bucket_name = "wp-1328701250"


def upload_file_to_cos(file: Path, bucket_name=bucket_name, cos_prefix=""):
    # response = client.upload_file(
    #     Bucket=bucket_name, Key="exampleobject", LocalFilePath="local.txt", EnableMD5=False, progress_callback=None
    # )
    try:
        files = [file, file.with_name(f"{file.stem}_small.webp")]
        for f in files:
            if not f.exists():
                logger.warning(f"File {f} does not exist, skipping upload.")
                continue

            filename = f.name
            cos_key = cos_prefix + filename

            response = cos_client.object_exists(Bucket=bucket_name, Key=cos_key)

            # response = True or False
            if response:
                logger.warning(f"File {f} already exists in COS, skipping upload.")
            else:
                cos_client.upload_file(Bucket=bucket_name, Key=cos_key, LocalFilePath=f)
                logger.info(f"Uploaded {f} -> cos://{bucket_name}/{cos_key}")

    except Exception as e:
        logger.error(f"Failed to upload {file}: {str(e)}")
        return (file, str(e))
