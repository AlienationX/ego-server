from pathlib import Path

import requests
from loguru import logger
from PIL import Image

# pip install Pillow


def generate_thumbs(file: Path, max_size=(520, 520)):
    """生成缩略图"""

    # 设置缩略图的最大宽度和高度（单位：像素）。例如 (200, 200) 表示缩略图最长边不超过 200 像素。
    with Image.open(file) as img:
        # 保持宽高比时自动计算尺寸
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 保存缩略图（支持JPEG/PNG等格式）
        output_file = file.with_name(f"{file.stem}_small.webp")
        logger.info(f"Generating thumbnail {output_file}")

        # ​​quality​​（仅适用于有损压缩格式）：
        # ​​JPEG​​：范围 1-95（值越大质量越高，默认 75）。
        # ​​WEBP​​：范围 0-100（默认 80）。
        # ​​optimize​​（适用于 PNG）：
        # 启用优化压缩（True/False），减小文件体积。
        img.save(output_file, "WEBP", quality=85)


def remove_watermark():
    """去除水印"""
    pass


def resize_image(
    input_file: str,
    output_file: str,
    target_width=1284,  # 目标宽度
    target_height=2778,  # 目标高度
    min_width=1080,  # 最小宽度约束
    min_height=1920,  # 最小高度约束
):
    """
    等比例缩放图片，并确保最小尺寸约束
    :param input_path: 输入图片路径
    :param output_path: 输出图片路径
    :param target_width: 目标宽度
    :param target_height: 目标高度
    :param min_width: 最小宽度约束
    :param min_height: 最小高度约束
    """
    # 打开原始图片
    original_image = Image.open(input_file)
    original_width, original_height = original_image.size

    logger.info(f"{input_file} 原始尺寸: {original_width} x {original_height}")

    # 方案1：以目标宽度为准进行等比缩放
    new_width_1 = target_width
    new_height_1 = int((target_width / original_width) * original_height)

    # 方案2：以目标高度为准进行等比缩放
    new_height_2 = target_height
    new_width_2 = int((target_height / original_height) * original_width)

    # 检查两种方案是否满足最小尺寸约束
    scheme1_valid = (new_width_1 >= min_width) and (new_height_1 >= min_height)
    scheme2_valid = (new_width_2 >= min_width) and (new_height_2 >= min_height)

    # 根据检查结果选择缩放方案
    if scheme1_valid and scheme2_valid:
        # 两种方案都满足时，选择方案1（以宽度为准）
        new_width = new_width_1
        new_height = new_height_1
        logger.info(f"{input_file} 选择方案1：以目标宽度为准缩放 {target_width}")
    elif scheme1_valid:
        new_width = new_width_1
        new_height = new_height_1
        logger.info(f"{input_file} 选择方案1：以目标宽度为准缩放 {target_width}")
    elif scheme2_valid:
        new_width = new_width_2
        new_height = new_height_2
        logger.info(f"{input_file} 选择方案2：以目标高度为准缩放 {target_height}")
    else:
        # 两种方案都不满足时，强制缩放至最小尺寸
        ratio_w = min_width / original_width
        ratio_h = min_height / original_height
        scale = max(ratio_w, ratio_h)  # 取较大比例确保两个维度都达到最小值
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        logger.info(f"{input_file} 选择方案3：强制缩放至最小尺寸 {min_width} x {min_height}")

    logger.info(f"{input_file} 最终尺寸: {new_width} x {new_height}")

    # 执行缩放并保存
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    resized_image = original_image.resize((new_width, new_height), Image.LANCZOS)
    resized_image.save(output_file, quality=95)
    logger.info(f"{input_file} 图片已保存至: {output_file}")
    return output_file


def send_dingtalk(msg, keyword="[通知]", secret="", access_token=""):
    """发送钉钉消息"""
    if not secret:
        secret = "SECcdc72b1e3470ecbc25b099883a29fea124a6b2ac4217b514cd51dee9a0ef0314"

    if not access_token:
        access_token = "d6796dfb449b3ffc382be1c1e9b6e8a9947b2f2d2915444bc4072e912460b2f0"

    webhook_url = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"

    if secret:
        # 加签
        import base64
        import hashlib
        import hmac
        import time
        import urllib

        timestamp = str(round(time.time() * 1000))
        # secret = '此处填写 webhook token'
        secret_enc = secret.encode("utf-8")
        string_to_sign = "{}\n{}".format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    headers = {"Content-Type": "application/json;charset=utf-8"}
    data = {
        # 消息类型参考：https://open.dingtalk.com/document/dingstart/custom-bot-send-message-type
        "msgtype": "text",  # 消息类型, 可选值有 text、link、markdown、actionCard、feedCard
        "text": {"content": f"{keyword} {msg}"},
        # "at": {
        #     "atMobiles": ["138xxxx8888"],  # 被@成员的手机号，可选
        #     "atUserIds": ["user123"],
        #     "isAtAll": False,  # 是否@所有人，慎用
        # },
    }
    response = requests.post(webhook_url, json=data, headers=headers)
    response.raise_for_status()

    logger.info(f"DingTalk message sent successfully, response: {response.text}")
    # logger.info(f"DingTalk message sent successfully, response: {response.json()}")
