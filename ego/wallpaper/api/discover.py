import json
import logging

import requests
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
        message = "访问 Ollama Library 官网 [https://ollama.com/library](https://ollama.com/library)支持的模型model列表（deepseek、qwen等开源模型，1.5b代表15亿个参数，参数越多模型越强，但是也越大，部署起来配置要求更高）安装ollama后启动：ollama serve拉取相关模型： ollama pull qwen2.5:1.5b、ollama run deepseek-r1:8b默认会有一个窗口，可以下载模型和支持对话，也可以通过api调用。"
        return Response({"message": message})

        img_url = request.data.get("img_url")
        if not img_url:
            return Response({"error": "img_url is required"}, status=status.HTTP_400_BAD_REQUEST)

        prompt = """根据图片内容，回答以下问题：
        1. 用自然柔和的语言，生成图片描述，30字以内
        2. 生成2到5个中英文标签（tag），用英文逗号分隔，逗号之间不要有空格
        3. 在以下分类中选择最合适的一个作为图片分类：
        请将回答内容以json格式返回，key分别为：description, tabs, classify_name
        """

        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {"Authorization": f"Bearer {settings.DECOUPLE_CONFIG('ZHIPU_API_KEY')}", "Content-Type": "application/json"}
        data = {
            # glm-4.7-flash 免费，但只能输入文字
            # https://bigmodel.cn/finance-center/resource-package/package-mgmt
            # glm-4.6v-flash 免费，支持图片输入。glm-4.6v 付费，支持图片输入，2026-03-12到期
            "model": "glm-4.6v",  # glm-4.6v-flash、glm-4.6v 付费
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                # "url": "https://cloudcovert-1305175928.cos.ap-guangzhou.myqcloud.com/%E5%9B%BE%E7%89%87grounding.PNG"
                                # "url": img_base
                                "url": img_url
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            # "thinking": {"type": "enabled"},
            # "stream": True,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            logging.debug(json.dumps(result, indent=2, ensure_ascii=False))

            content = result["choices"][0]["message"]["content"].strip()
            message = json.loads(content)
            return Response({"message": message})

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
