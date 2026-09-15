import csv
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.contrib.auth.models import User
from django.db.models import Count, Min, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from wallpaper.models import Access, Classify, Order, Profile, UserActions, Wall

ROOT_PIC_URL = "https://api.wp.ego8.space/static/wallpaper/media"


def parse_date_range(start_date_str: str = None, end_date_str: str = None, days: int = 7):
    """
    解析并返回开始和结束的 datetime 对象 (本地时区，完整日期边界 00:00:00 到 23:59:59)
    """
    today = timezone.localdate()

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            end_date = today
    else:
        end_date = today

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = end_date - timedelta(days=days - 1)
    else:
        start_date = end_date - timedelta(days=days - 1)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # 构造 datetime 边界
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max), tz)

    # 上一周期 (用于计算环比)
    period_days = (end_date - start_date).days + 1
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=period_days - 1)
    prev_start_dt = timezone.make_aware(datetime.combine(prev_start_date, time.min), tz)
    prev_end_dt = timezone.make_aware(datetime.combine(prev_end_date, time.max), tz)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_dt": start_dt,
        "end_dt": end_dt,
        "prev_start_dt": prev_start_dt,
        "prev_end_dt": prev_end_dt,
        "period_days": period_days,
    }


def get_filter_options() -> Dict[str, List[str]]:
    """
    获取系统中实际存在的平台和渠道选项，方便前端下拉菜单动态展示
    """
    channels = (
        Access.objects.exclude(channel__isnull=True)
        .exclude(channel="")
        .values_list("channel", flat=True)
        .distinct()
        .order_by("channel")[:30]
    )
    platforms = (
        Access.objects.exclude(platform__isnull=True)
        .exclude(platform="")
        .values_list("platform", flat=True)
        .distinct()
        .order_by("platform")[:20]
    )

    # 预设常见选项作为兜底
    preset_channels = ["huawei", "xiaomi", "oppo", "vivo", "apple", "appstore", "mp-weixin", "google", "web"]
    preset_platforms = ["android", "ios", "harmony", "mp-weixin", "mp-douyin", "web"]

    merged_channels = sorted(list(set(list(channels) + preset_channels)))
    merged_platforms = sorted(list(set(list(platforms) + preset_platforms)))

    return {
        "channels": merged_channels,
        "platforms": merged_platforms,
    }


def calculate_growth_rate(current: float, previous: float) -> str:
    """计算增长率字符串，如 +12.5% 或 -5.2%"""
    if previous == 0:
        return "+100%" if current > 0 else "0%"
    growth = ((current - previous) / previous) * 100
    prefix = "+" if growth > 0 else ""
    return f"{prefix}{growth:.1f}%"


