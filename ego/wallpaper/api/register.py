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
from utils.tools import ip_to_region

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
            profile["ip"] = request.META.get("REMOTE_ADDR", "")
            profile["region"] = ip_to_region(profile["ip"])
            profile["phone_number"] = phone_number
            profile["nickname"] = self._generate_nickname()

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

    def _generate_nickname(self, length=8):
        """生成一个指定长度的随机用户名，包含大小写字母和数字"""
        characters = string.ascii_letters + string.digits  # 大小写字母和数字
        username = "".join(random.choices(characters, k=length))
        return username

    @action(detail=False, methods=["post"])
    def send_email_verification_code(self, request, *args, **kwargs):
        # 发送邮件验证码
        to_email = request.data.get("email")
        if not to_email:
            return Response({"error": "缺少email参数"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=to_email).exists():
            return Response({"error": "该邮箱已被注册"}, status=status.HTTP_400_BAD_REQUEST)

        verification_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        expire_time = 60 * 10  # 验证码过期时间，单位秒，10分钟
        year = datetime.now().year  # 获取当前年份

        # 缓存验证码
        cache_key = f"email_verification_code_{to_email}"
        cache.set(cache_key, verification_code, expire_time)

        # 发送邮件
        content = {"verification_code": verification_code, "expire_minutes": round(expire_time / 60), "year": year}
        # templates/ 前缀 不应该出现在模板名里（Django 会在 app 的 templates 目录中查找），改为 emails/...
        text_content = render_to_string("emails/verification.txt", context=content)
        html_content = render_to_string("emails/verification.html", context=content)

        msg = EmailMultiAlternatives(
            subject="Ego Wallpaper 本我壁纸注册验证码",
            body=text_content,
            from_email=f"本我壁纸 <{settings.EMAIL_HOST_USER}>",
            to=[to_email],
            # headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},  # 可选的退订头
        )

        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return Response({"message": f"{to_email} 邮件已发送"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def verify_email(self, request, *args, **kwargs):

        email = request.data.get("email")
        if not email:
            return Response({"error": "缺少email参数"}, status=status.HTTP_400_BAD_REQUEST)

        code = request.data.get("code")
        if not code:
            return Response({"error": "缺少code参数"}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f"email_verification_code_{email}"
        cached_code = cache.get(cache_key)

        if not cached_code:
            return Response({"error": "验证码已过期或不存在"}, status=status.HTTP_400_BAD_REQUEST)

        if cached_code != code:
            return Response({"error": "验证码错误"}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(cache_key)
        return Response({"message": "验证成功"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def send_phone_verification_code(self, request, *args, **kwargs):
        # 发送短信验证码
        phone_number = request.data.get("phone_number")
        if not phone_number:
            return Response({"error": "缺少phone_number参数"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(profile__phone_number=phone_number).exists():
            return Response({"error": "该手机号已被注册"}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: 检查手机号是否合法

        # TODO: 发送验证码
