from datetime import timezone as dt_timezone

from django.contrib.auth.models import User
from django.db import models
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# from django.db.models.functions import Now


# 1.生成模型
# python manage.py makemigrations polls

# 2.显示生成的sql语句，用处不大
# python manage.py sqlmigrate polls 0001

# 3.执行sql语句
# python manage.py migrate polls

# 4.加载初始化数据，覆盖已有数据
# python manage.py loaddata polls/initial_data

# 设置 USE_TZ = True 数据库默认存储UTC时间，Django会自动转换成当前时区的时间
# 设置 USE_TZ = False 数据库默认存储当前时区的时间，Django不会转换时间，不推荐

# 关联关系（如 ForeignKey， OneToOneField， 或 ManyToManyField）
# 默认时间（auto_now_add=True 是创建记录时自动设置当前时间，auto_now=True 是每次保存记录时自动更新为当前时间，default=timezone.now 是可以多次修改，3种互斥只能选择1种）


class Application(models.Model):
    """
    wallpaper: 本我壁纸-ego
    pokemon: 宝可梦壁纸-pokemon
    """

    name = models.CharField(max_length=60, unique=True, verbose_name="应用名称")
    logo_url = models.CharField(max_length=255, verbose_name="logo图片url", blank=True, null=True)
    enable = models.BooleanField(default=True, verbose_name="状态")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "app应用"
        verbose_name_plural = "App应用管理"


class Classify(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="分类名称", db_comment="db_comment中显示的名称: 分类名称")
    name_en = models.CharField(max_length=100, unique=True, verbose_name="分类英文名称", blank=True, null=True)
    sort = models.IntegerField(verbose_name="排序")
    picurl = models.CharField(max_length=255, verbose_name="图片地址")
    select = models.BooleanField(default=False, verbose_name="是否首页推荐")
    enable = models.BooleanField(default=True, verbose_name="是否启用")  # is_active
    is_locked = models.BooleanField(default=False, verbose_name="需要解锁")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    # default 是给模型设置默认值，db_default 是给数据库设置默认值，推荐
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "分类"  # 点击列表处，该模型的标题显示的内容
        verbose_name_plural = "壁纸分类"  # admin列表处显示的是该字段，如果没有该字段会使用verbose_name并末尾增加个s


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="专题名称", db_comment="db_comment中显示的名称: 分类名称")
    content = models.TextField(verbose_name="专题内容", blank=True, null=True)
    sort = models.IntegerField(verbose_name="排序")
    picurl = models.CharField(max_length=255, verbose_name="图片地址")
    select = models.BooleanField(default=False, verbose_name="是否首页推荐")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    is_locked = models.BooleanField(default=False, verbose_name="是否需要解锁")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "专题"
        verbose_name_plural = "壁纸专题"


