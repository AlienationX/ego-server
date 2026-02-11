from django.conf import settings
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Feedback
from ..renderers import CustomJSONRenderer
from ..serializers import FeedbackSerializer


class ApiModelView(CreateModelMixin, GenericViewSet):
    # CreateAPIView = (CreateModelMixin, GenericViewSet) # 不能使用CreateAPIView，启动报错

    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    pagination_class = None  # 不使用分页器，直接返回所有数据
    renderer_classes = [CustomJSONRenderer]
    # permission_classes = []  # 这里可以根据需要设置权限类

    # TODO 增加图片上传处理逻辑
