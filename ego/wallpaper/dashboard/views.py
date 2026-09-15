from datetime import datetime
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from . import service


@staff_member_required
def bi_dashboard_view(request):
    """
    BI 数据看板主页面视图
    """
    filter_opts = service.get_filter_options()
    context = {
        "channels": filter_opts["channels"],
        "platforms": filter_opts["platforms"],
    }
    return render(request, "wallpaper/dashboard.html", context)


@staff_member_required
def bi_api_data_view(request):
    """
    BI 异步数据接口：提供指标卡、趋势图、占比图、壁纸排行及明细表数据
    """
    days = int(request.GET.get("days", 7))
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    channel = request.GET.get("channel", "all").strip()
    platform = request.GET.get("platform", "all").strip()
    granularity = request.GET.get("granularity", "day").strip()

    date_info = service.parse_date_range(start_date_str, end_date_str, days)

    cards = service.get_bi_overview_cards(date_info, channel, platform)
    trends = service.get_bi_trends(date_info, channel, platform, granularity)
    distributions = service.get_bi_distributions(date_info, channel, platform)
    wallpaper_rank = service.get_bi_wallpaper_rank(date_info, channel, limit=20)
    detail_table = service.get_bi_detail_table(date_info, channel, platform)

    return JsonResponse(
        {
            "code": 200,
            "message": "success",
            "data": {
                "date_info": {
                    "start_date": str(date_info["start_date"]),
                    "end_date": str(date_info["end_date"]),
                    "period_days": date_info["period_days"],
                },
                "cards": cards,
                "trends": trends,
                "distributions": distributions,
                "wallpaper_rank": wallpaper_rank,
                "detail_table": detail_table,
            },
        }
    )


@staff_member_required
def bi_api_export_view(request):
    """
    导出 BI 明细数据为 CSV 文件
    """
    days = int(request.GET.get("days", 7))
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    channel = request.GET.get("channel", "all").strip()
    platform = request.GET.get("platform", "all").strip()

    date_info = service.parse_date_range(start_date_str, end_date_str, days)
    detail_table = service.get_bi_detail_table(date_info, channel, platform)
    csv_content = service.export_bi_csv(detail_table)

    filename = f"ego_bi_report_{date_info['start_date']}_{date_info['end_date']}.csv"
    response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
