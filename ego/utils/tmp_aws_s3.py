import boto3
from botocore.exceptions import ClientError

# s3_client：提供底层的 API 接口，直接与 AWS S3 服务进行交互。它使用的是 低级 API，更接近 AWS 的原生 API，允许你执行各种 S3 操作，比如上传文件、列出桶、删除文件等。每个操作都对应于一个函数调用。
# s3_resource：提供更高层次的抽象，简化了与 S3 交互的代码。它使用的是 高级 API，通过对象模型来访问 S3 资源（例如 Bucket、Object）。s3_resource 的设计更为面向对象，提供了更简洁的接口和易于理解的操作方法。

# 快速上传整个目录
# aws s3 sync project_data/ s3://my-bucket/backup/project_data/

# 设置使用的账户，指定使用的profile
# session = boto3.Session()
# print("当前使用的 Profile:", session.profile_name)
# s3_client = session.client('s3')

s3_client = boto3.client('s3')

# aws s3 ls
response = s3_client.list_buckets()
print('-' * 20, response)
print('-' * 20, response['Buckets'])
for content in response.get('Buckets', []):
    print(content['Name'])
    
bucket_names = [bucket['Name'] for bucket in response['Buckets']]
print("Bucket Names:", bucket_names)


# 检查桶是否存在
bucket_name = 'wallpaper111-kpze6c'
try:
    s3_client.head_bucket(Bucket=bucket_name)
    print(f"Bucket '{bucket_name}' already exists.")
except ClientError as e:
    if e.response['Error']['Code'] == 'NoSuchBucket':
        # 桶不存在，创建一个新的桶
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' created successfully.")
    else:
        # 处理其他错误
        print(f"Error checking bucket: {e}")


bucket_name = 'wallpaper-kpze6c'
response = s3_client.list_objects(Bucket=bucket_name)

for content in response.get('Contents', [])[:10]:
    print(content['Key'])


# 重命名 S3 中的文件
# 旧文件名和新文件名
old_key = 'old-filename.txt'
new_key = 'new-filename.txt'

# 复制文件到新位置
s3_client.copy_object(
    Bucket=bucket_name,
    CopySource={'Bucket': bucket_name, 'Key': old_key},
    Key=new_key
)

# 删除旧文件
s3_client.delete_object(Bucket=bucket_name, Key=old_key)

print(f'File renamed from {old_key} to {new_key}')