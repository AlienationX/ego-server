import json
from xdbSearcher import XdbSearcher  # 从 ip2region 官方库导入


def lambda_handler(event, context):
    # 1. 获取客户端 IP（支持两种方式）
    if 'queryStringParameters' in event and 'ip' in event['queryStringParameters']:
        # 方式1：从查询参数获取指定 IP（如 ?ip=8.8.8.8）
        ip = event['queryStringParameters']['ip']
    else:
        # 方式2：从 API Gateway 的 X-Forwarded-For 头提取调用者 IP
        x_forwarded_for = event['headers'].get('x-forwarded-for', '').split(',')
        ip = x_forwarded_for[0].strip() if x_forwarded_for else event['requestContext']['identity']['sourceIp']

    # 2. 验证 IP 格式
    if not is_valid_ip(ip):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid IP address'})
        }

    # 3. 查询 IP 区域信息
    db_path = "ip2region.xdb"  # 数据库打包路径
    try:
        searcher = XdbSearcher(dbfile=db_path)
        region_str = searcher.searchByIPStr(ip)
        searcher.close()
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f"Database query failed: {str(e)}"})
        }

    # 4. 解析并返回结果
    fields = region_str.split('|')
    print(fields)
    result = {
        "ip": ip,
        "country": fields[0] or "N/A",
        "region": fields[1] or "N/A",
        "province": fields[2] or "N/A",
        "city": fields[3] or "N/A",
        "isp": fields[4] or "N/A"
    }
    return {
        'statusCode': 200,
        'body': result
    }


def is_valid_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)


if __name__ == "__main__":
    # 测试代码
    test_event = {
        'queryStringParameters': {'ip': '122.115.232.89'}
    }
    print(lambda_handler(test_event, None))
