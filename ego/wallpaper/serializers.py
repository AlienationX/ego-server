from rest_framework.serializers import ModelSerializer, CharField, PrimaryKeyRelatedField
from django.contrib.auth.models import User

from .models import Wall, Classify, Notice, Banner, Application, Profile


class ApplicationSerializer(ModelSerializer):
    class Meta:
        model = Application
        fields = "__all__"


class ClassifySerializer(ModelSerializer):
    class Meta:
        model = Classify
        fields = "__all__"


class WallSerializer(ModelSerializer):
    classify_id = PrimaryKeyRelatedField(source="classify", read_only=True)  # 显示外键表的主键值id
    classify_name = CharField(source="classify.name", read_only=True)

    class Meta:
        model = Wall
        # fields = "__all__"
        exclude = ["classify"]


class NoticeSerializer(ModelSerializer):
    class Meta:
        model = Notice
        fields = "__all__"


class BannerSerializer(ModelSerializer):
    class Meta:
        model = Banner
        fields = "__all__"


class ProfileSerializer(ModelSerializer):
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
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'date_joined', 'last_login', 'profile']  # 按需选择字段，profile是嵌套字段
