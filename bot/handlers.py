from datetime import datetime
import hashlib

from asgiref.sync import sync_to_async
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from bot.keyboards import get_main_menu_keyboard, get_gender_keyboard, get_occupation_keyboard, get_course_keyboard
from bot.states import ConversationState
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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user

    # Генерируем анонимный ID из telegram_id
    anonymous_id = generate_anonymous_id(user.id)

    # Сохраняем anonymous_id в контексте для использования в других обработчиках
    context.user_data['anonymous_id'] = anonymous_id

    # Создаем или получаем респондента
    respondent, created = await get_or_create_respondent(anonymous_id)

    # Если профиль не заполнен, запускаем процесс регистрации
    if not respondent.is_profile_complete:
        welcome_message = (
            "Здравствуйте! 👋\n\n"
            "Добро пожаловать в бот для опросов.\n\n"
            "📊 Ваши данные полностью анонимны и защищены.\n\n"
            "Для начала работы, пожалуйста, заполните небольшую анкету о себе."
        )
        await update.message.reply_text(welcome_message)

        # Начинаем процесс регистрации
        return await ask_gender(update, context)
    else:
        # Профиль уже заполнен
        welcome_message = (
            "С возвращением! 👋\n\n"
            "Рады видеть вас снова! Используйте меню ниже для навигации."
        )
        await update.message.reply_text(
            welcome_message,
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationState.MAIN_MENU


async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос пола респондента"""
    await update.message.reply_text(
        "Укажите ваш пол:",
        reply_markup=get_gender_keyboard()
    )
    return ConversationState.REGISTRATION_GENDER


async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора пола"""
    anonymous_id = context.user_data.get('anonymous_id')

    text = update.message.text
    if '👨 Мужской' in text:
        await update_respondent(anonymous_id, gender='male')
    elif '👩 Женский' in text:
        await update_respondent(anonymous_id, gender='female')
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите пол, используя кнопки ниже:",
            reply_markup=get_gender_keyboard()
        )
        return ConversationState.REGISTRATION_GENDER

    await update.message.reply_text(
        "Укажите ваш возраст (полных лет):",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationState.REGISTRATION_AGE


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода возраста"""
    anonymous_id = context.user_data.get('anonymous_id')

    try:
        age = int(update.message.text)
        if age < 16 or age > 100:
            await update.message.reply_text(
                "Пожалуйста, укажите корректный возраст (от 16 до 100 лет):"
            )
            return ConversationState.REGISTRATION_AGE

        await update_respondent(anonymous_id, age=age)

        await update.message.reply_text(
            "Выберите ваш текущий статус:",
            reply_markup=get_occupation_keyboard()
        )
        return ConversationState.REGISTRATION_OCCUPATION

    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите возраст числом (например, 25):"
        )
        return ConversationState.REGISTRATION_AGE


async def handle_occupation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора статуса (студент/работник)"""
    anonymous_id = context.user_data.get('anonymous_id')

    text = update.message.text
    if '🎓' in text or 'Учусь' in text:
        await update_respondent(anonymous_id, occupation_type='student')

        await update.message.reply_text(
            "На каком курсе вы обучаетесь?",
            reply_markup=get_course_keyboard()
        )
        return ConversationState.REGISTRATION_COURSE

    elif '💼' in text or 'Работаю' in text:
        await update_respondent(anonymous_id, occupation_type='working')

        await update.message.reply_text(
            "Укажите ваш стаж работы по специальности (полных лет):\n\n"
            "Если менее года, укажите 0.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationState.REGISTRATION_EXPERIENCE

    else:
        await update.message.reply_text(
            "Пожалуйста, выберите статус, используя кнопки ниже:",
            reply_markup=get_occupation_keyboard()
        )
        return ConversationState.REGISTRATION_OCCUPATION


async def handle_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора курса"""
    anonymous_id = context.user_data.get('anonymous_id')

    try:
        course = int(update.message.text)
        if course < 1 or course > 6:
            await update.message.reply_text(
                "Пожалуйста, выберите курс от 1 до 6:",
                reply_markup=get_course_keyboard()
            )
            return ConversationState.REGISTRATION_COURSE

        await update_respondent(anonymous_id, university_course=course, is_profile_complete=True)

        return await complete_registration(update, context)

    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, выберите курс, используя кнопки:",
            reply_markup=get_course_keyboard()
        )
        return ConversationState.REGISTRATION_COURSE


async def handle_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода стажа работы"""
    anonymous_id = context.user_data.get('anonymous_id')

    try:
        experience = int(update.message.text)
        if experience < 0 or experience > 60:
            await update.message.reply_text(
                "Пожалуйста, укажите корректный стаж работы (от 0 до 60 лет):"
            )
            return ConversationState.REGISTRATION_EXPERIENCE

        await update_respondent(anonymous_id, work_experience_years=experience, is_profile_complete=True)

        return await complete_registration(update, context)

    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите стаж работы числом (например, 5):"
        )
        return ConversationState.REGISTRATION_EXPERIENCE


async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение регистрации"""
    completion_message = (
        "✅ Отлично! Регистрация завершена.\n\n"
        "Теперь вы можете приступить к прохождению опросов.\n"
        "Используйте меню ниже для навигации."
    )

    await update.message.reply_text(
        completion_message,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationState.MAIN_MENU
