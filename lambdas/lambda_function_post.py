import json

# 示例 Lambda 函数，处理 POST 请求并返信息（只返回body的内容）
# 这个函数可以通过 API Gateway 触发，支持查询参数
# 例如访问以下 URL 时：
# post https://qddt9g4knl.execute-api.eu-north-1.amazonaws.com/dev/test-post
# https://qddt9g4knl.execute-api.eu-north-1.amazonaws.com/dev/test-get?name=John


def lambda_handler(event, context):
    print("传入的event", event)
    # API Gateway 传入的url参数会放到  event 的 queryStringParameters 字段里
    # 对于 POST 请求的数据会放到 event 的 body 字段中
    body = event.get('body') or json.dumps({}) 
    data = json.loads(body)  # 解析JSON数据

    name = data.get('name', 'Guest')  # 获取name字段，默认值为'Guest'
    email = data.get('email', 'unknown')

    # # 返回内容必须写到body中，固定格式不能更改。下面的返回会报错
    # return {'code': 200, 'data': f"Hello {name}", 'message': 'success'}
    # 正确的返回格式，必须使用json返回
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": f"Received {name} ({email})"})
    }
