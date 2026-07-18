from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response

from ..models import Subject
from ..renderers import CustomJSONRenderer
from ..serializers import SubjectSerializer
from ..paginations import CustomPageNumberPagination


class ApiModelView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def get_queryset(self):
        return self.queryset.order_by("sort", "id")

    def list(self, request, *args, **kwargs):
        # 默认仅查询启用的专题
        is_active = self.request.query_params.get("is_active")
        is_active = False if is_active in ("false", "False") else True

        # 首页推荐过滤
        select = self.request.query_params.get("select")
        select = True if select in ("true", "True") else False

        queryset = self.get_queryset()

        if is_active:
            queryset = queryset.filter(is_active=is_active)

        if select:
            queryset = queryset.filter(select=select)

        # 增加分页逻辑
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
