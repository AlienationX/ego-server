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


class ApiModelView(ViewSet):

    permission_classes = []
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):
        return Response({"test": "Hello World"})