def get_bi_overview_cards(date_info: dict, channel: str = "all", platform: str = "all") -> dict:
    """
    计算 7 大核心 KPI 指标卡数据及上一周期对比
    """
    start_dt = date_info["start_dt"]
    end_dt = date_info["end_dt"]
    prev_start_dt = date_info["prev_start_dt"]
    prev_end_dt = date_info["prev_end_dt"]

    # 1. 基础过滤条件
    access_q = Q(access_time__range=(start_dt, end_dt))
    prev_access_q = Q(access_time__range=(prev_start_dt, prev_end_dt))
    if channel != "all":
        access_q &= Q(channel=channel)
        prev_access_q &= Q(channel=channel)
    if platform != "all":
        access_q &= Q(platform=platform)
        prev_access_q &= Q(platform=platform)

    # DAU (当前周期内每日去重活跃设备均值，或所选时段独立设备数)
    active_devices = Access.objects.filter(access_q).values("device_id").distinct().count()
    prev_active_devices = Access.objects.filter(prev_access_q).values("device_id").distinct().count()

    # 今日实时 DAU (若今天在当前时段内)
    today = timezone.localdate()
    today_start = timezone.make_aware(datetime.combine(today, time.min))
    today_end = timezone.make_aware(datetime.combine(today, time.max))
    today_q = Q(access_time__range=(today_start, today_end))
    if channel != "all":
        today_q &= Q(channel=channel)
    if platform != "all":
        today_q &= Q(platform=platform)
    today_dau = Access.objects.filter(today_q).values("device_id").distinct().count()

    # 2. 新增访客设备 (首次访问在当前时段内的设备数)
    # 按设备取其首次访问时间
    new_devices = (
        Access.objects.values("device_id")
        .annotate(first_seen=Min("access_time"))
        .filter(first_seen__range=(start_dt, end_dt))
    )
    if channel != "all":
        new_devices = new_devices.filter(channel=channel)
    if platform != "all":
        new_devices = new_devices.filter(platform=platform)
    new_devices_count = new_devices.count()

    prev_new_devices = (
        Access.objects.values("device_id")
        .annotate(first_seen=Min("access_time"))
        .filter(first_seen__range=(prev_start_dt, prev_end_dt))
    )
    if channel != "all":
        prev_new_devices = prev_new_devices.filter(channel=channel)
    if platform != "all":
        prev_new_devices = prev_new_devices.filter(platform=platform)
    prev_new_devices_count = prev_new_devices.count()

    # 3. 新注册用户数 (User.date_joined)
    user_q = Q(date_joined__range=(start_dt, end_dt))
    prev_user_q = Q(date_joined__range=(prev_start_dt, prev_end_dt))
    if channel != "all":
        user_q &= Q(profile__channel=channel)
        prev_user_q &= Q(profile__channel=channel)
    new_registers = User.objects.filter(user_q).count()
    prev_new_registers = User.objects.filter(prev_user_q).count()

    # 4. VIP 付费订单数与 GMV 营收 (Order.paid_at, status='paid')
    order_q = Q(status="paid", paid_at__range=(start_dt, end_dt))
    prev_order_q = Q(status="paid", paid_at__range=(prev_start_dt, prev_end_dt))
    if channel != "all":
        order_q &= Q(channel=channel)
        prev_order_q &= Q(channel=channel)
    if platform != "all":
        order_q &= Q(platform=platform)
        prev_order_q &= Q(platform=platform)

    order_stats = Order.objects.filter(order_q).aggregate(
        total_orders=Count("id"),
        total_amount=Sum("amount"),
    )
    prev_order_stats = Order.objects.filter(prev_order_q).aggregate(
        total_orders=Count("id"),
        total_amount=Sum("amount"),
    )

    vip_orders = order_stats["total_orders"] or 0
    prev_vip_orders = prev_order_stats["total_orders"] or 0

    vip_revenue = float(order_stats["total_amount"] or Decimal("0.00"))
    prev_vip_revenue = float(prev_order_stats["total_amount"] or Decimal("0.00"))

    # 5. 当前有效会员数 (存量快照)
    now = timezone.now()
    active_vips_q = Q(vip_expire_time__gt=now)
    if channel != "all":
        active_vips_q &= Q(channel=channel)
    active_vips = Profile.objects.filter(active_vips_q).count()

    # 即将7天内到期的会员数
    expiring_soon_vips = Profile.objects.filter(
        vip_expire_time__range=(now, now + timedelta(days=7))
    ).count()

    # 6. 壁纸下载量 (UserActions.action_key='download')
    action_q = Q(action_key="download", created_at__range=(start_dt, end_dt))
    prev_action_q = Q(action_key="download", created_at__range=(prev_start_dt, prev_end_dt))
    if channel != "all":
        action_q &= Q(channel=channel)
        prev_action_q &= Q(channel=channel)

    downloads = UserActions.objects.filter(action_q).count()
    prev_downloads = UserActions.objects.filter(prev_action_q).count()

    return {
        "dau": active_devices,
        "dau_growth": calculate_growth_rate(active_devices, prev_active_devices),
        "today_dau": today_dau,
        "new_devices": new_devices_count,
        "new_devices_growth": calculate_growth_rate(new_devices_count, prev_new_devices_count),
        "new_registers": new_registers,
        "new_registers_growth": calculate_growth_rate(new_registers, prev_new_registers),
        "vip_orders": vip_orders,
        "vip_orders_growth": calculate_growth_rate(vip_orders, prev_vip_orders),
        "vip_revenue": vip_revenue,
        "vip_revenue_growth": calculate_growth_rate(vip_revenue, prev_vip_revenue),
        "active_vips": active_vips,
        "expiring_soon_vips": expiring_soon_vips,
        "downloads": downloads,
        "downloads_growth": calculate_growth_rate(downloads, prev_downloads),
    }


