import base64
import logging

from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from .models import Banner, Classify, Notice, Wall

# from .paginations import CustomPageNumberPagination
# from .permissions import HasAccessKey
# from .renderers import CustomJSONRenderer
# from .serializers import (
#     BannerSerializer,
#     ClassifySerializer,
#     NoticeSerializer,
#     WallSerializer,
# )

logger = logging.getLogger(__name__)


def index(request):
    return render(request, "wallpaper/index.html")


def upload(request):
    # 全部提交按钮事件
    if request.method == "POST" and request.FILES:
        files = request.FILES.getlist("images")
        items = []
        for idx, f in enumerate(files, start=1):
            content = f.read()
            try:
                b64 = base64.b64encode(content).decode()
                data_url = f"data:{f.content_type};base64,{b64}"
            except Exception:
                data_url = ""

            items.append(
                {
                    "id": idx,
                    "picurl": data_url,
                    "classify_id": f"cid{idx}",
                    "classify_name": "未分类",
                    "description": "",
                    "tags": "",
                    "filename": f.name,
                }
            )

        return render(request, "wallpaper/upload.html")

    # GET: 渲染上传页面
    classify_objects = Classify.objects.all().exclude(name__in=("必应每日壁纸", "宝可梦官方壁纸", "宝可梦睡眠"))
    classcfy_name = [obj.name for obj in classify_objects]
    items = [
        {
            "id": 1,
            "picurl": "",
            "classify_id": "cid1",
            "classify_name": classcfy_name[0] if classcfy_name else "",
            "description": "描述1",
            "tabs": "标签1,标签2",
        },
    ]
    return render(request, "wallpaper/upload.html", {"items": items})
