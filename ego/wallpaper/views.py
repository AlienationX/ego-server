import logging

from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

# from .models import Banner, Classify, Notice, Wall
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


def upload(request):
    return render(request, "wallpaper/upload.html")
