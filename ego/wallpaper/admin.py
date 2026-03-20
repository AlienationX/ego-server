import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

# Register your models here.
from .models import (
    Access,
    Actions,
    Application,
    Banner,
    Classify,
    Notice,
    Profile,
    Subject,
    Wall,
)

# ROOT_PIC_URL = "https://mp-36059119-7390-44c6-8190-cc3527d1e745.cdn.bspapp.com/wallpaper"
# ROOT_PIC_URL = "https://wallpaper-kpze6c.s3.eu-north-1.amazonaws.com"
# ROOT_PIC_URL = "https://wp-1328701250.cos.ap-beijing.myqcloud.com"
ROOT_PIC_URL = "https://api.wp.ego8.space/static/wallpaper/media"


class ClassifyAdmin(admin.ModelAdmin):
    # 控制字段显示顺序，及分块显示
    # fieldsets = [
    #     (None,               {'fields': ['question_text']}),
    #     ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    # ]
    list_display = ("id", "name", "name_en", "sort", "select", "enable", "is_locked", "pic_path_prefix")  # 显示的字段
    list_filter = ("enable",)

    # 在编辑页也显示图片预览, fields是编辑页面展示的字段
    fields = tuple(
        list(list_display)[1:2] + ["picurl", "image_preview"] + list(list_display)[2:] + ["created_at", "updated_at"]
    )
    readonly_fields = ("image_preview", "created_at", "updated_at")

    def image_preview(self, obj):
        # return self.display_image(obj)
        if obj.picurl:
            return format_html(
                '<img src="{}" style="height: 360px; width: auto; border-radius: 4px;" />', ROOT_PIC_URL + "/" + obj.picurl
            )
        return "-"

    image_preview.short_description = "当前图片"


class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "content",
        "sort",
        "select",
        "is_active",
        "is_locked",
        "created_at",
        "updated_at",
    )  # 显示的字段
    list_filter = ("select", "is_active")
    search_fields = ("name", "content")  # 添加搜索功能


class WallAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_image",
        "classify",
        "display_subjects",
        "is_locked",
        "publisher",
        "tabs",
        "score",
        "description",
    )
    list_filter = ("classify",)
    search_fields = ("description", "publisher", "tabs")
    filter_horizontal = ("subjects",)  # 优化多对多字段选择界面
    date_hierarchy = "created_at"  # 按创建日期分层筛选

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # 优化多对多字段的查询性能
        if db_field.name == "subjects":
            kwargs["queryset"] = Subject.objects.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def display_subjects(self, obj):
        """将多对多字段转换为逗号分隔的字符串"""
        return ", ".join([subject.name for subject in obj.subjects.all()])  # 假设多对多字段名为'subjects'

    display_subjects.short_description = "专题"  # 设置表头名称

    # 定义图片展示方法
    def display_image(self, obj):
        if obj.picurl:
            return format_html('<img src="{}" style="max-height: 60px; max-width: 60px;" />', ROOT_PIC_URL + "/" + obj.picurl)
        return "-"

    display_image.short_description = "图片预览"  # 设置列标题

    # 在编辑页也显示图片预览, fields是编辑页面的字段
    readonly_fields = ("image_preview",)
    # fields = ('picurl', 'image_preview', 'classify')

    def image_preview(self, obj):
        # return self.display_image(obj)
        if obj.picurl:
            return format_html(
                '<img src="{}" style="height: 640px; width: auto; border-radius: 4px;" />', ROOT_PIC_URL + "/" + obj.picurl
            )
        return "-"

    image_preview.short_description = "当前图片"


class BannerAdmin(admin.ModelAdmin):
    list_display = ("id", "url", "target", "enable")


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "select", "article_status", "view_count", "publish_date")
    fields = ("title", "content", "html_preview", "author", "select", "article_status", "publish_date", "view_count")
    readonly_fields = ("html_preview",)
    # 编辑页完整预览（带安全限制）

    def html_preview(self, obj):
        return format_html(
            '<div class="html-preview" style="border: 1px solid #ddd; padding: 10px; margin-top: 10px">{}</div>',
            mark_safe(obj.content),
        )

    html_preview.short_description = "HTML预览"


@admin.register(Access)
class AccessAdmin(admin.ModelAdmin):
    list_display = ("ip", "address", "platform", "channel", "app_version", "access_time")
    fields = (
        "ip",
        "address",
        "username",
        "source",
        "platform",
        "channel",
        "app_version",
        "access_time",
        "remark_json",
    )  # 可以控制顺序
    readonly_fields = ("access_time", "remark_json")

    def remark_json(self, obj):
        data_str = obj.remark
        try:
            # data_str是json字符串，但是没有格式，需要转成dict再转成有格式的字符串进行展示
            data = json.loads(data_str)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            return mark_safe(f'<pre style="white-space: pre-wrap">{formatted}</pre>')
        except TypeError:
            return "Invalid JSON: " + obj.remark

    remark_json.short_description = "备注JSON"  # 表头显示名
    # remark_json.allow_tags = True


admin.site.register(Classify, ClassifyAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Wall, WallAdmin)
admin.site.register(Banner, BannerAdmin)
# admin.site.register(Notice, NoticeAdmin)
# admin.site.register(Access, AccessAdmin)
admin.site.register(Actions)
admin.site.register(Profile)
admin.site.register(Application)
