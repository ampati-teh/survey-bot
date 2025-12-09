from enum import IntEnum


class ConversationState(IntEnum):
    """Состояния диалога с ботом"""
    # Регистрация
    REGISTRATION_GENDER = 0
    REGISTRATION_AGE = 1
    REGISTRATION_OCCUPATION = 2
    REGISTRATION_COURSE = 3
    REGISTRATION_EXPERIENCE = 4

    # Основное меню и опросы
    MAIN_MENU = 10
    ANSWERING_QUESTION = 11
    WAITING_TEXT_ANSWER = 12
    WAITING_CHOICE_ANSWER = 13
    WAITING_VOICE_ANSWER = 14
