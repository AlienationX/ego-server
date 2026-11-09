import io
import logging
from typing import Optional, Tuple

import requests
from PIL import Image

from .wechat_xpay import WeChatXPayService

logger = logging.getLogger(__name__)

MSG_SEC_CHECK_V1_URL = "https://api.weixin.qq.com/wxa/msg_sec_check"
MSG_SEC_CHECK_V2_URL = "https://api.weixin.qq.com/wxa/msg_sec_check"
IMG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/img_sec_check"


def check_text_security(content: str, openid: str = "") -> Tuple[bool, str]:
    """
    微信小程序文本内容安全检测 (结合 v2 与 v1)
    :param content: 待检测文本内容
    :param openid: 用户 openid (可选)
    :return: (is_pass, error_message)
    """
    if not content or not str(content).strip():
        return True, ""

    token = WeChatXPayService.get_access_token()
    if not token:
        logger.warning("[WeChatSec] 获取不到 access_token，跳过文本安全检测")
        return True, ""

    content_str = str(content).strip()

    # 1. 如果有 openid，优先使用 v2 接口检测
    if openid and len(openid) > 10:
        try:
            url = f"{MSG_SEC_CHECK_V2_URL}?access_token={token}"
            payload = {
                "version": 2,
                "scene": 4,  # 4: 日志/相册/图片处理/图文创作
                "openid": openid,
                "content": content_str,
            }
            resp = requests.post(url, json=payload, timeout=5)
            data = resp.json()
            errcode = data.get("errcode", 0)

            if errcode == 87014:
                logger.info(f"[WeChatSec] 文本检测违规 (v2 errcode 87014): {data}")
                return False, "内容包含敏感或违规信息，请修改后重试"

            result = data.get("result", {})
            if result.get("suggest") == "risky":
                logger.info(f"[WeChatSec] 文本检测违规 (v2 suggest risky): {data}")
                return False, "内容包含敏感或违规信息，请修改后重试"

            if errcode == 0:
                return True, ""

            # 若为其他错误（如 40003 invalid openid），继续向下走 v1 降级检测
            logger.warning(f"[WeChatSec] 文本检测 v2 返回非0: {data}，尝试 v1 检测")
        except Exception as e:
            logger.error(f"[WeChatSec] 文本检测 v2 异常: {e}")

    # 2. v1 降级检测 (无需 openid)
    try:
        url = f"{MSG_SEC_CHECK_V1_URL}?access_token={token}"
        resp = requests.post(url, json={"content": content_str}, timeout=5)
        data = resp.json()
        errcode = data.get("errcode", 0)

        if errcode == 87014:
            logger.info(f"[WeChatSec] 文本检测违规 (v1 errcode 87014): {data}")
            return False, "内容包含敏感或违规信息，请修改后重试"

        if errcode == 0:
            return True, ""

        logger.warning(f"[WeChatSec] 文本检测 v1 返回非0状态: {data}")
        return True, ""
    except Exception as e:
        logger.error(f"[WeChatSec] 文本检测 v1 异常: {e}")
        return True, ""


def check_image_security(image_bytes: bytes, filename: str = "image.jpg") -> Tuple[bool, str]:
    """
    微信小程序图片内容安全检测 (img_sec_check)
    :param image_bytes: 图片二进制数据
    :param filename: 图片文件名
    :return: (is_pass, error_message)
    """
    if not image_bytes:
        return True, ""

    token = WeChatXPayService.get_access_token()
    if not token:
        logger.warning("[WeChatSec] 获取不到 access_token，跳过图片安全检测")
        return True, ""

    upload_bytes = image_bytes
    upload_name = filename or "image.jpg"

    # 针对大图进行压缩与尺寸缩放，微信限制 <= 1MB，建议尺寸 <= 750x1334
    try:
        if len(image_bytes) > 800 * 1024:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # 统一转换为 RGB 格式并压缩为 JPEG
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.thumbnail((750, 1334), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=75, optimize=True)
                upload_bytes = output.getvalue()
                upload_name = "compressed.jpg"
                logger.info(f"[WeChatSec] 图片压缩: {len(image_bytes)}B -> {len(upload_bytes)}B")
    except Exception as e:
        logger.warning(f"[WeChatSec] 图片预压缩失败，尝试原图上传检测: {e}")

    try:
        url = f"{IMG_SEC_CHECK_URL}?access_token={token}"
        files = {
            "media": (upload_name, upload_bytes, "image/jpeg")
        }
        resp = requests.post(url, files=files, timeout=8)
        data = resp.json()
        errcode = data.get("errcode", 0)

        if errcode == 87014:
            logger.info(f"[WeChatSec] 图片检测违规 (errcode 87014): {data}")
            return False, "所选图片包含违规信息，请重新选择"

        if errcode == 0:
            return True, ""

        logger.warning(f"[WeChatSec] 图片检测返回非0状态: {data}")
        return True, ""
    except Exception as e:
        logger.error(f"[WeChatSec] 图片安全检测异常: {e}")
        return True, ""

