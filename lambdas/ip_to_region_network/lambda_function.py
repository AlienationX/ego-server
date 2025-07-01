import requests


def lambda_handler(event, context):
    # 1. 获取客户端 IP（支持两种方式）
    if 'queryStringParameters' in event and 'ip' in event['queryStringParameters']:
        # 方式1：从查询参数获取指定 IP（如 ?ip=8.8.8.8）
        ip = event['queryStringParameters']['ip']
    else:
        # 方式2：从 API Gateway 的 X-Forwarded-For 头提取调用者 IP
        x_forwarded_for = event['headers'].get('x-forwarded-for', '').split(',')
        ip = x_forwarded_for[0].strip() if x_forwarded_for else event['requestContext']['identity']['sourceIp']

    url = "http://whois.pconline.com.cn/ipJson.jsp"
    params = {"ip": ip, "json": "true"}

    try:
        print(f"请求的IP地址: {ip}")
        # ​​连接超时​​：3 秒内未建立连接则抛出 ConnectTimeout。
        # ​​读取超时​​：连接建立后，5 秒内未收到数据则抛出 ReadTimeout。
        response = requests.get(url, params=params, timeout=(2, 1))

        response.raise_for_status()

        data = response.json()

        result = {
            "ip": ip,
            "country": data.get("country") or "N/A",
            "province": data.get("pro") or "N/A",
            "city": data.get("city") or "N/A",
            "region": data.get("region") or "N/A",
            "isp": "N/A"
        }
        return {
            'statusCode': 200,
            # 'body': json.dumps(result)
            'body': result
        }

    except requests.exceptions.RequestException as e:
        return {
            'statusCode': 500,
            'body': {'error': f"RequestException : {str(e)}"}
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {'error': f"网络或接口异常: {str(e)}"}
        }
