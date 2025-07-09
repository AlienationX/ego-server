from django.db.models import F
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Notice
from ..paginations import CustomPageNumberPagination
from ..renderers import CustomJSONRenderer
from ..serializers import NoticeSerializer


class ApiModelView(ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def get_queryset(self):
        # 'publish_date' 是你要倒序排列的字段，- 代表倒序的意思
        queryset = self.queryset.filter(article_status=True).order_by("-publish_date")
        return queryset

    def list(self, request, *args, **kwargs):
        # 动态修改分页器的 page_size，只显示 6 个公告，公告太多轮播会不方便查看
        self.paginator.page_size = 6
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        重写 GET 方法, view_count浏览量字段每次增加1。
        使用increase_view_count方法可以保持原子性，在数据库层面增加。
        如果在这里使用，在高并发的情况下，多人同时访问同一条公告时，可能会导致浏览量统计不准确只会增加1次，推荐使用F。
            notice.view_count += 1
            notice.save()
        备注：其实正常情况下是前端在onLoad时调用ModelViewSet自动生成的update方法增加浏览量
        """
        instance = self.get_object()  # 获取单个对象

        # instance.increase_view_count()  # 触发计数自增
        # QuerySet.update(view_count=F("view_count") + 1). # queryset才有update方法

        instance.view_count = F("view_count") + 1
        instance.save(update_fields=["view_count"])
        instance.refresh_from_db(fields=["view_count"])  # 刷新实例字段值

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def latest(self, request):
        latest_queryset = self.get_queryset()[:3]

        # 将查询集序列化
        serializer = self.get_serializer(latest_queryset, many=True)

        return Response(serializer.data)
