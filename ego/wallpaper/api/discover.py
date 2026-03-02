from django.conf import settings
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer


class ApiModelView(CreateModelMixin, GenericViewSet):
    # CreateAPIView = (CreateModelMixin, GenericViewSet)

    # queryset = Access.objects.all()
    # serializer_class = AccessSerializer
    pagination_class = None  # 不使用分页器，直接返回所有数据
    # authentication_classes = [JSONWebTokenAuthentication]  # JWT 认证, 已在settings中全局配置
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    def create(self, request, *args, **kwargs):
        message = """访问 Ollama Library 官网 [https://ollama.com/library](https://ollama.com/library)
支持的模型model列表（deepseek、qwen等开源模型，1.5b代表15亿个参数，参数越多模型越强，但是也越大，部署起来配置要求更高）
安装ollama后启动：ollama serve
拉取相关模型： ollama pull qwen2.5:1.5b、ollama run deepseek-r1:8b
默认会有一个窗口，可以下载模型和支持对话"""
        return Response({"message": message})
