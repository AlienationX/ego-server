import json

# 示例 Lambda 函数，处理 GET 请求并返回问候语（只返回body的内容）
# 这个函数可以通过 函数URL 或 API Gateway 触发，支持查询参数
# 例如访问以下 函数URL 时：
# https://czvlgzfpk5hevtbmt4ojebfviy0lsrxn.lambda-url.eu-north-1.on.aws/?name=shuli
# 或者通过 API Gateway 触发：
# https://qddt9g4knl.execute-api.eu-north-1.amazonaws.com/dev/test-get
# https://qddt9g4knl.execute-api.eu-north-1.amazonaws.com/dev/test-get?name=John


def lambda_handler(event, context):
    print("传入的event", event)
    # API Gateway 传入的url参数会放到  event 的 queryStringParameters 字段里
    query_params = event.get('queryStringParameters') or {}

    if 'name' in query_params:
        name = query_params['name']
    else:
        name = 'Guest'

    # # 返回内容必须写到body中，固定格式不能更改。下面的返回会报错
    # return {'code': 200, 'data': f"Hello {name}", 'message': 'success'}
    # 正确的返回格式，必须使用json返回
    return {'statusCode': 200, 'body': json.dumps({'message': f"Hello {name}"})}
