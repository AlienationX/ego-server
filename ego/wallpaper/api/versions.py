from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Versions
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import VersionsSerializer


class ApiModelView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Versions.objects.all()
    serializer_class = VersionsSerializer
    permission_classes = [HasAccessKey]
    pagination_class = None  # 不使用分页器，直接返回所有数据
    renderer_classes = [CustomJSONRenderer]
    lookup_field = "channel"  # 使用 channel 作为 pk 字段进行查找

    def list(self, request, *args, **kwargs):
        channel = self.request.query_params.get("channel", "official")
        platform = self.request.query_params.get("platform")
        app_version = self.request.query_params.get("app_version")

        qs = self.get_queryset()
        if platform:
            qs = qs.filter(platform=platform)
        if channel:
            qs = qs.filter(channel=channel)
        if app_version:
            qs = qs.filter(app_version=app_version)

        obj = qs.first()

        # 如果特定平台/版本未配置，兜底按 platform 查询全平台通用版本
        if not obj and platform:
            obj = Versions.objects.filter(platform=platform).first()

        if not obj:
            # 默认兜底配置
            return Response({
                "platform": platform or "all",
                "channel": channel or "official",
                "app_version": app_version or "1.0.0",
                "ad_enabled": True,
                "is_force_update": False,
                "app_store_url": "",
                "update_title": "",
                "update_log": ""
            })

        return Response(self.get_serializer(obj, many=False).data)

    def retrieve(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object(), many=False).data)
