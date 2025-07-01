import json
import os
import jwt

# 不同触发器（API Gateway、S3、DynamoDB 等）生成结构差异显著的 event 对象，需按触发器类型解析

# API Gateway 触发的 Lambda 函数示例，处理 GET 和 POST 请求
# {
#   "httpMethod": "POST",
#   "path": "/users",
#   "headers": {"Content-Type": "application/json"},
#   "queryStringParameters": {"limit": "10"},  # 查询参数
#   "body": "{\"name\":\"Alice\", \"age\":30}",  # 请求体（JSON 字符串）
#   "isBase64Encoded": False  # 是否Base64编码
# }


def lambda_handler(event, context):
    """处理 API Gateway 触发的 Lambda 函数，支持 GET 和 POST 请求。"""

    print("Received event:", json.dumps(event, indent=2))
    token = event["headers"].get("Authorization", "").replace("Bearer ", "")

    try:
        secret = os.environ["JWT_SECRET"]
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        username = payload["user"]
    except jwt.ExpiredSignatureError:
        return {"statusCode": 401, "body": json.dumps({"error": "Token expired"})}
    except jwt.InvalidTokenError:
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid token"})}

    if event["httpMethod"] == "GET":
        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Hello {username} from Lambda"}),
            "headers": {"Content-Type": "application/json"}
        }

    if event["httpMethod"] == "POST":
        body = json.loads(event["body"])
        name = body.get("name", "Anonymous")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Hello, {name}", "user": username}),
            "headers": {"Content-Type": "application/json"}
        }

    return {
        "statusCode": 405,
        "body": json.dumps({"error": "Method Not Allowed"}),
        "headers": {"Content-Type": "application/json"}
    }