def get_bi_trends(date_info: dict, channel: str = "all", platform: str = "all", granularity: str = "day") -> dict:
    """
    按日或按月计算时间序列趋势：DAU、新增设备、新注册、下载量、VIP订单、营收金额
    """
    start_date = date_info["start_date"]
    end_date = date_info["end_date"]
    start_dt = date_info["start_dt"]
    end_dt = date_info["end_dt"]

    # 1. 生成时间轴标签
    date_labels = []
    bucket_map = {}

    if granularity == "month":
        # 按月生成标签
        cur = start_date.replace(day=1)
        while cur <= end_date:
            key = cur.strftime("%Y-%m")
            if key not in bucket_map:
                date_labels.append(key)
                bucket_map[key] = {
                    "dau": 0,
                    "new_devices": 0,
                    "new_registers": 0,
                    "downloads": 0,
                    "vip_orders": 0,
                    "vip_revenue": 0.0,
                }
            # 步进到下个月
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        trunc_func = TruncMonth
        date_format = "%Y-%m"
    else:
        # 按日生成标签
        cur = start_date
        while cur <= end_date:
            key = cur.strftime("%Y-%m-%d")
            date_labels.append(key)
            bucket_map[key] = {
                "dau": 0,
                "new_devices": 0,
                "new_registers": 0,
                "downloads": 0,
                "vip_orders": 0,
                "vip_revenue": 0.0,
            }
            cur += timedelta(days=1)
        trunc_func = TruncDate
        date_format = "%Y-%m-%d"

    # 2. 统计 DAU (按日/月独立设备)
    access_q = Q(access_time__range=(start_dt, end_dt))
    if channel != "all":
        access_q &= Q(channel=channel)
    if platform != "all":
        access_q &= Q(platform=platform)

    dau_qs = (
        Access.objects.filter(access_q)
        .annotate(bucket=trunc_func("access_time"))
        .values("bucket")
        .annotate(cnt=Count("device_id", distinct=True))
        .order_by("bucket")
    )
    for row in dau_qs:
        if row["bucket"]:
            b_key = row["bucket"].strftime(date_format)
            if b_key in bucket_map:
                bucket_map[b_key]["dau"] = row["cnt"]

    # 3. 统计 新增设备 (首次访问在各时间桶)
    new_dev_qs = (
        Access.objects.values("device_id")
        .annotate(first_seen=Min("access_time"))
        .filter(first_seen__range=(start_dt, end_dt))
    )
    if channel != "all":
        new_dev_qs = new_dev_qs.filter(channel=channel)
    if platform != "all":
        new_dev_qs = new_dev_qs.filter(platform=platform)

    new_dev_qs = (
        new_dev_qs.annotate(bucket=trunc_func("first_seen"))
        .values("bucket")
        .annotate(cnt=Count("device_id"))
        .order_by("bucket")
    )
    for row in new_dev_qs:
        if row["bucket"]:
            b_key = row["bucket"].strftime(date_format)
            if b_key in bucket_map:
                bucket_map[b_key]["new_devices"] = row["cnt"]

    # 4. 统计 新注册用户
    user_q = Q(date_joined__range=(start_dt, end_dt))
    if channel != "all":
        user_q &= Q(profile__channel=channel)

    user_qs = (
        User.objects.filter(user_q)
        .annotate(bucket=trunc_func("date_joined"))
        .values("bucket")
        .annotate(cnt=Count("id"))
        .order_by("bucket")
    )
    for row in user_qs:
        if row["bucket"]:
            b_key = row["bucket"].strftime(date_format)
            if b_key in bucket_map:
                bucket_map[b_key]["new_registers"] = row["cnt"]

    # 5. 统计 壁纸下载
    action_q = Q(action_key="download", created_at__range=(start_dt, end_dt))
    if channel != "all":
        action_q &= Q(channel=channel)

    action_qs = (
        UserActions.objects.filter(action_q)
        .annotate(bucket=trunc_func("created_at"))
        .values("bucket")
        .annotate(cnt=Count("id"))
        .order_by("bucket")
    )
    for row in action_qs:
        if row["bucket"]:
            b_key = row["bucket"].strftime(date_format)
            if b_key in bucket_map:
                bucket_map[b_key]["downloads"] = row["cnt"]

    # 6. 统计 VIP 订单与营收
    order_q = Q(status="paid", paid_at__range=(start_dt, end_dt))
    if channel != "all":
        order_q &= Q(channel=channel)
    if platform != "all":
        order_q &= Q(platform=platform)

    order_qs = (
        Order.objects.filter(order_q)
        .annotate(bucket=trunc_func("paid_at"))
        .values("bucket")
        .annotate(cnt=Count("id"), rev=Sum("amount"))
        .order_by("bucket")
    )
    for row in order_qs:
        if row["bucket"]:
            b_key = row["bucket"].strftime(date_format)
            if b_key in bucket_map:
                bucket_map[b_key]["vip_orders"] = row["cnt"]
                bucket_map[b_key]["vip_revenue"] = float(row["rev"] or 0)

    # 组装返回的序列列表
    return {
        "dates": date_labels,
        "dau": [bucket_map[k]["dau"] for k in date_labels],
        "new_devices": [bucket_map[k]["new_devices"] for k in date_labels],
        "new_registers": [bucket_map[k]["new_registers"] for k in date_labels],
        "downloads": [bucket_map[k]["downloads"] for k in date_labels],
        "vip_orders": [bucket_map[k]["vip_orders"] for k in date_labels],
        "vip_revenue": [bucket_map[k]["vip_revenue"] for k in date_labels],
    }


