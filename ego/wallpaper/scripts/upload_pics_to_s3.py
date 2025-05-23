import boto3

# 快速上传整个目录
# aws s3 sync project_data/ s3://my-bucket/backup/project_data/

s3_client = boto3.client('s3')

response = s3_client.list_buckets()
print(response)

bucket_name = 'your-bucket-name'