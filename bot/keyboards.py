from telegram import ReplyKeyboardMarkup


def get_main_menu_keyboard():
    """Главное меню бота"""
    keyboard = [
        ['📝 Начать опрос'],
        ['ℹ️ Информация', '📊 Мои опросы'],
        ['👤 Мой профиль']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_survey_management_keyboard():
    """Меню управления сессиями"""
    keyboard = [
        ['▶ Возобновить опрос'],
        ['❌ Сбросить сессию'],
        ['⏪️ В главное меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_survey_drop_keyboard():
    keyboard = [
        ['❌ Удалить все'],
        ['⏪️ Назад']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_gender_keyboard():
    """Клавиатура для выбора пола"""
    keyboard = [
        ['👨 Мужской', '👩 Женский']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_occupation_keyboard():
    """Клавиатура для выбора статуса (студент/работник)"""
    keyboard = [
        ['🎓 Учусь в вузе'],
        ['💼 Работаю по специальности']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_course_keyboard():
    """Клавиатура для выбора курса"""
    keyboard = [
        ['1', '2', '3'],
        ['4', '5', '6']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_skip_keyboard():
    """Клавиатура с кнопкой пропустить"""
    keyboard = [['⏭ Пропустить']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_choice_keyboard(options):
    """Клавиатура для вопросов с выбором вариантов"""
    keyboard = [[option.text] for option in options]
    keyboard.append(['⏭ Пропустить'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