def get_bi_distributions(date_info: dict, channel: str = "all", platform: str = "all") -> dict:
    """
    计算渠道、平台、会员商品销售结构占比
    """
    start_dt = date_info["start_dt"]
    end_dt = date_info["end_dt"]

    # 1. 渠道分布 (按访问设备数)
    access_q = Q(access_time__range=(start_dt, end_dt))
    if platform != "all":
        access_q &= Q(platform=platform)

    channel_qs = (
        Access.objects.filter(access_q)
        .exclude(channel__isnull=True)
        .exclude(channel="")
        .values("channel")
        .annotate(value=Count("device_id", distinct=True))
        .order_by("-value")[:10]
    )
    channels = [{"name": row["channel"], "value": row["value"]} for row in channel_qs]

    # 2. 平台分布
    plat_q = Q(access_time__range=(start_dt, end_dt))
    if channel != "all":
        plat_q &= Q(channel=channel)

    platform_qs = (
        Access.objects.filter(plat_q)
        .exclude(platform__isnull=True)
        .exclude(platform="")
        .values("platform")
        .annotate(value=Count("device_id", distinct=True))
        .order_by("-value")[:10]
    )
    platforms = [{"name": row["platform"], "value": row["value"]} for row in platform_qs]

    # 3. VIP 套餐销售占比
    order_q = Q(status="paid", paid_at__range=(start_dt, end_dt))
    if channel != "all":
        order_q &= Q(channel=channel)
    if platform != "all":
        order_q &= Q(platform=platform)

    vip_product_qs = (
        Order.objects.filter(order_q)
        .values("product_name")
        .annotate(value=Count("id"), total_amount=Sum("amount"))
        .order_by("-value")[:10]
    )
    vip_products = [
        {
            "name": row["product_name"] or "通用会员",
            "value": row["value"],
            "amount": float(row["total_amount"] or 0),
        }
        for row in vip_product_qs
    ]

    return {
        "channels": channels,
        "platforms": platforms,
        "vip_products": vip_products,
    }


