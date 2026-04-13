from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Classify
from ..renderers import CustomJSONRenderer
from ..serializers import ClassifySerializer


class ApiModelView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Classify.objects.all()
    serializer_class = ClassifySerializer
    pagination_class = None  # 不使用分页器，直接返回所有数据
    renderer_classes = [CustomJSONRenderer]

    def get_queryset(self):
        return self.queryset.order_by("sort", "id")

    def list(self, request, *args, **kwargs):
        # 获取查询参数中的 select
        select = self.request.query_params.get("select")
        select = True if select == "true" else False

        # 获取所有数据
        queryset = self.get_queryset().filter(enable=True)

        # 如果 select 参数存在，则过滤查询集
        if select:
            queryset = queryset.filter(select=select)
            # select=true即首页显示的分类，只显示8条即可
            return queryset[:8]

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def all(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def update_picurl(self, request, pk=None):
        instance = self.get_object()
        picurl = request.data.get("picurl")
        if not picurl:
            return Response({"error": "picurl is required"}, status=400)
        instance.picurl = picurl
        instance.save(update_fields=["picurl"])
        return Response({"id": instance.id, "picurl": instance.picurl})