class Wall(models.Model):
    # small_picurl = models.CharField(max_length=255, verbose_name="图片缩略图地址")
    picurl = models.CharField(max_length=255, verbose_name="图片地址")
    description = models.CharField(max_length=255, verbose_name="描述", blank=True, null=True)
    publisher = models.CharField(max_length=60, default="unknown", verbose_name="发布者", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    is_locked = models.BooleanField(default=False, verbose_name="是否需要解锁")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    classify = models.ForeignKey(Classify, on_delete=models.PROTECT, verbose_name="分类")  # 外键写表名即可

    # 这个字段其实可以设计成 ManyToManyField，其实就是列表存储，使用add方法添加
    tabs = models.CharField(max_length=200, verbose_name="标签", blank=True, null=True)
    score = models.DecimalField(max_digits=10, decimal_places=1, verbose_name="图片分数", blank=True, null=True)
    views = models.IntegerField(default=0, verbose_name="浏览量")
    downloads = models.IntegerField(default=0, verbose_name="下载量")

    # 多对多关系，不会添加该字段，会增加一张存储对应关系的中间表wallpaper_wall_subjects，里面只有三个字段 id、wall_id、subject_id
    subjects = models.ManyToManyField(Subject, related_name="walls", verbose_name="专题", blank=True)

    def __str__(self):
        return self.description if self.description else f"壁纸-{self.pk}"

    class Meta:
        verbose_name = "壁纸"
        verbose_name_plural = "壁纸信息"


class Notice(models.Model):
    title = models.CharField(max_length=200, verbose_name="公告标题")
    content = models.TextField(verbose_name="公告详情")
    select = models.BooleanField(default=False, verbose_name="是否置顶")
    author = models.CharField(max_length=60, verbose_name="发布者")
    article_status = models.BooleanField(default=True, verbose_name="公告状态")
    publish_date = models.DateTimeField(default=timezone.now, verbose_name="发布时间")
    view_count = models.IntegerField(default=0, verbose_name="浏览量")

    def increase_view_count(self):
        # 原子自增，避免并发冲突，未使用
        Notice.objects.filter(pk=self.pk).update(view_count=F("view_count") + 1)
        self.refresh_from_db(fields=["view_count"])  # 刷新实例字段值

    def __str__(self):
        return f"{self.title} - {self.publish_date}"

    class Meta:
        verbose_name = "公告"
        verbose_name_plural = "公告信息"


class Banner(models.Model):
    url = models.CharField(max_length=200, verbose_name="跳转链接地址")
    sort = models.IntegerField(verbose_name="排序字段")
    picurl = models.CharField(max_length=255, verbose_name="缩略图")
    target = models.CharField(max_length=60, verbose_name="跳转方式，默认：self，外站：miniProgram")
    appid = models.CharField(max_length=100, verbose_name="外部小程序的app-id", blank=True, null=True)
    enable = models.BooleanField(default=True, verbose_name="是否启用")  # is_active
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    # def __str__(self):
    #     return f"{self.url}"

    class Meta:
        verbose_name = "首页横幅"
        verbose_name_plural = "首页横幅_plural"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nickname = models.CharField(max_length=60, verbose_name="用户昵称", blank=True, null=True)
    avater = models.CharField(max_length=150, verbose_name="头像", blank=True, null=True)
    phone_number = models.CharField(max_length=20, verbose_name="电话号码", blank=True, null=True)
    source = models.CharField(max_length=60, verbose_name="来源", blank=True, null=True)
    ip = models.CharField(max_length=60, verbose_name="ip地址")
    region = models.CharField(max_length=60, verbose_name="行政区省市县", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    wechat_openid = models.CharField(max_length=100, verbose_name="微信openid", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} 的个人资料"

    class Meta:
        verbose_name = "个人信息"
        verbose_name_plural = "用户个人信息s"


# # 自动创建Profile对象
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)

# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     if hasattr(instance, 'profile'):
#         instance.profile.save()


class Rate(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, verbose_name="用户id")
    wall = models.ForeignKey(Wall, on_delete=models.DO_NOTHING, null=True, verbose_name="壁纸id")
    pic_score = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="壁纸分数")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "用户评分"
        verbose_name_plural = "用户评分"


class PageView(models.Model):
    url = models.CharField(max_length=255, verbose_name="url地址")
    pv = models.IntegerField(default=0, verbose_name="页面访问量")

    class Meta:
        verbose_name = "页面访问量"
        verbose_name_plural = "页面访问量统计"


class Access(models.Model):
    ip = models.CharField(max_length=100, verbose_name="ip地址")  #  models.GenericIPAddressField
    address = models.CharField(max_length=255, verbose_name="访问地址", blank=True, null=True)
    # device_id = models.CharField(max_length=100, verbose_name="设备id", blank=True, null=True)
    # app_version = models.CharField(max_length=100, verbose_name="app版本号", blank=True, null=True)
    username = models.CharField(max_length=100, verbose_name="用户名", blank=True, null=True)

    # client = models.CharField(max_length=100, verbose_name="", blank=True, null=True)  # 客户端类型，如：web、android、ios、wechat、douyin、qq等
    # provider = models.CharField(max_length=100, verbose_name="", blank=True, null=True)

    # 如：app(android\ios)、web、mp-weixin、mp-douyin等，对应uniapp的多端 uniPlatform 或 platform
    platform = models.CharField(max_length=100, verbose_name="平台", blank=True, null=True)
    # 如：google、小米、oppo、vivo、apple等应用商店
    channel = models.CharField(max_length=100, verbose_name="渠道", blank=True, null=True)

    access_time = models.DateTimeField(auto_now_add=True, verbose_name="访问时间")
    remark = models.JSONField(default=dict, verbose_name="备注", blank=True, null=True)  # desciption

    def __str__(self):
        # 将access_time转换为本地时区的时间字符串，也就是settings.py中设置的TIME_ZONE对应的时区
        local_tz = timezone.get_default_timezone()
        # 使用strftime来格式化日期时间，截取前19个字符
        formatted_time = self.access_time.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S")
        return f"{formatted_time} - {self.platform} - {self.ip}"

    class Meta:
        verbose_name = "访问日志详情"
        verbose_name_plural = "访问日志"
