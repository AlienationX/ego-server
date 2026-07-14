import logging
import time
from pathlib import Path

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from ..business_status import BusinessStatus
from ..models import Profile, UserActions, EnergyLog
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..responses import BusinessResponse
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
            # TODO 优化：缓存 UserActions.object.filter(user_id=user_id, action_value__gt=0)
            # user_actions_list = list(UserActions.objects.filter(user_id=user_id, action_value__gt=0))
            user_actions = UserActions.objects.filter(user_id=user_id, action_value__gt=0)
            favorite_count = user_actions.filter(action_key="favorite").count()
            download_count = user_actions.filter(action_key="download").count()
            rate_count = user_actions.filter(action_key="rate").count()
            data["count"] = {
                "favorite_count": favorite_count,
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

        # QueryDict 的值是列表，转成普通 dict 取单值，避免 setattr 写入列表
        data = {k: (v[0] if isinstance(v, list) and len(v) == 1 else v) for k, v in data.items()}

        uploaded_file = request.FILES.get("avatar")
        file_save_path = None  # 初始化，避免异常捕获时 NameError
        if uploaded_file:
            try:
                avatar_url, file_save_path = self._update_avatar(uploaded_file, user.id)
                data["avatar"] = avatar_url
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 更新对应用户的Profile模型
        try:
            profile = user.profile

            # 只有本次请求确实上传了新头像，才记录旧路径准备替换
            old_avatar_path = None
            if uploaded_file and profile.avatar:
                old_avatar_path = Path(settings.MEDIA_ROOT) / "wallpaper" / Path(profile.avatar)

            # 更新数据，类似于 profile.avatar = avatar_url, profile.name = name
            update_fields = list(data.keys())
            for attr, value in data.items():
                setattr(profile, attr, value)

            # 同步更新 updated_at（auto_now 字段需要通过 save() 触发，无需显式列出）
            if "updated_at" not in update_fields:
                update_fields.append("updated_at")

            profile.save(update_fields=update_fields)

            # 上传新头像且数据库更新成功后，才删除旧的头像文件
            if old_avatar_path and old_avatar_path.exists():
                old_avatar_path.unlink()

        except Exception as e:
            # 如果更新数据库失败，可以考虑删除刚上传的文件
            if file_save_path and file_save_path.exists():
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
        file_save_path = Path(settings.MEDIA_ROOT) / "wallpaper" / Path(avatar_url)

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
            return BusinessResponse({"error": "新密码和确认密码不一致"}, business_status=BusinessStatus.AUTH_ERROR)

        # 验证旧密码
        if not user.check_password(old_password):
            return BusinessResponse({"error": "旧密码错误"}, business_status=BusinessStatus.AUTH_ERROR)

        # 验证新密码长度
        if len(new_password) < 6:
            return BusinessResponse({"error": "新密码长度不能少于6位"}, business_status=BusinessStatus.AUTH_ERROR)

        # 设置新密码
        try:
            user.set_password(new_password)
            user.save(update_fields=["password"])
            logger.info(f"用户 {user.id} {user.username} 修改密码成功")
            return Response({"msg": "密码修改成功"})
        except Exception as e:
            logger.error(f"用户 {user.id} {user.username} 修改密码失败: {e}")
            return Response({"error": f"修改密码失败: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def deactivate(self, request):
        user = request.user
        user.is_active = False
        user.save()
        return Response({"msg": "用户已停用"})

    @action(detail=False, methods=["post"])
    def consume_energy(self, request):
        """
        消耗能量接口：用于免广告下载壁纸。
        每次成功扣除 1 点能量，能量不足时返回 400 错误。
        记录流水类型为：'consume_download'。
        """
        user = request.user
        wall_id = request.data.get("wall_id")
        
        try:
            profile = user.profile
            if profile.energy > 0:
                profile.energy -= 1
                profile.save(update_fields=["energy"])
                
                EnergyLog.objects.create(
                    user=user,
                    action_type="consume_download",
                    energy_change=-1,
                    wall_id=wall_id
                )
                return Response({"energy": profile.energy})
            else:
                return Response({"error": "能量不足"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"扣除能量失败: {e}")
            return Response({"error": f"扣除能量失败: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def earn_energy(self, request):
        """
        获取能量接口：用于通过观看广告、分享、签到、评分等途径奖励能量（需要登录）。
        防刷限制规则：
        - share_image (分享图片给好友+1)：每天最多获取 3 次奖励
        - share_timeline (分享到朋友圈+3)：每天最多获取 3 次奖励
        - app_rate (App内评价+5)：每个用户终生仅限获取 1 次奖励
        - check_in (每日签到+1)：每天最多获取 1 次奖励
        - watch_ad (观看激励视频广告+3)：目前暂时不限制单日获取次数
        """
        user = request.user
        action_type = request.data.get("action_type")
        amount = request.data.get("amount", 0)
        
        if not action_type:
            return Response({"error": "action_type不能为空"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return Response({"error": "amount必须是整数"}, status=status.HTTP_400_BAD_REQUEST)
            
        if amount <= 0:
            return Response({"error": "amount必须大于0"}, status=status.HTTP_400_BAD_REQUEST)
        
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 防刷限制
        if action_type == "share_image":
            count = EnergyLog.objects.filter(user=user, action_type=action_type, created_at__gte=today_start).count()
            if count >= 3:
                return Response({"energy": user.profile.energy, "msg": "今日分享图片次数已达上限"})
        elif action_type == "share_timeline":
            count = EnergyLog.objects.filter(user=user, action_type=action_type, created_at__gte=today_start).count()
            if count >= 3:
                return Response({"energy": user.profile.energy, "msg": "今日分享朋友圈次数已达上限"})
        elif action_type == "app_rate":
            exists = EnergyLog.objects.filter(user=user, action_type=action_type).exists()
            if exists:
                return Response({"energy": user.profile.energy, "msg": "已经评价过App"})
        elif action_type == "check_in":
            exists = EnergyLog.objects.filter(user=user, action_type=action_type, created_at__gte=today_start).exists()
            if exists:
                return Response({"energy": user.profile.energy, "msg": "今日已签到"})
        
        try:
            profile = user.profile
            profile.energy += amount
            profile.save(update_fields=["energy"])
            
            EnergyLog.objects.create(
                user=user,
                action_type=action_type,
                energy_change=amount
            )
            return Response({"energy": profile.energy})
        except Exception as e:
            logger.error(f"获取能量失败: {e}")
            return Response({"error": f"获取能量失败: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
