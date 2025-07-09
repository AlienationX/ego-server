from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe


# Register your models here.
from .models import Classify, Subject, Wall, Notice, Rate, Profile, Banner, Access, Application

ROOT_PIC_URL = "https://wallpaper-kpze6c.s3.eu-north-1.amazonaws.com/"
# ROOT_PIC_URL = "https://mp-36059119-7390-44c6-8190-cc3527d1e745.cdn.bspapp.com/wallpaper"

class ClassifyAdmin(admin.ModelAdmin):
    # 控制字段显示顺序，及分块显示
    # fieldsets = [
    #     (None,               {'fields': ['question_text']}),
    #     ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    # ]
    list_display = ('id', 'name', 'sort', 'select', 'enable', 'created_at', 'updated_at')  # 显示的字段
    list_filter = ['enable']

    # 在编辑页也显示图片预览, fields是编辑页面展示的字段
    fields = tuple(list(list_display)[1:2] + ['picurl', 'image_preview'] + list(list_display)[2:])
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        # return self.display_image(obj)
        if obj.picurl:
            return format_html(
                '<img src="{}" style="height: 360px; width: auto; border-radius: 4px;" />',
                ROOT_PIC_URL + obj.picurl
            )
        return "-"

    image_preview.short_description = "当前图片"


class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'content', 'sort', 'select', 'enable', 'created_at', 'updated_at')  # 显示的字段
    list_filter = ('select', 'enable')
    search_fields = ('name', 'content')  # 添加搜索功能


class WallAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_image', 'classify', 'display_subjects', 'publisher', 'tabs', 'score', 'description')
    list_filter = ('classify',)
    search_fields = ('description', 'publisher', 'tabs')
    filter_horizontal = ('subjects',)  # 优化多对多字段选择界面
    date_hierarchy = 'created_at'   # 按创建日期分层筛选

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
            return format_html(
                '<img src="{}" style="max-height: 60px; max-width: 60px;" />',
                ROOT_PIC_URL + obj.picurl
            )
        return "-"
    display_image.short_description = "图片预览"  # 设置列标题

    # 在编辑页也显示图片预览, fields是编辑页面的字段
    readonly_fields = ('image_preview',)
    # fields = ('picurl', 'image_preview', 'classify')

    def image_preview(self, obj):
        # return self.display_image(obj)
        if obj.picurl:
            return format_html(
                '<img src="{}" style="height: 640px; width: auto; border-radius: 4px;" />',
                ROOT_PIC_URL + obj.picurl
            )
        return "-"
    image_preview.short_description = "当前图片"


class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'target', 'enable')


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'select', 'article_status', 'view_count', 'publish_date')

    fields = ('title', 'content', 'html_preview', 'author', 'select', 'article_status', 'publish_date', 'view_count')

    readonly_fields = ('html_preview',)
    # 编辑页完整预览（带安全限制）

    def html_preview(self, obj):
        return format_html(
            '<div class="html-preview" style="border: 1px solid #ddd; padding: 10px; margin-top: 10px">{}</div>',
            mark_safe(obj.content)
        )

    html_preview.short_description = "HTML预览"


admin.site.register(Classify, ClassifyAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Wall, WallAdmin)
# admin.site.register(Notice, NoticeAdmin)
admin.site.register(Banner, BannerAdmin)
admin.site.register(Rate)
admin.site.register(Access)
admin.site.register(Profile)
admin.site.register(Application)
