from datetime import datetime
import hashlib

from asgiref.sync import sync_to_async

from survey.models import Respondent, Survey, SurveySession, Response

from django.conf import settings


# Anonymization function
def generate_anonymous_id(telegram_id: int) -> str:
    """
    Генерирует анонимный ID из telegram_id с использованием криптографического хеширования.

    Используется SHA-256 с секретной солью, что делает невозможным:
    - Восстановление telegram_id из anonymous_id
    - Создание радужных таблиц для подбора

    Args:
        telegram_id: Telegram ID пользователя

    Returns:
        Анонимный ID (64 символа hex)
    """
    salt = settings.ANONYMOUS_SALT
    if not salt:
        raise ValueError("ANONYMOUS_SALT не установлен в settings!")

    # Создаем строку из соли и telegram_id
    data = f"{salt}:{telegram_id}".encode('utf-8')

    # Генерируем SHA-256 хеш
    anonymous_id = hashlib.sha256(data).hexdigest()

    return anonymous_id

@sync_to_async
def get_or_create_respondent(anonymous_id):
    """Получить или создать анонимного респондента"""
    return Respondent.objects.get_or_create(
        anonymous_id=anonymous_id,
        defaults={}
    )


@sync_to_async
def update_respondent(anonymous_id, **fields):
    """Обновить данные респондента"""
    respondent = Respondent.objects.get(anonymous_id=anonymous_id)
    for field, value in fields.items():
        setattr(respondent, field, value)
    respondent.save()
    return respondent


@sync_to_async
def get_respondent(anonymous_id):
    """Получить респондента"""
    return Respondent.objects.get(anonymous_id=anonymous_id)

@sync_to_async
def get_active_survey():
    """Получить активный опрос"""
    return Survey.objects.filter(is_active=True).first()


@sync_to_async
def create_survey_session(user, survey):
    """Создать сессию опроса"""
    return SurveySession.objects.create(
        user=user,
        survey=survey,
        status='in_progress'
    )

@sync_to_async
def get_first_question(survey):
    """Получить первый вопрос опроса"""
    return survey.questions.order_by('order').first()


@sync_to_async
def update_session_question(session, question):
    """Обновить текущий вопрос в сессии"""
    session.current_question = question
    session.save()


@sync_to_async
def abandon_session(session):
    """Отменить сессию"""
    session.status = 'abandoned'
    session.save()


@sync_to_async
def get_session(session_id):
    """Получить сессию по ID"""
    return SurveySession.objects.get(id=session_id)

@sync_to_async
def get_question_options(question):
    """Получить варианты ответов на вопрос"""
    return list(question.options.order_by('order'))


@sync_to_async
def find_option_by_text(question, text):
    """Найти вариант ответа по тексту"""
    return question.options.filter(text=text).first()


@sync_to_async
def create_response(session, question, **fields):
    """Создать ответ на вопрос"""
    return Response.objects.create(
        session=session,
        question=question,
        **fields
    )


@sync_to_async
def get_next_question(survey, current_order):
    """Получить следующий вопрос"""
    return survey.questions.filter(order__gt=current_order).order_by('order').first()

@sync_to_async
def complete_session(session):
    """Завершить сессию"""
    session.status = 'completed'
    session.completed_at = datetime.now()
    session.save()


@sync_to_async
def count_completed_sessions(user):
    """Подсчитать завершенные сессии пользователя"""
    return SurveySession.objects.filter(user=user, status='completed').count()


@sync_to_async
def count_in_progress_sessions(user):
    """Подсчитать активные сессии пользователя"""
    return SurveySession.objects.filter(user=user, status='in_progress').count()
