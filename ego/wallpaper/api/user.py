from django.db import connection
from rest_framework.viewsets import ModelViewSet, ViewSet, GenericViewSet
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import status

from ..models import Profile
# from ..serializers import ProfileSerializer
from ..renderers import CustomJSONRenderer
from ..permissions import HasAccessKey

import requests

import random
import logging

logger = logging.getLogger(__name__)


class ApiModelView(RetrieveModelMixin, GenericViewSet):

    queryset = Profile.objects.all()
    # serializer_class = ProfileSerializer
    # permission_classes = [HasAccessKey, IsAuthenticated]
    permission_classes = []
    renderer_classes = [CustomJSONRenderer]

    def retrieve(self, request, *args, **kwargs):
        # 获取路径上的pk/id值
        # print(self.kwargs)
        # print(self.kwargs.get('pk'))

        url = "http://whois.pconline.com.cn/ipJson.jsp"
        ip = request.META.get('REMOTE_ADDR')
        params = {"ip": ip, "json": "true"}

        province = ""
        city = ""
        region = ""

        try:
            logger.info(f"请求的IP地址: {ip}")
            # ​​连接超时​​：3 秒内未建立连接则抛出 ConnectTimeout。
            # ​​读取超时​​：连接建立后，5 秒内未收到数据则抛出 ReadTimeout。
            response = requests.get(url, params=params, timeout=(2, 1))
            
            response.raise_for_status()

            data = response.json()
            province = data.get("pro", "")
            city = data.get("city", "")
            region = data.get("region", "")

        except requests.exceptions.RequestException as e:
            logger.error(f"IP查询接口请求失败: {e}")
            regions = ["地球", "月球", "太阳系", "银河系", "宇宙", "黑洞", "未知", "unknown"]
            region = regions[random.randint(0, len(regions)-1)]
        except Exception as e:
            # 异常处理，url问题、请求超时等 e.args / str(e) / repr(e)
            logger.error(f"系统异常: {e}")
            region = "error"
            # return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "id": -1,
            "name": "unknown",
            "IP": ip,
            "address": {
                "province": province,
                "city": city,
                "region": region
            }
        })