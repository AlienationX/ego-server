from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.response import Response
from rest_framework.decorators import action

from ..models import Notice
from ..serializers import NoticeSerializer
from ..renderers import CustomJSONRenderer
from ..paginations import CustomPageNumberPagination


class ApiModelView(ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def get_queryset(self):
        queryset = self.queryset.filter(article_status=True)
        return queryset

    def list(self, request, *args, **kwargs):
        # 动态修改分页器的 page_size，只显示 6 个公告
        self.paginator.page_size = 6
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        # 假设 'publish_date' 是你要倒序排列的字段，- 代表倒序的意思
        latest_queryset = self.get_queryset().order_by('-publish_date')[:3]

        # 将查询集序列化
        serializer = self.get_serializer(latest_queryset, many=True)

        return Response(serializer.data)
