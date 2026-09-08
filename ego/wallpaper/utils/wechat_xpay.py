import hashlib
import hmac
import json
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional, Tuple

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def calc_pay_sig(uri: str, post_body: str, appkey: str) -> str:
    """
    计算支付签名 paySig (HMAC-SHA256)
    - C端下单 (wx.requestVirtualPayment): uri 固定为 "requestVirtualPayment"
    - B端服务端接口 (/xpay/*): uri 为接口真实路径，如 "/xpay/query_order"
    """
    msg = uri + "&" + post_body
    return hmac.new(
        appkey.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def calc_signature(post_body: str, session_key: str) -> str:
    """
    计算用户态签名 signature (HMAC-SHA256, 以用户的 session_key 为密钥)
    """
    return hmac.new(
        session_key.encode("utf-8"),
        post_body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class WeChatXPayService:
    """
    微信小程序虚拟支付服务（个人主体 / 道具直购 short_series_goods）
    """

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        获取虚拟支付配置
        注：微信虚拟支付 (wx.requestVirtualPayment) 中的 env 必须为整数：
        0 - 现网环境（正式）
        1 - 沙箱环境（测试）
        """
        raw_env = getattr(settings, "ENV", "prod")  # dev or prod
        if str(raw_env).lower() == "dev":
            appkey = settings.WECHAT_XPAY_SANDBOX_APPKEY
            env_code = 1  # 沙箱环境
        else:
            appkey = settings.WECHAT_XPAY_APPKEY
            env_code = 0  # 现网环境

        return {
            "appid": settings.WECHAT_XPAY_APPID,
            "offer_id": settings.WECHAT_XPAY_OFFER_ID,
            "appkey": appkey,
            "env": env_code,
        }

    @classmethod
    def build_order_pay_data(
        cls,
        out_trade_no: str,
        product_id: str,
        goods_price_fen: int,
        session_key: str,
        buy_quantity: int = 1,
        attach: str = "",
    ) -> Dict[str, Any]:
        """
        构建前端 wx.requestVirtualPayment 所需的 payData
        """
        config = cls.get_config()
        offer_id = str(config["offer_id"])
        appkey = config["appkey"]
        env = int(config["env"])

        # 构造并序列化 signData（紧凑JSON，不能含多余空格）
        sign_dict = {
            "offerId": offer_id,
            "buyQuantity": buy_quantity,
            "env": env,
            "currencyType": "CNY",
            "productId": str(product_id),
            "goodsPrice": goods_price_fen,
            "outTradeNo": str(out_trade_no),
            "attach": str(attach or out_trade_no),
        }
        sign_data_str = json.dumps(sign_dict, separators=(",", ":"), ensure_ascii=False)

        # 计算 paySig 与 signature
        pay_sig = calc_pay_sig("requestVirtualPayment", sign_data_str, appkey)
        signature = calc_signature(sign_data_str, session_key)

        return {
            "mode": "short_series_goods",
            "signData": sign_data_str,
            "paySig": pay_sig,
            "signature": signature,
        }

    @classmethod
    def parse_deliver_notify_xml(cls, xml_text: str) -> Optional[Dict[str, Any]]:
        """
        解析微信虚拟支付推送的 XML 报文 (xpay_goods_deliver_notify)
        """
        if not xml_text:
            return None

        try:
            root = ET.fromstring(xml_text.strip())
            event = root.findtext("Event") or ""
            openid = root.findtext("OpenId") or root.findtext("FromUserName") or ""
            out_trade_no = root.findtext("OutTradeNo") or ""

            # 平台单号位于 WeChatPayInfo/MchOrderNo
            wx_order_id = ""
            wechat_pay_info = root.find("WeChatPayInfo")
            if wechat_pay_info is not None:
                wx_order_id = wechat_pay_info.findtext("MchOrderNo") or wechat_pay_info.findtext("TransactionId") or ""

            # 道具信息位于 GoodsInfo
            product_id = ""
            quantity = 1
            goods_info = root.find("GoodsInfo")
            if goods_info is not None:
                product_id = goods_info.findtext("ProductId") or ""
                try:
                    quantity = int(goods_info.findtext("Quantity") or 1)
                except ValueError:
                    quantity = 1

            attach = root.findtext("Attach") or ""

            return {
                "event": event,
                "openid": openid,
                "out_trade_no": out_trade_no,
                "wx_order_id": wx_order_id,
                "product_id": product_id,
                "quantity": quantity,
                "attach": attach,
                "raw_root": root,
            }
        except Exception as e:
            logger.error(f"解析微信发货推送 XML 失败: {e}, 原始内容: {xml_text[:300]}")
            return None

    @classmethod
    def format_deliver_response(cls, err_code: int = 0, err_msg: str = "success") -> str:
        """
        生成返回给微信的应答 XML
        """
        return f"<xml><ErrCode>{err_code}</ErrCode><ErrMsg><![CDATA[{err_msg}]]></ErrMsg></xml>"

    @classmethod
    def get_access_token(cls) -> Optional[str]:
        """
        获取小程序接口调用凭据 access_token（带 1.5 小时缓存）
        """
        cache_key = "wechat_miniprogram_access_token"
        token = cache.get(cache_key)
        if token:
            return token

        appid = settings.WECHAT_APPID
        secret = settings.WECHAT_SECRET
        if not appid or not secret:
            logger.error("未配置 WECHAT_APPID 或 WECHAT_SECRET，无法获取 access_token")
            return None

        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret,
        }

        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in", 7200)
            if access_token:
                cache.set(cache_key, access_token, timeout=max(60, expires_in - 300))
                return access_token
            logger.error(f"获取微信 access_token 失败: {data}")
            return None
        except Exception as e:
            logger.error(f"请求微信 access_token 异常: {e}")
            return None

    @classmethod
    def query_order(cls, openid: str, out_trade_no: str) -> Optional[Dict[str, Any]]:
        """
        向微信虚拟支付接口主动查单 (POST /xpay/query_order)
        """
        token = cls.get_access_token()
        if not token:
            logger.warning("获取不到 access_token，跳过 query_order 远程调用")
            return None

        config = cls.get_config()
        appkey = config["appkey"]
        env = int(config["env"])

        url = f"https://api.weixin.qq.com/xpay/query_order?access_token={token}"
        uri = "/xpay/query_order"

        post_dict = {
            "openid": openid,
            "env": env,
            "order_id": out_trade_no,
        }
        post_body = json.dumps(post_dict, separators=(",", ":"), ensure_ascii=False)
        pay_sig = calc_pay_sig(uri, post_body, appkey)

        headers = {
            "Content-Type": "application/json",
            "pay_sig": pay_sig,
        }

        try:
            resp = requests.post(url, data=post_body, headers=headers, timeout=5)
            data = resp.json()
            logger.info(f"微信虚拟支付 query_order 返回: {data}")
            return data
        except Exception as e:
            logger.error(f"微信虚拟支付查单异常, out_trade_no={out_trade_no}: {e}")
            return None
