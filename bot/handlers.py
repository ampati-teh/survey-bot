from datetime import datetime
import hashlib

from asgiref.sync import sync_to_async
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, MessageHandler, filters

from bot.keyboards import get_main_menu_keyboard, get_gender_keyboard, get_occupation_keyboard, get_course_keyboard, \
    get_skip_keyboard, get_choice_keyboard
from bot.states import ConversationState
from survey.models import Respondent, Survey, SurveySession, Response, Question

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

async def start_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать прохождение опроса"""
    anonymous_id = context.user_data.get('anonymous_id')
    respondent = await get_respondent(anonymous_id)

    # Получаем активный опрос
    active_survey = await get_active_survey()

    if not active_survey:
        await update.message.reply_text(
            "К сожалению, в данный момент нет активных опросов. 😔\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationState.MAIN_MENU

    # Создаем сессию опроса
    session = await create_survey_session(respondent, active_survey)

    # Сохраняем ID сессии в контексте
    context.user_data['session_id'] = session.id

    # Получаем первый вопрос
    first_question = await get_first_question(active_survey)

    if not first_question:
        await update.message.reply_text(
            "Опрос еще не готов (нет вопросов). 🔧\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
        await abandon_session(session)
        return ConversationState.MAIN_MENU

    await update_session_question(session, first_question)

    await update.message.reply_text(
        f"📋 Опрос: {active_survey.title}\n\n"
        f"{active_survey.description}\n\n"
        "Приступаем к опросу!"
    )

    return await ask_question(update, context, session, first_question)


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       session: SurveySession, question: Question):
    """Задать вопрос пользователю"""
    question_text = f"❓ Вопрос {question.order + 1}:\n\n{question.text}"

    if question.question_type == 'text':
        await update.message.reply_text(
            question_text + "\n\n💬 Пожалуйста, отправьте ваш ответ текстом.",
            reply_markup=get_skip_keyboard() if not question.is_required else None
        )
        return ConversationState.WAITING_TEXT_ANSWER

    elif question.question_type == 'choice':
        options = await get_question_options(question)
        await update.message.reply_text(
            question_text + "\n\n📌 Выберите один из вариантов:",
            reply_markup=get_choice_keyboard(options)
        )
        return ConversationState.WAITING_CHOICE_ANSWER

    elif question.question_type == 'voice':
        await update.message.reply_text(
            question_text + "\n\n🎤 Пожалуйста, отправьте голосовое сообщение.",
            reply_markup=get_skip_keyboard() if not question.is_required else None
        )
        return ConversationState.WAITING_VOICE_ANSWER


async def handle_text_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ответа"""
    session_id = context.user_data.get('session_id')
    session = await get_session(session_id)
    question = session.current_question

    # Проверка на пропуск
    if update.message.text == '⏭ Пропустить' and not question.is_required:
        return await move_to_next_question(update, context, session)

    # Сохраняем ответ
    await create_response(session, question, text_answer=update.message.text)

    await update.message.reply_text("✅ Ответ сохранен!")

    return await move_to_next_question(update, context, session)


async def handle_choice_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа с выбором варианта"""
    session_id = context.user_data.get('session_id')
    session = await get_session(session_id)
    question = await session.get_current_question()

    # Проверка на пропуск
    if update.message.text == '⏭ Пропустить' and not question.is_required:
        return await move_to_next_question(update, context, session)

    # Ищем выбранный вариант
    selected_option = await find_option_by_text(question, update.message.text)

    if not selected_option:
        options = await get_question_options(question)
        await update.message.reply_text(
            "⚠️ Пожалуйста, выберите один из предложенных вариантов.",
            reply_markup=get_choice_keyboard(options)
        )
        return ConversationState.WAITING_CHOICE_ANSWER

    # Сохраняем ответ
    await create_response(session, question, selected_option=selected_option)

    await update.message.reply_text("✅ Ответ сохранен!")

    return await move_to_next_question(update, context, session)


async def handle_voice_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосового ответа"""
    session_id = context.user_data.get('session_id')
    session = await get_session(session_id)
    question = session.current_question

    if not update.message.voice:
        # Проверка на пропуск
        if update.message.text == '⏭ Пропустить' and not question.is_required:
            return await move_to_next_question(update, context, session)

        await update.message.reply_text(
            "⚠️ Пожалуйста, отправьте голосовое сообщение.",
            reply_markup=get_skip_keyboard() if not question.is_required else None
        )
        return ConversationState.WAITING_VOICE_ANSWER

    # Получаем файл
    voice_file = await update.message.voice.get_file()

    # Сохраняем ответ с file_id (файл будет скачан позже при необходимости)
    await create_response(session, question, telegram_file_id=update.message.voice.file_id)

    await update.message.reply_text("✅ Голосовое сообщение сохранено!")

    return await move_to_next_question(update, context, session)


