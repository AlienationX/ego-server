from django.db import connection
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework import status


from ..renderers import CustomJSONRenderer
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey


class ApiModelView(ViewSet):
    
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):
        return Response({"test": "Hello World"})