def get_bi_wallpaper_rank(date_info: dict, channel: str = "all", limit: int = 20) -> list:
    """
    统计指定时段内热门壁纸下载榜单 TOP N
    """
    start_dt = date_info["start_dt"]
    end_dt = date_info["end_dt"]

    action_q = Q(action_key="download", created_at__range=(start_dt, end_dt), wall__isnull=False)
    if channel != "all":
        action_q &= Q(channel=channel)

    top_walls_qs = (
        UserActions.objects.filter(action_q)
        .values("wall_id")
        .annotate(download_count=Count("id"))
        .order_by("-download_count")[:limit]
    )

    wall_ids = [item["wall_id"] for item in top_walls_qs]
    walls_map = {
        wall.id: wall
        for wall in Wall.objects.filter(id__in=wall_ids).select_related("classify")
    }

    # 顺便统计收藏数
    favorite_counts = {
        row["wall_id"]: row["fav_count"]
        for row in UserActions.objects.filter(
            action_key="favorite",
            wall_id__in=wall_ids,
            created_at__range=(start_dt, end_dt),
        )
        .values("wall_id")
        .annotate(fav_count=Count("id"))
    }

    result = []
    for item in top_walls_qs:
        wid = item["wall_id"]
        wall = walls_map.get(wid)
        if not wall:
            continue

        picurl = wall.picurl or ""
        if picurl and not picurl.startswith("http"):
            picurl = f"{ROOT_PIC_URL}/{picurl.lstrip('/')}"

        result.append(
            {
                "id": wid,
                "description": wall.description or f"壁纸 #{wid}",
                "classify_name": wall.classify.name if wall.classify else "未分类",
                "publisher": wall.publisher or "官方",
                "picurl": picurl,
                "download_count": item["download_count"],
                "favorite_count": favorite_counts.get(wid, 0),
            }
        )

    return result


def get_bi_detail_table(date_info: dict, channel: str = "all", platform: str = "all") -> list:
    """
    多维明细透视表：按日期 x 渠道聚合明细数据
    """
    start_dt = date_info["start_dt"]
    end_dt = date_info["end_dt"]

    # 1. 查每日每渠道的访问量和去重设备
    access_q = Q(access_time__range=(start_dt, end_dt))
    if channel != "all":
        access_q &= Q(channel=channel)
    if platform != "all":
        access_q &= Q(platform=platform)

    daily_access = (
        Access.objects.filter(access_q)
        .annotate(day=TruncDate("access_time"))
        .values("day", "channel", "platform")
        .annotate(pv=Count("id"), dau=Count("device_id", distinct=True))
        .order_by("-day", "channel")
    )

    # 转换为字典方便映射
    table_rows = []
    for row in daily_access[:200]:  # 限制最多200条避免过大
        d_str = row["day"].strftime("%Y-%m-%d") if row["day"] else "-"
        ch = row["channel"] or "未知渠道"
        pl = row["platform"] or "未知平台"
        pv = row["pv"]
        dau = row["dau"]

        table_rows.append(
            {
                "date": d_str,
                "channel": ch,
                "platform": pl,
                "pv": pv,
                "dau": dau,
            }
        )

    return table_rows


def export_bi_csv(table_data: list) -> str:
    """
    将明细透视表转换为 CSV 字符串
    """
    import io

    output = io.StringIO()
    # 写入 UTF-8 BOM 避免 Excel 打开乱码
    output.write("\ufeff")
    writer = csv.writer(output)

    writer.writerow(["日期", "渠道", "平台", "访问PV", "活跃设备(DAU)"])
    for row in table_data:
        writer.writerow([row["date"], row["channel"], row["platform"], row["pv"], row["dau"]])

    return output.getvalue()
