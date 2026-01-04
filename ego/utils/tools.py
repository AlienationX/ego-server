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
    except Exception as e:
        region_str = "N/A|N/A|N/A|N/A|N/A"

    return region_str
