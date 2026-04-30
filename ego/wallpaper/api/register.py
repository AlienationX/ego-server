import logging
import random
import string
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet
from utils.tools import generate_nickname, get_client_ip, ip_to_region

from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import UserProfileSerializer, UserSerializer

logger = logging.getLogger(__name__)


class ApiModelView(CreateModelMixin, GenericViewSet):
    queryset = User.objects.select_related("profile").all()
    serializer_class = UserProfileSerializer
    # permission_classes = [HasAccessKey, IsAuthenticated]
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()

            email = data.get("email")
            phone_number = data.get("phone_number")
            if not email and not phone_number:
                return Response({"error": "缺少email或phone_number参数"}, status=status.HTTP_400_BAD_REQUEST)

            if email and User.objects.filter(email=email).exists():
                return Response({"error": "该邮箱已被注册"}, status=status.HTTP_400_BAD_REQUEST)

            if phone_number and User.objects.filter(profile__phone_number=phone_number).exists():
                return Response({"error": "该手机号已被注册"}, status=status.HTTP_400_BAD_REQUEST)

            username = data.get("username")
            if not username:
                # 可以自动生成用户名
                if email:
                    data["username"] = email  # 使用邮箱前缀作为用户名
                elif phone_number:
                    data["username"] = phone_number
                else:
                    data["username"] = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            profile = {}
            profile["ip"] = get_client_ip(request)
            profile["region"] = ip_to_region(profile["ip"])
            profile["phone_number"] = phone_number
            profile["nickname"] = generate_nickname()

            data["profile"] = profile

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            # 手动调用perform_create以确保信号等被正确触发
            self.perform_create(serializer)

            return Response(
                {
                    "user_id": serializer.instance.id,
                    "username": serializer.instance.username,
                    "email": serializer.instance.email,
                    "phone_number": phone_number,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.exception("INTERNAL_SERVER_ERROR")
            return Response({"error": "注册失败", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
