import logging

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from utils.tools import generate_nickname, get_client_ip, ip_to_region

from ..models import Profile
from ..permissions import HasAccessKey

# from ..serializers import ProfileSerializer
from ..renderers import CustomJSONRenderer

logger = logging.getLogger(__name__)


class ApiModelView(CreateModelMixin, GenericViewSet):
    queryset = User.objects.select_related("profile").all()
    # serializer_class = ProfileSerializer
    permission_classes = [HasAccessKey]
    permission_classes = []
    renderer_classes = [CustomJSONRenderer]

    def create(self, request, *args, **kwargs):
        """默认email登录"""
        data = request.data.copy()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return Response({"error": "缺少email或password参数"}, status=status.HTTP_400_BAD_REQUEST)

        user = self.queryset.filter(email=email).first()
        # if not user:
        #     return Response({"error": "用户不存在"}, status=status.HTTP_400_BAD_REQUEST)

        # if not user.check_password(password):
        #     return Response({"error": "密码错误"}, status=status.HTTP_400_BAD_REQUEST)

        # if not user.is_active:
        #     return Response({"error": "用户未激活"}, status=status.HTTP_400_BAD_REQUEST)

        if not user or not user.check_password(password) or not user.is_active:
            # raise AuthenticationFailed("Invalid Email or Password")
            return Response({"error": "Invalid Email or Password"}, status=status.HTTP_401_UNAUTHORIZED)

        # 更新最后登录时间
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # 如果profile不存在，创建一条记录
        if not hasattr(user, "profile"):
            Profile.objects.create(user=user, nickname=generate_nickname())

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                # 'success': True,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user_id": user.id,
            }
        )

    @action(detail=False, methods=["post"])
    def wechat(self, request):
        # 1. 获取前端传来的 code
        code = request.data.get("code")
        if not code:
            return Response({"error": "缺少code参数"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 用 code 换 openid
        openid = self._get_wechat_openid(code)
        if not openid:
            return Response({"error": "微信登录失败 Invalid code"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 查找用户，不存在则创建
        user = User.objects.select_related("profile").filter(profile__wechat_openid=openid).first()

        ip_address = get_client_ip(request)
        # region = self._get_region(ip)  # 获取IP地址对应的地区信息，aws外部接口调用存在问题，暂时注释
        region = ip_to_region(ip_address)

        if user:
            if not user.is_active:
                raise AuthenticationFailed("User is not active")
        else:
            username = f"wechat_{openid}"
            # password = User.objects.make_random_password()
            source = "wechat"
            user = User.objects.create_user(username=username)  # 创建User表数据
            Profile.objects.create(
                user=user, wechat_openid=openid, ip_address=ip_address, region=region, channel="wechat", source=source
            )  # 创建Profile表数据

        # 4. 生成JWT
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                # 'success': True,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user_id": user.id,
                "openid": openid,
            }
        )

    @action(detail=False, methods=["post"])
    def mobile(self, request):
        pass

    @action(detail=False, methods=["post"])
    def google(self, request):
        pass

    @action(detail=False, methods=["post"])
    def apple(self, request):
        pass

    def _get_wechat_openid(self, code):
        # 获取微信小程序的openid
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": settings.WECHAT_APPID,
            "secret": settings.WECHAT_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            # {'session_key': 'hkDdAFzHEBa2yIYk6VC90w==', 'openid': 'oqp6q7XoU8sdJ2UpAVJWug6SM8_U'}
            return data.get("openid")
        except Exception as e:
            logger.error(f"Wechat openid 获取失败: {e}")
            return None

    def _get_region(self, ip):
        url = "http://whois.pconline.com.cn/ipJson.jsp"
        params = {"ip": ip, "json": "true"}

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
            return ",".join([x for x in [province, city, region] if x])

        except Exception as e:
            # 异常处理，url问题、请求超时等 e.args / str(e) / repr(e)
            logger.error(f"系统异常: {e}")
            region = f"error: {e}"
            return region
            # return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
