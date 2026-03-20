import logging
import random
import string
import uuid
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

from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import UserProfileSerializer

logger = logging.getLogger(__name__)


class ApiModelView(CreateModelMixin, GenericViewSet):
    queryset = User.objects.select_related("profile").all()
    serializer_class = UserProfileSerializer
    # permission_classes = [HasAccessKey, IsAuthenticated]
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    def create(self, request, *args, **kwargs):
        """校验验证码"""
        code = request.data.get("code")
        if not code:
            return Response({"error": "缺少code参数"}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get("email")
        phone = request.data.get("phone")

        if email:
            code_cache_key = f"email_verification_code:{email}"
        elif phone:
            code_cache_key = f"phone_verification_code:{phone}"
        else:
            return Response({"error": "缺少email或phone参数"}, status=status.HTTP_400_BAD_REQUEST)

        cached_code = cache.get(code_cache_key)

        if not cached_code:
            return Response({"error": "验证码已过期或不存在"}, status=status.HTTP_400_BAD_REQUEST)

        if cached_code != code:
            return Response({"error": "验证码错误"}, status=status.HTTP_400_BAD_REQUEST)

        # 验证成功后，返回reset_token，用于后续的重置密码请求必须携带此令牌，确保流程连续性。
        reset_token = str(uuid.uuid4()).replace("-", "")
        token_cache_key = f"reset_token:{reset_token}"
        expire_time = 60 * 10  # 验证码过期时间，单位秒，10分钟
        cache.set(token_cache_key, email, expire_time)

        cache.delete(code_cache_key)
        return Response({"msg": "验证成功", "reset_token": reset_token})

    @action(detail=False, methods=["post"])
    def reset_password(self, request):
        """重置密码（需要验证验证码返回的reset_token，用于忘记密码邮箱重置的场景，不需要用户登录状态）"""
        reset_token = request.data.get("reset_token")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not new_password or not confirm_password or new_password != confirm_password:
            return Response({"error": "new_password 和 confirm_password 不能为空 或不一致"}, status=status.HTTP_400_BAD_REQUEST)

        # 验证新密码长度
        if len(new_password) < 6:
            return Response({"error": "新密码长度不能少于6位"}, status=status.HTTP_400_BAD_REQUEST)

        # 验证reset_token
        if not reset_token:
            return Response({"error": "reset_token 不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        # 验证reset_token是否匹配
        token_cache_key = f"reset_token:{reset_token}"
        cached_email = cache.get(token_cache_key)
        if not cached_email:
            return Response({"error": "reset_token 错误"}, status=status.HTTP_400_BAD_REQUEST)
        cache.delete(token_cache_key)

        try:
            user = User.objects.get(email=cached_email)
            user.set_password(new_password)
            user.save(update_fields=["password"])
            logger.info(f"用户 {user.id} {user.username} 重置密码成功")
            return Response({"msg": "密码重置成功"})
        except Exception as e:
            logger.error(f"用户 {user.id} {user.username} 重置密码失败: {e}", exc_info=True)
            return Response({"error": f"重置密码失败: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def send_email_verification_code(self, request, *args, **kwargs):
        # 发送邮件验证码
        to_email = request.data.get("email")
        if not to_email:
            return Response({"error": "缺少email参数"}, status=status.HTTP_400_BAD_REQUEST)

        # 无论邮箱是否存在，都返回“发送成功”的通用提示，避免邮箱枚举攻击
        # if User.objects.filter(email=to_email).exists():
        #     return Response({"error": "该邮箱已被注册"}, status=status.HTTP_400_BAD_REQUEST)

        verification_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        expire_time = 60 * 10  # 验证码过期时间，单位秒，10分钟
        year = datetime.now().year  # 获取当前年份

        # 缓存验证码
        cache_key = f"email_verification_code:{to_email}"
        cache.set(cache_key, verification_code, expire_time)

        # 发送邮件

        # 发送注册邮件的验证码，内容不太一样
        # content = {"verification_code": verification_code, "expire_minutes": round(expire_time / 60), "year": year}
        # # templates/ 前缀 不应该出现在模板名里（Django 会在 app 的 templates 目录中查找），改为 emails/...
        # text_content = render_to_string("emails/verification.txt", context=content)
        # html_content = render_to_string("emails/verification.html", context=content)
        # msg = EmailMultiAlternatives(
        #     subject="Ego Wallpaper 本我壁纸注册验证码",
        #     body=text_content,
        #     from_email=f"本我壁纸 <{settings.EMAIL_HOST_USER}>",
        #     to=[to_email],
        #     # headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},  # 可选的退订头
        # )

        content = {"verification_code": verification_code, "expire_minutes": round(expire_time / 60), "year": year}
        text_content = render_to_string("wallpaper/emails/reset_password.txt", context=content)
        html_content = render_to_string("wallpaper/emails/reset_password.html", context=content)

        msg = EmailMultiAlternatives(
            subject="安全通知 - 验证码",
            body=text_content,
            from_email=f"Ego Wallpaper 本我壁纸 <{settings.EMAIL_HOST_USER}>",
            to=[to_email],
            # headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},  # 可选的退订头
        )

        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return Response({"msg": f"{to_email} 邮件已发送"})

    @action(detail=False, methods=["post"])
    def send_phone_verification_code(self, request, *args, **kwargs):
        # 发送短信验证码
        to_phone = request.data.get("phone")
        if not to_phone:
            return Response({"error": "缺少phone参数"}, status=status.HTTP_400_BAD_REQUEST)

        # 无论手机号是否存在，都返回“发送成功”的通用提示，避免手机号枚举攻击
        # if User.objects.filter(profile__phone_number=to_phone).exists():
        #     return Response({"error": "该手机号已被注册"}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: 检查手机号是否合法

        # TODO: 发送验证码
