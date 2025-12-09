import hashlib

from asgiref.sync import sync_to_async

from survey.models import Respondent
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
