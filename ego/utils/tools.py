import random
import string

from django.conf import settings
from utils.ip2region.xdbSearcher import XdbSearcher


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

    return region_str


def generate_nickname(self, length=8):
    """生成一个指定长度的随机用户名，包含大小写字母和数字"""
    characters = string.ascii_letters + string.digits  # 大小写字母和数字
    nickname = "".join(random.choices(characters, k=length))
    return nickname
