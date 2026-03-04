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

logger = logging.getLogger(__name__)


class ApiModelView(CreateModelMixin, GenericViewSet):
    # CreateAPIView = (CreateModelMixin, GenericViewSet)

    # queryset = Access.objects.all()
    # serializer_class = AccessSerializer
    pagination_class = None  # 不使用分页器，直接返回所有数据
    # authentication_classes = [JSONWebTokenAuthentication]  # JWT 认证, 已在settings中全局配置
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    def create(self, request, *args, **kwargs):
        # TODO: 校验img_url是否是http开头，还是local图片。如果是local图片，需要转换为base64编码。
        img_url = request.data.get("img_url")
        logger.info(f"Discover Analyze img_url: {img_url}")
        if not img_url:
            return Response({"error": "img_url is required"}, status=status.HTTP_400_BAD_REQUEST)

        prompt = """请扮演一位融合了心理学、艺术评论和人文洞察的分析师。
        我将给你一张我特别喜欢的图片。请你从色彩心理学、构图焦点、象征元素、整体氛围等多个维度，
        分析这张图片可能反映出拥有者怎样的性格特质、潜在爱好和当前的情感或精神需求，
        最后结合基于弗洛伊德的本我、自我、超我理论，给出一个综合的分析结果。
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
                                # "url": img_base64
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
            response = requests.post(url, headers=headers, json=data, timeout=180)
            response.raise_for_status()

            result = response.json()
            logger.debug(json.dumps(result, indent=2, ensure_ascii=False))

            content = result["choices"][0]["message"]["content"].strip()
            return Response({"content": content})

        except Exception as e:
            logging.error(f"Discover Analyze error: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
