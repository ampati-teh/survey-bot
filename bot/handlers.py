import hashlib

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
