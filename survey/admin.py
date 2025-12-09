from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Respondent, Survey, Question, QuestionOption, SurveySession, Response


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 1
    fields = ['text', 'order']


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    fields = ['text', 'question_type', 'order', 'is_required']


@admin.register(Respondent)
class RespondentAdmin(admin.ModelAdmin):
    list_display = ['get_anonymous_id_short', 'gender', 'age', 'occupation_type',
                    'is_profile_complete', 'created_at']
    list_filter = ['gender', 'occupation_type', 'is_profile_complete', 'created_at']
    search_fields = ['anonymous_id']
    readonly_fields = ['anonymous_id', 'created_at']
    fieldsets = [
        ('Анонимная идентификация', {
            'fields': ['anonymous_id'],
            'description': 'Анонимный ID создан на основе Telegram ID с использованием криптографического хеширования. '
                          'Невозможно восстановить исходный Telegram ID из этого значения.'
        }),
        ('Информация о респонденте (анонимная)', {
            'fields': ['gender', 'age', 'occupation_type', 'university_course', 'work_experience_years']
        }),
        ('Служебное', {
            'fields': ['is_profile_complete', 'created_at']
        }),
    ]

    def get_anonymous_id_short(self, obj):
        """Показать первые 8 символов анонимного ID"""
        return f"{obj.anonymous_id[:8]}..."
    get_anonymous_id_short.short_description = 'Анонимный ID'

    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'created_at', 'editor_link']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    inlines = [QuestionInline]

    def editor_link(self, obj):
        """Ссылка на визуальный редактор опроса"""
        url = reverse('survey_editor', args=[obj.id])
        return format_html('<a href="{}" class="button">✏️ Визуальный редактор</a>', url)
    editor_link.short_description = 'Редактор'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'survey', 'question_type', 'order', 'is_required']
    list_filter = ['survey', 'question_type', 'is_required']
    search_fields = ['text']
    inlines = [QuestionOptionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('survey')


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'question', 'order']
    list_filter = ['question__survey']
    search_fields = ['text']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('question', 'question__survey')


@admin.register(SurveySession)
class SurveySessionAdmin(admin.ModelAdmin):
    list_display = ['get_user_short', 'survey', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'survey', 'started_at']
    search_fields = ['user__anonymous_id']
    readonly_fields = ['started_at', 'completed_at']

    def get_user_short(self, obj):
        """Показать первые 8 символов анонимного ID респондента"""
        return f"Респондент {obj.user.anonymous_id[:8]}..."
    get_user_short.short_description = 'Респондент'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'survey')


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ['get_session_info', 'question', 'get_answer_preview', 'created_at']
    list_filter = ['question__question_type', 'created_at']
    search_fields = ['text_answer', 'session__user__anonymous_id']
    readonly_fields = ['created_at']

    def get_session_info(self, obj):
        """Информация о сессии"""
        return f"Респондент {obj.session.user.anonymous_id[:8]}... - {obj.session.survey.title}"
    get_session_info.short_description = 'Сессия'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'session', 'session__user', 'session__survey', 'question', 'selected_option'
        )

    def get_answer_preview(self, obj):
        if obj.text_answer:
            return obj.text_answer[:50]
        elif obj.selected_option:
            return obj.selected_option.text
        elif obj.voice_file:
            return f"Голосовой файл: {obj.voice_file.name}"
        return "-"
    get_answer_preview.short_description = 'Ответ'
