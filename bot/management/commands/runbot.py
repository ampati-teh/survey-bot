import os
import django
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram.ext import Application
from bot.handlers import setup_handlers


class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **options):
        """Запуск бота"""
        self.stdout.write(self.style.SUCCESS('Запуск Telegram бота...'))

        # Проверяем наличие токена
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stdout.write(
                self.style.ERROR('Ошибка: TELEGRAM_BOT_TOKEN не установлен в .env файле')
            )
            return

        # Создаем приложение
        application = Application.builder().token(token).build()

        # Настраиваем обработчики
        setup_handlers(application)

        # Запускаем бота
        self.stdout.write(self.style.SUCCESS('Бот успешно запущен!'))
        self.stdout.write(self.style.SUCCESS('Нажмите Ctrl+C для остановки'))

        application.run_polling(allowed_updates=['message', 'callback_query'])
