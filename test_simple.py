"""
Упрощенная версия главного модуля для тестирования
"""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from logging.handlers import TimedRotatingFileHandler

# Импорты модулей
from src.config.settings import load_config, TOKEN, BOT_VERSION
from src.config.translations import TRANSLATIONS as T
from src.keyboards.user_keyboards import kb_main

def setup_logging():
    """Настройка логирования"""
    logger = logging.getLogger("bot")
    logger.setLevel(logging.INFO)
    
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    
    # Консольный вывод
    logger.addHandler(logging.StreamHandler())
    
    return logger

async def main():
    """Главная функция запуска бота"""
    
    # Настройка логирования
    logger = setup_logging()
    logger.info(f"Запуск упрощенного бота версии {BOT_VERSION}")
    
    # Загрузка конфигурации
    load_config()
    
    # Создание бота
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Создание диспетчера
    dp = Dispatcher()
    
    # Простой обработчик для тестирования
    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        await message.answer(T["start"], reply_markup=kb_main())
        logger.info(f"Пользователь {message.from_user.id} выполнил команду /start")
    
    @dp.message(Command("version"))
    async def cmd_version(message: Message):
        text = f"{T['version_pre']}{BOT_VERSION}"
        await message.answer(text)
        logger.info(f"Пользователь {message.from_user.id} запросил версию")
    
    @dp.message()
    async def echo(message: Message):
        await message.answer("❓ Используйте команды /start или /version для тестирования модульного бота")
    
    logger.info("Упрощенный бот запущен и готов к работе")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())