async def move_to_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                session: SurveySession):
    """Переход к следующему вопросу или завершение опроса"""
    current_order = session.current_question.order
    next_question = await get_next_question(session.survey, current_order)

    if next_question:
        await update_session_question(session, next_question)
        return await ask_question(update, context, session, next_question)
    else:
        # Опрос завершен
        await complete_session(session)

        await update.message.reply_text(
            "🎉 Поздравляем! Вы завершили опрос!\n\n"
            "Спасибо за ваше участие. Ваши ответы очень важны для нас!",
            reply_markup=get_main_menu_keyboard()
        )

        return ConversationState.MAIN_MENU

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о боте"""
    info_text = (
        "ℹ️ О боте:\n\n"
        "Этот бот предназначен для проведения фонетических опросов.\n\n"
        "Вы можете:\n"
        "• Проходить опросы о произношении и восприятии звуков\n"
        "• Отвечать текстом, выбирать варианты или записывать голосовые сообщения\n"
        "• Просматривать свои результаты\n\n"
        "Для начала опроса нажмите '📝 Начать опрос'"
    )

    await update.message.reply_text(info_text, reply_markup=get_main_menu_keyboard())
    return ConversationState.MAIN_MENU


async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты пользователя"""
    anonymous_id = context.user_data.get('anonymous_id')
    respondent = await get_respondent(anonymous_id)

    completed_sessions = await count_completed_sessions(respondent)
    in_progress_sessions = await count_in_progress_sessions(respondent)

    results_text = (
        f"📊 Ваши результаты:\n\n"
        f"✅ Завершенных опросов: {completed_sessions}\n"
        f"⏳ Опросов в процессе: {in_progress_sessions}\n\n"
        "Спасибо за ваше участие!"
    )

    await update.message.reply_text(results_text, reply_markup=get_main_menu_keyboard())
    return ConversationState.MAIN_MENU


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль респондента"""
    anonymous_id = context.user_data.get('anonymous_id')
    respondent = await get_respondent(anonymous_id)

    gender_text = respondent.get_gender_display() if respondent.gender else "Не указано"
    age_text = f"{respondent.age} лет" if respondent.age else "Не указано"
    occupation_text = respondent.get_occupation_display_full()

    profile_text = (
        f"👤 Ваш профиль:\n\n"
        f"Пол: {gender_text}\n"
        f"Возраст: {age_text}\n"
        f"Статус: {occupation_text}\n\n"
        f"📊 Все данные анонимны и защищены."
    )

    await update.message.reply_text(profile_text, reply_markup=get_main_menu_keyboard())
    return ConversationState.MAIN_MENU


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка главного меню"""
    text = update.message.text

    if text == '📝 Начать опрос':
        return await start_survey(update, context)
    elif text == 'ℹ️ Информация':
        return await show_info(update, context)
    elif text == '📊 Мои результаты':
        return await show_results(update, context)
    elif text == '👤 Мой профиль':
        return await show_profile(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации.",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationState.MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    session_id = context.user_data.get('session_id')
    if session_id:
        session = await get_session(session_id)
        await abandon_session(session)

    await update.message.reply_text(
        "Действие отменено. Возвращаемся в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationState.MAIN_MENU


def setup_handlers(application: Application):
    """Настройка обработчиков бота"""

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            # Состояния регистрации
            ConversationState.REGISTRATION_GENDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender)
            ],
            ConversationState.REGISTRATION_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)
            ],
            ConversationState.REGISTRATION_OCCUPATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_occupation)
            ],
            ConversationState.REGISTRATION_COURSE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_course)
            ],
            ConversationState.REGISTRATION_EXPERIENCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_experience)
            ],
            # Основные состояния
            ConversationState.MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
            ],
            ConversationState.WAITING_TEXT_ANSWER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_answer)
            ],
            ConversationState.WAITING_CHOICE_ANSWER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice_answer)
            ],
            ConversationState.WAITING_VOICE_ANSWER: [
                MessageHandler(filters.VOICE | filters.TEXT, handle_voice_answer)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
