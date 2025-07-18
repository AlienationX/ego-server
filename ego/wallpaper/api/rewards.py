import logging

from django.db import connection
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer

logger = logging.getLogger(__name__)


class ApiModelView(ViewSet):

    permission_classes = []  # uni-ad设置的回调函数，不支持key或token的设置，暂时关闭
    # pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):

        queryParams = request.query_params
        logger.info(f"Rewards received query parameters: {queryParams}")

        return Response(queryParams)
