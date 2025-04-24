from django.db import connection
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response

from ..models import Application
from ..serializers import ApplicationSerializer
from ..renderers import CustomJSONRenderer
from ..paginations import CustomPageNumberPagination

class ApiModelView(ModelViewSet):

    serializer_class = ApplicationSerializer
    # pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def get_queryset(self):
        # 使用 raw() 执行原生 SQL
        sql = """
        SELECT *
        FROM wallpaper_application 
        WHERE id = %s 
        """
        id = self.request.query_params.get("id")
        return Application.objects.raw(sql, [id])  # sql防注入，禁止拼接
    
