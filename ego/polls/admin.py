from django.contrib import admin

# Register your models here.
from .models import Question, Choice


class ChoiceInline(admin.TabularInline):
    # StackedInline, TabularInline
    model = Choice
    extra = 2  # 默认提供的明细框个数


class QuestionAdmin(admin.ModelAdmin):
    # 控制字段显示顺序，及分块显示
    fieldsets = [
        (None,               {'fields': ['question_text']}),
        ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    ]
    inlines = [ChoiceInline]  # 编辑问题时，同时必须编辑选项模型，这样其实就不需要再注册Choice模型
    list_display = ('question_text', 'pub_date', 'was_published_recently')  # 显示的字段
    list_filter = ['pub_date']
    search_fields = ['question_text']


admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
