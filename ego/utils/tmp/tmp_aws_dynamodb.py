import boto3

# code examples 强烈推荐
# https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/service_code_examples.html

"""
通过awscli设置密钥，或者代码读取环境变量，不推荐硬编码到代码中
pip install awscli
aws configure

要求输入4个配置：
AWS Access Key ID [None]: 
AWS Secret Access Key [None]:
Default region name [None]: 
Default output format [None]:

存储位置: ~/.aws/credentials

数据库权限不足，需要在aws新建用户、组，将权限分配给组即可

# pip install boto3
"""

# 使用显式的 AWS 访问密钥和秘钥
dynamodb = boto3.resource(
    'dynamodb',
    # region_name='eu-north-1',  # 你要连接的区域
    # aws_access_key_id='xxx',
    # aws_secret_access_key='xxx'
)

for table in dynamodb.tables.all():
    print(table)
    print(table.name)

######## 
table = dynamodb.Table('test_score')
response = table.scan()

for item in response.get('Items'):
    print(item)

