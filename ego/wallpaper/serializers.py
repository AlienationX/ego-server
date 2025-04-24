from rest_framework.serializers import ModelSerializer, CharField, PrimaryKeyRelatedField
from .models import Wall, Classify, Notice, Banner, Application


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
