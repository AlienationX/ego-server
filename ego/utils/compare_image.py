import hashlib

import numpy as np
from PIL import Image


def get_file_md5(file_path):
    """计算文件的二进制内容的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        # 分块读取大文件，避免内存占用过高
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_image_content_hash(file_path, hash_size=8):
    """
    生成图像的内容的差异哈希（dHash）。
    相同内容但格式、质量不同的图片，此哈希值很可能相同。
    """
    img = Image.open(file_path)
    # 统一处理：转灰度、缩放到 (hash_size+1, hash_size)
    img = img.convert("L").resize((hash_size + 1, hash_size))
    pixels = np.array(img)

    # 计算每行相邻像素的差异
    diff = pixels[:, 1:] > pixels[:, :-1]
    # 将布尔矩阵转换为整数哈希
    hash_value = 0
    for row in diff.flatten():
        hash_value = (hash_value << 1) | int(row)

    # 返回十六进制字符串，也可以直接用整数比较
    return hex(hash_value)[2:].zfill(hash_size**2 // 4)


if __name__ == "__main__":
    img_path1 = "/Users/tangzy/Downloads/Snipaste_2026-03-26_17-45-06.png"
    img_path2 = "/Users/tangzy/Downloads/Snipaste_2026-03-26_17-45-06_副本.jpg"
    print(get_file_md5(img_path1))
    print(get_image_content_hash(img_path1))
    print(get_file_md5(img_path2))
    print(get_image_content_hash(img_path2))
