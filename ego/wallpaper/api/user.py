import logging
import time
from pathlib import Path

import requests
from django.conf import settings
from django.contrib.auth.models import User
from PIL import Image
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from ..models import Actions, Profile
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import ProfileSerializer, UserSerializer

logger = logging.getLogger(__name__)


class ApiModelView(RetrieveModelMixin, GenericViewSet):
    queryset = User.objects.select_related("profile").all()
    serializer_class = UserSerializer
    # authentication_classes = [JSONWebTokenAuthentication]  # JWT 认证, 已在settings中全局配置
    permission_classes = [HasAccessKey, IsAuthenticated]
    renderer_classes = [CustomJSONRenderer]
    parser_classes = [MultiPartParser, JSONParser]  # 重要：允许处理文件上传, 以及 JSON 格式的数据

    @action(detail=False, methods=["get"])
    def me(self, request):
        # JWT通过，会将user放入到request.user中，没有登录默认返回是AnonymousUser
        user = request.user

        # if not user.is_authenticated:
        #     # /user/1/ 可以直接访问，但 /user/me/ 需要认证
        #     raise AuthenticationFailed("未认证或token无效")  # 401
        #     return Response({"error": "未认证或token无效"}, status=status.HTTP_401_UNAUTHORIZED)  # 效果一样

        try:
            serializer = UserSerializer(user)
            # return Response(serializer.data)  # 直接返回序列化数据

            # 将序列化后的数据复制为可变 dict 并添加统计字段
            data = dict(serializer.data)
            user_id = user.id
            collect_count = Actions.objects.filter(user_id=user_id, is_collect=True).count()
            download_count = Actions.objects.filter(user_id=user_id, is_download=True).count()
            rate_count = Actions.objects.filter(user_id=user_id, pic_score__isnull=False).count()
            data["count"] = {
                "collect_count": collect_count,
                "download_count": download_count,
                "rate_count": rate_count,
            }
            return Response(data)
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return Response({"error": f"获取用户信息失败: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def update_profile(self, request):
        # JWT通过，会将user放入到request.user中，没有登录默认返回是AnonymousUser
        user = request.user

        data = request.data.copy()
        data.pop("email", None)  # 移除email字段 (不允许更新)

        uploaded_file = request.FILES.get("avatar")  # 'avatar' 是前端表单中文件字段的name，postman字段类型不是string，而是file
        if uploaded_file:
            try:
                avatar_url, file_save_path = self._update_avatar(uploaded_file, user.id)
                data["avatar"] = avatar_url
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 更新对应用户的Profile模型
        try:
            profile = user.profile

            old_avatar_path = ""
            if profile.avatar:
                old_avatar_path = Path(settings.MEDIA_ROOT) / Path(profile.avatar)

            # 更新数据，类似于 profile.avatar = avatar_url, profile.name = name
            for attr, value in data.items():
                setattr(profile, attr, value)
            profile.save(update_fields=list(data.keys()))  # 仅更新变化的字段

            # 可选：上传文件成功且数据库更新后，才删除旧的头像文件以释放空间
            if old_avatar_path and old_avatar_path.exists():
                old_avatar_path.unlink()

        except Exception as e:
            # 如果更新数据库失败，可以考虑删除刚上传的文件
            if file_save_path.exists():
                file_save_path.unlink()
            return Response({"error": f"更新数据库失败: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ProfileSerializer(profile).data)

    def _update_avatar(self, uploaded_file, user_id):
        if not uploaded_file:
            raise Exception("未提供文件")

        # 1. 自定义验证：文件大小
        max_size = 1 * 1024 * 1024  # 1MB
        if uploaded_file.size > max_size:
            raise Exception("文件大小不能超过1MB")

        # 2. 自定义验证：文件扩展名
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        ext = Path(uploaded_file.name).suffix
        if ext not in allowed_extensions:
            raise Exception("不支持的文件格式。请上传JPG, JPEG, PNG或WebP图片。")

        # 3. (推荐) 自定义验证：使用PIL检查文件内容是否为有效图片
        try:
            image = Image.open(uploaded_file)
            image.verify()  # 验证图片完整性
            # 重置文件指针，因为verify()或open()操作可能会改变它
            uploaded_file.seek(0)
        except Exception:
            raise Exception("无效的图片文件")

        dt = int(time.time())  # 当前10位时间戳
        avatar_url = f"avatars/user_{user_id}_{dt}{ext}"
        file_save_path = Path(settings.MEDIA_ROOT) / Path(avatar_url)

        # 保存文件到服务器
        try:
            with open(file_save_path, "wb+") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except IOError as e:
            raise Exception(f"文件保存失败 {e.strerror}")

        return avatar_url, file_save_path

    @action(detail=False, methods=["post"])
    def change_password(self, request):
        """修改密码（需要验证旧密码，需要用户登录状态）"""
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not old_password or not new_password or not confirm_password:
            return Response(
                {"error": "old_password, new_password, confirm_password 不能为空"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 验证新密码和确认密码是否一致
        if new_password != confirm_password:
            return Response({"error": "新密码和确认密码不一致"}, status=status.HTTP_400_BAD_REQUEST)

        # 验证旧密码
        if not user.check_password(old_password):
            return Response({"error": "旧密码错误"}, status=status.HTTP_400_BAD_REQUEST)

        # 验证新密码长度
        if len(new_password) < 6:
            return Response({"error": "新密码长度不能少于6位"}, status=status.HTTP_400_BAD_REQUEST)

        # 设置新密码
        try:
            user.set_password(new_password)
            user.save(update_fields=["password"])
            logger.info(f"用户 {user.id} {user.username} 修改密码成功")
            return Response({"msg": "密码修改成功"})
        except Exception as e:
            logger.error(f"用户 {user.id} {user.username} 修改密码失败: {e}")
            return Response({"error": f"修改密码失败: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 类似me接口，但是做权限控制。故暂时不开放，后续再考虑是否需要
    # def retrieve(self, request, *args, **kwargs):
    #     # 获取路径上的pk/id值
    #     # print(self.kwargs)
    #     # print(self.kwargs.get('pk'))

    #     url = "http://whois.pconline.com.cn/ipJson.jsp"
    #     ip = request.META.get('REMOTE_ADDR')
    #     params = {"ip": ip, "json": "true"}

    #     province = ""
    #     city = ""
    #     region = ""

    #     try:
    #         logger.info(f"请求的IP地址: {ip}")
    #         # ​​连接超时​​：3 秒内未建立连接则抛出 ConnectTimeout。
    #         # ​​读取超时​​：连接建立后，5 秒内未收到数据则抛出 ReadTimeout。
    #         response = requests.get(url, params=params, timeout=(2, 1))

    #         response.raise_for_status()

    #         data = response.json()
    #         province = data.get("pro", "")
    #         city = data.get("city", "")
    #         region = data.get("region", "")

    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"IP查询接口请求失败: {e}")
    #         regions = ["地球", "月球", "太阳系", "银河系", "宇宙", "黑洞", "未知", "unknown"]
    #         region = regions[random.randint(0, len(regions)-1)]
    #     except Exception as e:
    #         # 异常处理，url问题、请求超时等 e.args / str(e) / repr(e)
    #         logger.error(f"系统异常: {e}")
    #         region = "error"
    #         # return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    #     return Response({
    #         "id": -1,
    #         "name": "unknown",
    #         "IP": ip,
    #         "address": {
    #             "province": province,
    #             "city": city,
    #             "region": region
    #         }
    #     })
