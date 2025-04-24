from rest_framework.viewsets import ModelViewSet

from ..models import Banner
from ..serializers import BannerSerializer
from ..renderers import CustomJSONRenderer


class ApiModelView(ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    renderer_classes = [CustomJSONRenderer]

    def get_queryset(self):
        # 自定义结果集
        # 获取enable=True的数据并按 'created_at' 字段倒序排序，返回前 4 个滑动图
        return self.queryset.filter(enable=True).order_by('-created_at')[:4]
