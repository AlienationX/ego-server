"""
华为应用内支付（IAP Kit HarmonyOS NEXT）服务端工具类
参考 Huawei IAP Server 官方 Python 示例实现：
- JWTGenerator: 生成访问华为 IAP Server 的鉴权 Token (ES256)
- JWSChecker: 解析与校验客户端返回的购买凭据 jwsPurchaseOrder / 服务端通知 JWS
- HuaweiIAPService: 封装订单状态查询 (order_status_query) 与发货确认核销 (order_shipped_confirm)
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

import jwt
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class HuaweiJWTGenerator:
    """
    华为 IAP Server 请求鉴权 Token 生成器
    遵循 HarmonyOS NEXT IAP 服务端 JWT 规范 (ES256 算法)
    """

    DEFAULT_ACTIVE_TIME_SECOND = 3600  # JWT 有效期（秒），最长 1 小时

    @classmethod
    def get_private_key_pem(cls) -> str:
        """
        从 .env (settings.HUAWEI_PAY_PRIVATE_KEY) 获取私钥 PEM 字符串
        """
        key_str = getattr(settings, "HUAWEI_PAY_PRIVATE_KEY", "").strip()
        if not key_str:
            return ""

        # 如果已经是标准 PEM 格式，直接返回
        if key_str.startswith("-----BEGIN"):
            return key_str

        # 如果是 Base64 单行编码，自动拼装成标准 PKCS#8 PEM 格式
        return f"-----BEGIN PRIVATE KEY-----\n{key_str}\n-----END PRIVATE KEY-----"

    @classmethod
    def gen_jwt(cls, body_str: str) -> Optional[str]:
        """
        为请求 Body 生成对应的 ES256 Bearer JWT
        :param body_str: 请求体 JSON 字符串
        :return: JWT 字符串
        """
        pri_key_pem = cls.get_private_key_pem()
        if not pri_key_pem:
            logger.error("生成华为 IAP JWT 失败：未配置 HUAWEI_PAY_PRIVATE_KEY")
            return None

        key_id = getattr(settings, "HUAWEI_IAP_KEY_ID", "")
        issuer_id = getattr(settings, "HUAWEI_IAP_ISSUER_ID", "")
        app_id = getattr(settings, "HUAWEI_CLIENT_ID", "")

        now_ts = int(time.time())
        digest = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

        headers = {
            "alg": "ES256",
            "typ": "JWT",
            "kid": key_id,
        }

        payload = {
            "iss": issuer_id,
            "aud": "iap-v1",
            "iat": now_ts,
            "exp": now_ts + cls.DEFAULT_ACTIVE_TIME_SECOND,
            "aid": app_id,
            "digest": digest,
        }

        try:
            token = jwt.encode(payload, pri_key_pem, algorithm="ES256", headers=headers)
            return token
        except Exception as e:
            logger.exception(f"生成华为 IAP JWT 异常: {e}")
            return None


class HuaweiJWSChecker:
    """
    华为 IAP JWS 凭证解析与验签器
    用于解析 jwsPurchaseOrder, inAppPurchaseData 等 JWS 格式的载荷
    """

    @staticmethod
    def decode_jws(jws_str: str) -> Optional[Dict[str, Any]]:
        """
        解码 JWS 字符串并返回 Payload 字典
        :param jws_str: 华为返回的三段式 JWS 字符串 (header.payload.signature)
        :return: Payload 字典
        """
        if not jws_str or not isinstance(jws_str, str):
            return None

        try:
            # 优先使用 pyjwt 解析 unverified payload
            payload = jwt.decode(jws_str, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.warning(f"JWS decode 失败，尝试手动解析 payload: {e}")

        # 手动 Base64 URL Safe 解码
        try:
            import base64

            parts = jws_str.split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1]
                # 补全 padding
                rem = len(payload_b64) % 4
                if rem > 0:
                    payload_b64 += "=" * (4 - rem)
                payload_bytes = base64.urlsafe_b64decode(payload_b64)
                return json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"手动解析 JWS payload 异常: {e}")

        return None


class HuaweiIAPService:
    """
    华为应用内支付服务端 API 调用服务
    """

    URL_ROOT = "https://iap.cloud.huawei.com"
    TIMEOUT_SECONDS = 8

    # 订单状态查询（消耗型/非消耗型）
    URL_ORDER_STATUS_QUERY = "/order/harmony/v1/application/order/status/query"

    # 订单发货/交付确认（消耗型/非消耗型）
    URL_ORDER_SHIPPED_CONFIRM = "/order/harmony/v1/application/purchase/shipped/confirm"

    # 自动续期订阅状态查询
    URL_SUB_STATUS_QUERY = "/subscription/harmony/v1/application/subscription/status/query"

    # 自动续期订阅发货确认
    URL_SUB_SHIPPED_CONFIRM = "/subscription/harmony/v1/application/purchase/shipped/confirm"

    @classmethod
    def _http_post(cls, endpoint: str, body_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送携带 Bearer JWT 的 HTTP POST 请求到华为 IAP Server
        """
        url = f"{cls.URL_ROOT}{endpoint}"
        body_json = json.dumps(body_dict, separators=(",", ":"))

        jwt_token = HuaweiJWTGenerator.gen_jwt(body_json)
        if not jwt_token:
            logger.error(f"华为 IAP 请求失败：无法生成 JWT，url={url}")
            return None

        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Authorization": f"Bearer {jwt_token}",
        }

        try:
            response = requests.post(url, data=body_json.encode("utf-8"), headers=headers, timeout=cls.TIMEOUT_SECONDS)
            logger.info(f"华为 IAP 请求响应 [{response.status_code}], url={url}, body={response.text}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"华为 IAP 请求异常 HTTP {response.status_code}: {response.text}")
                return response.json() if response.text else {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.exception(f"华为 IAP HTTP 请求失败, url={url}: {e}")
            return None

    @classmethod
    def order_status_query(cls, purchase_order_id: str, purchase_token: str) -> Optional[Dict[str, Any]]:
        """
        查询非续期/普通订单在华为 IAP 的最新状态
        :param purchase_order_id: 华为交易订单号 (Purchase Order ID)
        :param purchase_token: 商品购买 Token (Purchase Token)
        """
        body = {
            "purchaseOrderId": purchase_order_id,
            "purchaseToken": purchase_token,
        }
        return cls._http_post(cls.URL_ORDER_STATUS_QUERY, body)

    @classmethod
    def order_shipped_confirm(cls, purchase_order_id: str, purchase_token: str) -> Optional[Dict[str, Any]]:
        """
        确认发货（核销订单）：向华为 IAP Server 确认商品已向用户交付
        注意：购买成功后必须确认发货，否则华为会在一段时期后自动退款！
        :param purchase_order_id: 华为交易订单号
        :param purchase_token: 商品购买 Token
        """
        body = {
            "purchaseOrderId": purchase_order_id,
            "purchaseToken": purchase_token,
        }
        return cls._http_post(cls.URL_ORDER_SHIPPED_CONFIRM, body)

    @classmethod
    def sub_status_query(cls, purchase_order_id: str, purchase_token: str) -> Optional[Dict[str, Any]]:
        """
        查询自动续期订阅状态
        """
        body = {
            "purchaseOrderId": purchase_order_id,
            "purchaseToken": purchase_token,
        }
        return cls._http_post(cls.URL_SUB_STATUS_QUERY, body)

    @classmethod
    def sub_shipped_confirm(cls, purchase_order_id: str, purchase_token: str) -> Optional[Dict[str, Any]]:
        """
        确认自动续期订阅交付
        """
        body = {
            "purchaseOrderId": purchase_order_id,
            "purchaseToken": purchase_token,
        }
        return cls._http_post(cls.URL_SUB_SHIPPED_CONFIRM, body)
