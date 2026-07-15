from datetime import timezone as dt_timezone

from django.contrib.auth.models import User
from django.db import models
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# from django.db.models.functions import Now

# 0.重新从零初始化数据库
# python manage.py migrate --fake <app_name> zero

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
    sort = models.FloatField(verbose_name="排序", blank=True, null=True)
    picurl = models.CharField(max_length=255, verbose_name="图片地址")
    pic_path_prefix = models.CharField(max_length=255, verbose_name="图片所在路径", blank=True, null=True)
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
    name = models.CharField(max_length=100, unique=True, verbose_name="专题名称", db_comment="db_comment中显示的名称: 专题名称")
    name_en = models.CharField(max_length=100, unique=True, verbose_name="专题英文名称", blank=True, null=True)
    content = models.TextField(verbose_name="专题内容", blank=True, null=True)
    content_en = models.TextField(verbose_name="专题英文内容", blank=True, null=True)
    sort = models.FloatField(verbose_name="排序", blank=True, null=True)
    picurl = models.CharField(max_length=255, verbose_name="图片地址")
    select = models.BooleanField(default=False, verbose_name="是否首页推荐")
    tags = models.CharField(max_length=200, verbose_name="标签", blank=True, null=True)
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
    picurl = models.CharField(max_length=255, unique=True, verbose_name="图片地址")
    description = models.CharField(max_length=255, verbose_name="描述", blank=True, null=True)
    description_en = models.CharField(max_length=255, verbose_name="英文描述", blank=True, null=True)
    publisher = models.CharField(max_length=60, default="unknown", verbose_name="发布者", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    is_locked = models.BooleanField(default=False, verbose_name="是否需要解锁")
    md5_hash = models.CharField(max_length=32, verbose_name="MD5哈希值", blank=True, null=True)
    content_hash = models.CharField(max_length=32, verbose_name="内容哈希值", blank=True, null=True)

    width = models.IntegerField(blank=True, null=True, verbose_name="图片宽度")
    height = models.IntegerField(blank=True, null=True, verbose_name="图片高度")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    remark = models.CharField(max_length=500, verbose_name="备注", blank=True, null=True)

    # 1对1关系
    classify = models.ForeignKey(Classify, on_delete=models.PROTECT, verbose_name="分类")  # 外键写表名即可

    # 这个字段其实可以设计成 ManyToManyField，其实就是列表存储，使用add方法添加
    tags = models.CharField(max_length=200, verbose_name="标签", blank=True, null=True)
    tags_en = models.CharField(max_length=200, verbose_name="英文标签", blank=True, null=True)
    # 缓存计数与热度分（应通过信号或定时任务更新）
    score = models.FloatField(verbose_name="图片分数", blank=True, null=True)
    views = models.IntegerField(default=0, db_default=0, verbose_name="浏览量", blank=True, null=True)
    downloads = models.IntegerField(default=0, db_default=0, verbose_name="下载量", blank=True, null=True)
    likes = models.IntegerField(default=0, db_default=0, verbose_name="点赞数", blank=True, null=True)
    favorites = models.IntegerField(default=0, db_default=0, verbose_name="收藏数", blank=True, null=True)
    shares = models.IntegerField(default=0, db_default=0, verbose_name="分享数", blank=True, null=True)
    comments = models.IntegerField(default=0, db_default=0, verbose_name="评论数", blank=True, null=True)

    # 趋势评分，通过加权计算得出
    # 例如 trends = (views * w1 + likes * w2 + favorites * w3 + downloads * w4 + comments * w5 + shares * w6) / time_decay
    trends = models.FloatField(default=0, db_default=0, verbose_name="趋势评分", blank=True, null=True)
    normalized_trends = models.FloatField(default=0, db_default=0, verbose_name="归一化趋势评分", blank=True, null=True)

    # 多对多关系，不会添加该字段，会增加一张存储对应关系的中间表wallpaper_wall_subjects，里面只有三个字段 id、wall_id、subject_id
    subjects = models.ManyToManyField(Subject, related_name="walls", verbose_name="专题", blank=True)

    def calc_trends_score(self, save=False):
        # 计算趋势评分，通过加权计算得出。
        # 分子：浏览量、点赞数、收藏数、下载量、评论数、分享数的加权和，
        # 分母：时间衰减因子。根据时间衰减，用于调整旧数据的影响
        w1 = 1  # 浏览量权重
        w2 = 3  # 点赞数权重
        w3 = 4  # 收藏数权重
        w4 = 5  # 下载量权重
        w5 = 2  # 评论数权重，无论好坏评论，都增加热度
        w6 = 5  # 分享数权重

        age_in_hours = (timezone.now() - self.updated_at).total_seconds() / 3600
        time_decay = (age_in_hours + 2) ** 1.5

        # 计算趋势评分
        base_score = self.score if self.score is not None else 2.5
        trends_score = (
            (self.views or 0) * w1
            + (self.likes or 0) * w2
            + (self.favorites or 0) * w3
            + (self.downloads or 0) * w4
            + (self.comments or 0) * w5
            + (self.shares or 0) * w6
            + (base_score - 2.5)  # 图片分数，2.5分以上为正数，2.5分以下为负数负评分
        ) / time_decay

        # 保存趋势评分
        self.trends = trends_score
        # 归一化趋势评分，范围(0, 1]
        self.normalized_trends = trends_score / max(trends_score, 1)
        if save:
            self.save(update_fields=["trends", "normalized_trends"])

        return self.trends, self.normalized_trends

    def __str__(self):
        return f"壁纸 - {self.description if self.description else self.pk}"

    class Meta:
        verbose_name = "壁纸"
        verbose_name_plural = "壁纸信息"
        db_table_comment = "壁纸信息，存储壁纸的基本信息"
        indexes = [
            models.Index(fields=["is_active", "-updated_at"]),
            # 联合索引：先按分类排序，再按更新时间倒序
            models.Index(fields=["is_active", "classify", "-updated_at"]),
            # 自定义索引名
            # models.Index(fields=['title', 'author'], name='idx_title_author'),
        ]


class WallFeatures(models.Model):
    wall = models.OneToOneField(Wall, on_delete=models.CASCADE, related_name="wall_features", primary_key=True)
    # 二进制存储特征向量,比TEXT存储JSON节省50%空间
    feature_vector = models.BinaryField(verbose_name="壁纸特征向量", blank=True, null=True)
    # 特征维度，用于记录特征向量的维度，用于判断是否需要降维
    feature_dim = models.IntegerField(verbose_name="壁纸特征维度", blank=True, null=True)
    # 模型名称，用于记录使用的是哪个模型提取的特征
    model_name = models.CharField(max_length=100, verbose_name="模型名称", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "壁纸特征向量"
        verbose_name_plural = "壁纸特征向量"
        db_table = "wallpaper_wall_features"  # 自定义表名最好带上应用名。没指定db_table，默认是应用名_模型名
        db_table_comment = "壁纸特征向量，存储图片的特征向量用于相似度计算"


class WallSimilarities(models.Model):
    source_wall_id = models.IntegerField(verbose_name="源壁纸ID")
    target_wall_id = models.IntegerField(verbose_name="目标壁纸ID")
    similarity = models.FloatField(verbose_name="相似度", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "壁纸相似度"
        verbose_name_plural = "壁纸相似度"
        db_table = "wallpaper_wall_similarities"
        db_table_comment = "壁纸相似度，用于存储壁纸之间的相似度关系"
        constraints = [
            # 唯一约束：确保 source_wall_id + target_wall_id 组合唯一
            models.UniqueConstraint(fields=["source_wall_id", "target_wall_id"], name="unique_source_target")
        ]
        indexes = [
            # 联合索引：先按源壁纸 ID 排序，再按相似度倒序排序。自定义索引名
            models.Index(fields=["source_wall_id", "-similarity"], name="idx_source_wall_id_similarity"),
        ]


class Notice(models.Model):
    title = models.CharField(max_length=200, verbose_name="公告标题")
    title_en = models.CharField(max_length=200, verbose_name="公告标题-英文", blank=True, null=True)
    content = models.TextField(verbose_name="公告详情")
    content_en = models.TextField(verbose_name="公告详情-英文", blank=True, null=True)
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
    sort = models.FloatField(verbose_name="排序字段", blank=True, null=True)
    picurl = models.CharField(max_length=255, verbose_name="缩略图")
    target = models.CharField(max_length=60, verbose_name="跳转方式，默认：self，外站：miniProgram")
    appid = models.CharField(max_length=100, verbose_name="外部小程序的app-id", blank=True, null=True)
    enable = models.BooleanField(default=True, verbose_name="是否启用")  # is_active
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    # def __str__(self):
    #     return f"{self.url}"

    class Meta:
        verbose_name = "首页横幅"
        verbose_name_plural = verbose_name


class Profile(models.Model):
    GENDER_CHOICES = (
        (0, '保密'),
        (1, '男'),
        (2, '女'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", primary_key=True)
    nickname = models.CharField(max_length=60, verbose_name="用户昵称", blank=True, null=True)
    gender = models.IntegerField(choices=GENDER_CHOICES, default=0, verbose_name="性别")
    birthday = models.DateField(blank=True, null=True, verbose_name="生日")
    description = models.CharField(max_length=255, verbose_name="个人简介", blank=True, null=True)
    avatar = models.CharField(max_length=150, verbose_name="头像", blank=True, null=True)
    phone_number = models.CharField(max_length=20, verbose_name="电话号码", blank=True, null=True)
    is_vip = models.BooleanField(default=False, verbose_name="是否vip")
    energy = models.IntegerField(default=0, verbose_name="用户能量值")
    channel = models.CharField(max_length=60, verbose_name="渠道", blank=True, null=True)
    source = models.CharField(max_length=60, verbose_name="来源", blank=True, null=True)
    ip = models.CharField(max_length=60, verbose_name="ip地址", blank=True, null=True)
    region = models.CharField(max_length=60, verbose_name="行政区省市县", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    wechat_openid = models.CharField(max_length=100, verbose_name="微信openid", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} 的个人资料"

    class Meta:
        verbose_name = "个人信息"
        verbose_name_plural = "用户个人信息"


# # 自动创建Profile对象
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)


# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     if hasattr(instance, "profile"):
#         instance.profile.save()


class UserActions(models.Model):
    """用户操作日志表，主要用于记录用户的操作行为"""

    # 用户操作：浏览、点赞、收藏、下载、分享、评论、评分
    ACTION_TYPES = [
        ("view", "浏览"),  # 1为浏览1次，可以多次浏览
        ("like", "点赞"),  # 1为like，0为dislike，可以多次操作
        ("favorite", "收藏"),  # 1为收藏，0为取消收藏，可以多次操作
        ("download", "下载"),  # 1为下载1次，可以多次下载
        ("share", "分享"),  # 1为分享1次，可以多次分享
        ("comment", "评论"),  # 1为评论1次，可以多次评论
        ("rate", "评分"),  # 0～5，0为取消评分。可以多次操作，覆盖之前的值
    ]
    device_id = models.CharField(max_length=100, verbose_name="设备id", blank=True, null=True)
    channel = models.CharField(max_length=60, verbose_name="渠道", blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name="用户id", blank=True, null=True)
    wall = models.ForeignKey(Wall, on_delete=models.DO_NOTHING, verbose_name="壁纸id", blank=True, null=True)
    action_key = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name="操作类型")
    action_value = models.FloatField(default=0, verbose_name="操作值", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.user} - {self.action_key} - {self.action_value} - {self.created_at}"

    class Meta:
        verbose_name = "用户操作日志"
        verbose_name_plural = "用户操作日志_plural"
        db_table = "wallpaper_user_actions"
        db_table_comment = "用户操作日志表"
        constraints = [
            # 注意：一个设备可以有多个用户操作，一个用户也可以在多个设备上操作
            models.UniqueConstraint(
                fields=["device_id", "user", "wall", "action_key"],
                condition=models.Q(device_id__isnull=False, wall__isnull=False, action_key__isnull=False),
                name="unique_device_user_action",
            ),
        ]
        indexes = [
            models.Index(fields=["device_id", "action_key", "-updated_at"]),
            models.Index(fields=["user", "action_key", "-updated_at"]),
        ]


# class UserBehaviors(models.Model):
#     # TODO: 用户行为，待优化，埋点数据，需要统计分析和推荐算法
#     user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, verbose_name="用户id")
#     # -- 上下文信息 --
#     referer = models.CharField(max_length=500, verbose_name="来源页面")
#     updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

#     class Meta:
#         verbose_name = "用户行为"
#         verbose_name_plural = "用户行为"
#         db_table = "wallpaper_user_behaviors"


# class UserPortraits(models.Model):
#     # user_labels: 用户标签

#     user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户id")
#     # 用户向量
#     feature_vector = models.BLOBField(verbose_name="用户特征向量")
#     feature_dim = models.SmallIntegerField(default=512, verbose_name="壁纸特征维度")
#     # 用户画像
#     interest_classify = models.JSONField(verbose_name="用户兴趣分类")  # 前端用户选择设置订阅喜欢的分类
#     interest_tags = models.JSONField(verbose_name="用户兴趣标签")  # 前端用户选择设置订阅喜欢的标签
#     portrait = models.JSONField(verbose_name="用户画像")
#     updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

#     class Meta:
#         verbose_name = "用户画像"
#         verbose_name_plural = "用户画像"
#         db_table = "wallpaper_user_portraits"
#         db_table_comment = "用户画像表"


# class Events(models.Model):
#     """用户事件表"""
#     pass


class Recommendations(models.Model):
    """用户推荐表"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, verbose_name="用户id")
    device_id = models.CharField(max_length=100, verbose_name="设备id", blank=True, null=True)
    wall_id = models.IntegerField(verbose_name="壁纸id")
    score = models.FloatField(verbose_name="推荐分数")
    reason = models.CharField(
        max_length=60, verbose_name="推荐原因", blank=True, null=True
    )  # 表示推荐的原因，如：相似度、热门等
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "用户推荐"
        verbose_name_plural = verbose_name
        db_table = "wallpaper_recommendations"
        db_table_comment = "存储预计算的推荐结果"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "wall_id"], condition=models.Q(user__isnull=False), name="unique_user_recommendation"
            ),
            models.UniqueConstraint(
                fields=["device_id", "wall_id"],
                condition=models.Q(device_id__isnull=False),
                name="unique_device_recommendation",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-score"]),
            models.Index(fields=["device_id", "-score"]),
        ]


class PageView(models.Model):
    url = models.CharField(max_length=255, verbose_name="url地址")
    pv = models.IntegerField(default=0, verbose_name="页面访问量")

    class Meta:
        verbose_name = "页面访问量"
        verbose_name_plural = "页面访问量统计"


class Access(models.Model):
    ip = models.CharField(max_length=100, verbose_name="ip地址")  #  models.GenericIPAddressField
    address = models.CharField(max_length=255, verbose_name="访问地址", blank=True, null=True)
    username = models.CharField(max_length=100, verbose_name="用户名", blank=True, null=True)

    # client = models.CharField(max_length=100, verbose_name="", blank=True, null=True)  # 客户端类型，如：web、android、ios、wechat、douyin、qq等
    # provider = models.CharField(max_length=100, verbose_name="", blank=True, null=True)

    # 如：app(android\ios)、web、mp-weixin、mp-douyin等，对应uniapp的多端 uniPlatform 或 platform
    platform = models.CharField(max_length=100, verbose_name="平台", blank=True, null=True)
    # 如：google、小米、oppo、vivo、apple等应用商店
    channel = models.CharField(max_length=100, verbose_name="渠道", blank=True, null=True)
    app_version = models.CharField(max_length=100, verbose_name="app版本号", blank=True, null=True)
    device_id = models.CharField(max_length=100, verbose_name="设备id", blank=True, null=True)
    device_brand = models.CharField(max_length=100, verbose_name="设备品牌", blank=True, null=True)
    device_model = models.CharField(max_length=100, verbose_name="设备型号", blank=True, null=True)
    language = models.CharField(max_length=16, verbose_name="语言", blank=True, null=True)  # 语言，如：zh-CN、en-US等

    access_time = models.DateTimeField(auto_now_add=True, verbose_name="访问时间", db_index=True)
    remark = models.JSONField(default=dict, verbose_name="备注", blank=True, null=True)  # desciption

    def __str__(self):
        # 将access_time转换为本地时区的时间字符串，也就是settings.py中设置的TIME_ZONE对应的时区
        local_tz = timezone.get_default_timezone()
        # 使用strftime来格式化日期时间，截取前19个字符
        formatted_time = self.access_time.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S")
        return f"{formatted_time} - {self.platform} - {self.ip}"

    class Meta:
        verbose_name = "访问日志详情"
        verbose_name_plural = "访问日志_plural"


class Feedback(models.Model):
    type = models.CharField(max_length=60, verbose_name="反馈类型")  # 如：bug反馈、功能建议、内容投诉、其他等
    content = models.CharField(max_length=255, verbose_name="反馈内容")
    contact = models.CharField(max_length=100, verbose_name="联系方式", blank=True, null=True)  # 联系方式，如邮箱、手机号等
    images = models.JSONField(max_length=255, verbose_name="图片地址", blank=True, null=True)  # 多张图片地址列表
    is_deal = models.BooleanField(default=False, verbose_name="处理状态")  # 处理状态, 默认未处理
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "反馈信息"
        verbose_name_plural = "反馈信息"


class Versions(models.Model):
    channel = models.CharField(max_length=100, verbose_name="渠道")
    platform = models.CharField(max_length=100, verbose_name="平台")
    app_store_url = models.CharField(max_length=255, verbose_name="应用商店地址")
    app_version = models.CharField(max_length=100, verbose_name="app版本号")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "版本信息"
        verbose_name_plural = "版本信息"


class EnergyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    action_type = models.CharField(max_length=60, verbose_name="操作类型")
    energy_change = models.IntegerField(verbose_name="能量变化")
    wall_id = models.IntegerField(verbose_name="壁纸id", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.energy_change}"

    class Meta:
        verbose_name = "能量流水记录"
        verbose_name_plural = "能量流水记录_plural"
        db_table = "wallpaper_energy_log"
        indexes = [
            models.Index(fields=["user", "action_type", "-created_at"]),
        ]
