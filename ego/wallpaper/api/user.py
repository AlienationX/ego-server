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


class ApiModelView(RetrieveModelMixin, GenericViewSet):

    queryset = Profile.objects.all()
    # serializer_class = ProfileSerializer
    # permission_classes = [HasAccessKey, IsAuthenticated]
    renderer_classes = [CustomJSONRenderer]

    def retrieve(self, request, *args, **kwargs):
        # 获取路径上的pk/id值
        # print(self.kwargs)
        # print(self.kwargs.get('pk'))

        url = "http://whois.pconline.com.cn/ipJson.jsp"
        ip = request.META.get('REMOTE_ADDR')
        params = {"ip": ip, "json": "true"}
        response = requests.get(url, params=params)
        data = response.json()

        # print(data)

        return Response({
            "id": -1,
            "name": "unknown",
            "IP": ip,
            "address": {
                # "country": "中国",
                "province": data["pro"],
                "city": data["city"],
                "region": data["region"]
            }})
