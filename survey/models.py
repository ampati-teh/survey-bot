from asgiref.sync import sync_to_async
from django.db import models


class Respondent(models.Model):
    """Анонимный респондент"""

    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
    ]

    OCCUPATION_CHOICES = [
        ('student', 'Учится в вузе'),
        ('working', 'Работает по специальности'),
    ]

    # Анонимный идентификатор (генерируется из telegram_id с помощью хеширования)
    anonymous_id = models.CharField(max_length=64, unique=True, verbose_name='Анонимный ID')

    # Данные респондента
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True, verbose_name='Пол')
    age = models.PositiveIntegerField(blank=True, null=True, verbose_name='Возраст')
    occupation_type = models.CharField(max_length=20, choices=OCCUPATION_CHOICES, blank=True, null=True,
                                      verbose_name='Статус')
    university_course = models.PositiveIntegerField(blank=True, null=True,
                                                    verbose_name='Курс обучения')
    work_experience_years = models.PositiveIntegerField(blank=True, null=True,
                                                        verbose_name='Стаж работы (лет)')

    # Служебные поля
    is_profile_complete = models.BooleanField(default=False, verbose_name='Профиль заполнен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')

    class Meta:
        verbose_name = 'Респондент'
        verbose_name_plural = 'Респонденты'

    def __str__(self):
        return f"Респондент {self.anonymous_id[:8]}..."

    def get_occupation_display_full(self):
        """Полное описание статуса респондента"""
        if self.occupation_type == 'student' and self.university_course:
            return f"Студент {self.university_course} курса"
        elif self.occupation_type == 'working' and self.work_experience_years is not None:
            return f"Работает (стаж {self.work_experience_years} лет)"
        return self.get_occupation_type_display() if self.occupation_type else "Не указано"


class Survey(models.Model):
    """Опрос"""
    title = models.CharField(max_length=255, verbose_name='Название опроса')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Опрос'
        verbose_name_plural = 'Опросы'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Question(models.Model):
    """Вопрос опроса"""

    QUESTION_TYPES = [
        ('text', 'Текстовый ответ'),
        ('choice', 'Выбор варианта'),
        ('voice', 'Голосовое сообщение'),
    ]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions', verbose_name='Опрос')
    text = models.TextField(verbose_name='Текст вопроса')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, verbose_name='Тип вопроса')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_required = models.BooleanField(default=True, verbose_name='Обязательный')

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['survey', 'order']

    def __str__(self):
        return f"{self.survey.title} - {self.text[:50]}"


class QuestionOption(models.Model):
    """Вариант ответа для вопроса с выбором"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options', verbose_name='Вопрос')
    text = models.CharField(max_length=255, verbose_name='Текст варианта')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'
        ordering = ['question', 'order']

    def __str__(self):
        return f"{self.question.text[:30]} - {self.text}"


class SurveySession(models.Model):
    """Сессия прохождения опроса"""

    STATUS_CHOICES = [
        ('started', 'Начат'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершен'),
        ('abandoned', 'Прерван'),
    ]

    user = models.ForeignKey(Respondent, on_delete=models.CASCADE, related_name='sessions', verbose_name='Респондент')
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='sessions', verbose_name='Опрос')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started', verbose_name='Статус')
    current_question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='current_sessions', verbose_name='Текущий вопрос')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Время начала')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Время завершения')

    class Meta:
        verbose_name = 'Сессия опроса'
        verbose_name_plural = 'Сессии опросов'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user} - {self.survey.title} ({self.status})"

    @sync_to_async
    def get_current_question(self):
        return self.current_question


class Response(models.Model):
    """Ответ на вопрос"""
    session = models.ForeignKey(SurveySession, on_delete=models.CASCADE, related_name='responses', verbose_name='Сессия')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses', verbose_name='Вопрос')
    text_answer = models.TextField(blank=True, null=True, verbose_name='Текстовый ответ')
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='responses', verbose_name='Выбранный вариант')
    voice_file = models.FileField(upload_to='voice_responses/%Y/%m/%d/', blank=True, null=True,
                                  verbose_name='Голосовой файл')
    telegram_file_id = models.CharField(max_length=255, blank=True, null=True,
                                       verbose_name='Telegram File ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время ответа')

    class Meta:
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'
        ordering = ['session', 'created_at']

    def __str__(self):
        return f"{self.session.user} - {self.question.text[:30]}"
