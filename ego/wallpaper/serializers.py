from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.serializers import (
    CharField,
    EmailField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    SerializerMethodField,
    ValidationError,
)

from wallpaper.utils.daily_featured import DailyFeaturedService

from .models import (
    Access,
    Application,
    Banner,
    Classify,
    Feedback,
    Notice,
    Order,
    Product,
    Profile,
    Subject,
    UserActions,
    Versions,
    Wall,
)


class ApplicationSerializer(ModelSerializer):
    class Meta:
        model = Application
        fields = "__all__"


class ClassifySerializer(ModelSerializer):
    class Meta:
        model = Classify
        fields = "__all__"


class SubjectSerializer(ModelSerializer):
    cover_url = SerializerMethodField()
    preview_walls = SerializerMethodField()
    wall_count = SerializerMethodField()

    class Meta:
        model = Subject
        fields = "__all__"

    def get_cover_url(self, obj):
        first_wall = obj.walls.filter(is_active=True).first()
        if first_wall:
            return first_wall.picurl
        return ""

    def get_preview_walls(self, obj):
        walls = obj.walls.filter(is_active=True)[:3]
        return [w.picurl for w in walls]

    def get_wall_count(self, obj):
        return obj.walls.filter(is_active=True).count()


class WallSerializer(ModelSerializer):
    classify_id = PrimaryKeyRelatedField(source="classify", read_only=True)  # 显示外键表的主键值id
    classify_name = CharField(source="classify.name", read_only=True)
    classify_name_en = CharField(source="classify.name_en", read_only=True)

    effective_access_level = SerializerMethodField()
    unlock_type = SerializerMethodField()
    is_daily_free = SerializerMethodField()
    is_daily_ad = SerializerMethodField()
    is_locked = SerializerMethodField()

    class Meta:
        model = Wall
        exclude = (
            "classify",
            "is_active",
            "md5_hash",
            "content_hash",
            "remark",
            "trends",
            "normalized_trends",
            "subjects",
        )

    def _get_featured_info(self, obj):
        if not hasattr(self, "_cached_daily_featured"):
            self._cached_daily_featured = DailyFeaturedService.get_daily_featured_ids()
            self._cached_service = DailyFeaturedService

        return self._cached_service.get_effective_access_level(obj, self._cached_daily_featured)

    def get_effective_access_level(self, obj):
        info = self._get_featured_info(obj)
        return info["effective_access_level"]

    def get_unlock_type(self, obj):
        info = self._get_featured_info(obj)
        return info["unlock_type"]

    def get_is_daily_free(self, obj):
        info = self._get_featured_info(obj)
        return info["is_daily_free"]

    def get_is_daily_ad(self, obj):
        info = self._get_featured_info(obj)
        return info["is_daily_ad"]

    def get_is_locked(self, obj):
        info = self._get_featured_info(obj)
        return info["effective_access_level"] > 0


class NoticeSerializer(ModelSerializer):
    class Meta:
        model = Notice
        fields = "__all__"


class BannerSerializer(ModelSerializer):
    class Meta:
        model = Banner
        fields = "__all__"


class ProfileSerializer(ModelSerializer):
    user = PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Profile
        fields = "__all__"


class UserSerializer(ModelSerializer):
    # 使用嵌套序列化器，注意：这默认是只读的
    profile = ProfileSerializer()

    # 如果你不想使用嵌套序列化器，也可以使用source参数来指定要包含的字段，例如：
    # author_name = CharField(source='author.name')
    # author_birth_date = DateField(source='author.birth_date')

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "last_login",
            "profile",
        )  # 按需选择字段，profile是嵌套字段


class UserProfileSerializer(ModelSerializer):
    """用于创建或更新用户及其关联的Profile"""

    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password", "profile")
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, attrs):
        # 至少需要邮箱或手机号之一
        email = attrs.get("email")
        profile = attrs.get("profile") or {}
        phone_number = profile.get("phone_number")

        if not email and not phone_number:
            raise ValidationError("邮箱或手机号至少需要提供一个")

        return attrs

    def create(self, validated_data):

        # 提取Profile相关数据
        profile_data = validated_data.pop("profile", {})
        # 提取密码
        password = validated_data.pop("password")

        with transaction.atomic():
            # 创建User对象
            user = User(**validated_data)
            user.set_password(password)
            user.save()

            # 无论是否传手机号，都确保存在Profile记录
            Profile.objects.update_or_create(user=user, defaults=profile_data)

        return user


class AccessSerializer(ModelSerializer):
    class Meta:
        model = Access
        fields = "__all__"

        # extra_kwargs = {
        #     "ip": {"read_only": True, "required": False},  # 禁止前端传入IP字段  # 但是后端也不能写入ip
        #     "platform": {"min_length": 3},  # 名称至少3个字符
        #     # 'address': {'min_length': 5}  # 地址至少5个字符
        # }


class FeedbackSerializer(ModelSerializer):
    class Meta:
        model = Feedback
        fields = "__all__"


class VersionsSerializer(ModelSerializer):
    class Meta:
        model = Versions
        fields = "__all__"


class UserActionsSerializer(ModelSerializer):
    # 同时返回外键 id 和嵌套对象，保持与 WallSerializer 的风格一致
    user_id = PrimaryKeyRelatedField(source="user", read_only=True)
    wall_id = PrimaryKeyRelatedField(source="wall", read_only=True)

    # 嵌套序列化器用于返回更多信息（只读）
    # user = UserSerializer(read_only=True)
    wall = WallSerializer(read_only=True)

    class Meta:
        model = UserActions
        fields = "__all__"
        # exclude = ["user", "wall"]


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class OrderSerializer(ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
