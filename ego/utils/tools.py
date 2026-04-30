import random
import string

from django.conf import settings
from utils.ip2region.xdbSearcher import XdbSearcher


def get_client_ip(request) -> str:
    """
    获取客户端真实IP地址，支持反向代理场景（如 Nginx）。
    优先从 X-Forwarded-For 头获取，格式: client_ip, proxy1_ip, proxy2_ip
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # X-Forwarded-For 第一个 IP 是客户端真实 IP
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def ip_to_region(ip_address: str) -> str:
    """
    Convert an IP address to a region string using the ip2region database.
    """
    db_path = settings.BASE_DIR / "utils/ip2region/ip2region.xdb"  # 数据库打包路径
    try:
        # 缓存优化参考：https://github.com/lionsoul2014/ip2region/tree/master/binding/python
        # 缓存 VectorIndex 索引
        # 缓存整个 xdb 数据
        searcher = XdbSearcher(dbfile=db_path)
        region_str = searcher.searchByIPStr(ip_address)
        searcher.close()
    except Exception:
        region_str = "N/A|N/A|N/A|N/A|N/A"

    # region_str = region_str.replace("|", ",")
    return region_str


def generate_nickname(length=8):
    """生成一个指定长度的随机用户名，包含大小写字母和数字"""
    characters = string.ascii_letters + string.digits  # 大小写字母和数字
    nickname = "".join(random.choices(characters, k=length))
    return nickname
