from rest_framework import status
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
        channel = self.request.query_params.get("channel")
        platform = self.request.query_params.get("platform")

        if not channel:
            return Response({"error": "必须指定渠道参数"}, status=status.HTTP_400_BAD_REQUEST)

        obj = self.get_queryset().filter(channel=channel).first()
        if not obj:
            # 未匹配到时返回预设默认值
            obj = self.get_queryset().filter(channel="default").first()
            obj.update_title = f"channel:{channel}, platform:{platform}"

        return Response(self.get_serializer(obj, many=False).data)

    def retrieve(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object(), many=False).data)
