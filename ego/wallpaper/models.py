from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
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


# 关联关系（如 ForeignKey， OneToOneField， 或 ManyToManyField）

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
    sort = models.IntegerField(verbose_name="排序")
    picurl = models.CharField(max_length=255, verbose_name="图片地址")
    select = models.BooleanField(default=False, verbose_name="是否首页推荐")
    enable = models.BooleanField(default=True, verbose_name="是否启用")  # is_active
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")  # auto_now_add=True auto_now=True
    # default 是给模型设置默认值，db_default 是给数据库设置默认值，推荐
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="更新时间")

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
    enable = models.BooleanField(default=True, verbose_name="是否启用")  # is_active
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")  # auto_now_add=True auto_now=True
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="更新时间")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "专题"
        verbose_name_plural = "壁纸专题"


class Wall(models.Model):
    # small_picurl = models.CharField(max_length=255, verbose_name="图片缩略图地址")
    picurl = models.CharField(max_length=255, verbose_name="图片地址")
    description = models.CharField(max_length=255, verbose_name="描述", blank=True, null=True)
    # 这个字段其实可以设计成 ManyToManyField，其实就是列表存储，使用add方法添加
    tabs = models.CharField(max_length=200, verbose_name="标签", blank=True, null=True)
    score = models.DecimalField(max_digits=10, decimal_places=1, verbose_name="图片分数", blank=True, null=True)
    publisher = models.CharField(max_length=60, default="unknown", verbose_name="发布者")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="更新时间")
    classify = models.ForeignKey(Classify, on_delete=models.PROTECT, verbose_name="分类")  # 外键写表名即可
    subjects = models.ManyToManyField(Subject, related_name='walls', verbose_name="专题", blank=True)  # 多对多关系

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
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")

    # def __str__(self):
    #     return f"{self.url}"

    class Meta:
        verbose_name = "首页横幅"
        verbose_name_plural = "首页横幅_plural"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nickname = models.CharField(max_length=60, verbose_name="用户昵称", blank=True, null=True)
    avater = models.CharField(max_length=150, verbose_name="头像", blank=True, null=True)
    phone_number = models.CharField(max_length=20, verbose_name="电话号码", blank=True, null=True)
    source = models.CharField(max_length=60, verbose_name="来源", blank=True, null=True)
    ip = models.CharField(max_length=60, verbose_name="ip地址")
    region = models.CharField(max_length=60, verbose_name="行政区省市县", blank=True, null=True)
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="更新时间")
    wechat_openid = models.CharField(max_length=100, verbose_name="微信openid", blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} 的个人资料'

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
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="更新时间")

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
    ip = models.CharField(max_length=100, verbose_name="ip地址")
    username = models.CharField(max_length=100, verbose_name="用户名")
    source = models.CharField(max_length=100, verbose_name="来源")
    access_time = models.DateTimeField(default=timezone.now, verbose_name="访问时间")

    class Meta:
        verbose_name_plural = "请求访问信息"
