"""
Полнофункциональная версия модульного бота
"""
import asyncio
import json
import logging
import os
import secrets

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramBadRequest
from logging.handlers import TimedRotatingFileHandler

# Импорты модулей
from src.config.settings import load_config, TOKEN, REDIS_DSN, BOT_VERSION, CONFIG, ADMIN_ID
from src.config.translations import TRANSLATIONS as T
from src.database.connection import get_pool
from src.database.user_operations import (
    get_account_info, delete_account, admin_delete_account, get_account_by_email,
    register_user, reset_password, change_password
)
from src.utils.middleware import RateLimit
from src.utils.notifications import safe_edit_message, delete_all_bot_messages, record_message
from src.utils.validators import validate_email, validate_nickname, validate_password, filter_text, is_text_only, check_password_strength
from src.keyboards.user_keyboards import kb_main, kb_back, kb_account_list, kb_password_weak_choice
from src.keyboards.admin_keyboards import kb_admin, kb_admin_back
from src.states.user_states import RegistrationStates, ForgotPasswordStates, ChangePasswordStates, AdminStates

# Импорты модульных обработчиков
from src.handlers.commands import register_command_handlers, register_callback_handlers
from src.handlers.registration import register_registration_handlers
from src.handlers.account_management import register_account_handlers
from src.handlers.admin import register_admin_handlers
from src.handlers.messages import register_message_handlers

def setup_logging():
    """Настройка логирования"""
    logger = logging.getLogger("bot")
    logger.setLevel(logging.INFO)
    
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    
    # Обработчик для основного лога
    h_info = TimedRotatingFileHandler("bot.log", when="midnight", backupCount=7, encoding="utf-8")
    h_info.setLevel(logging.INFO)
    h_info.setFormatter(fmt)
    logger.addHandler(h_info)
    
    # Обработчик для ошибок
    h_err = TimedRotatingFileHandler("error.log", when="midnight", backupCount=7, encoding="utf-8")
    h_err.setLevel(logging.ERROR)
    h_err.setFormatter(fmt)
    logger.addHandler(h_err)
    
    # Консольный вывод
    logger.addHandler(logging.StreamHandler())
    
    return logger

# Глобальные переменные для состояний
user_wizard_msg = {}
main_menu_msgs = {}
admin_menu_msgs = {}
# Хранилище для ID последних предупреждающих сообщений (для предотвращения накопления)
user_warning_msgs = {}

def kb_wizard(step):
    """Клавиатура для мастера регистрации"""
    btns = []
    if step > 0:
        btns.append(InlineKeyboardButton(text=T["back"], callback_data="wiz_back"))
    btns.append(InlineKeyboardButton(text=T["cancel"], callback_data="wiz_cancel"))
    return InlineKeyboardMarkup(inline_keyboard=[btns])

async def main():
    """Главная функция запуска бота"""
    
    # Настройка логирования
    logger = setup_logging()
    logger.info(f"Запуск полнофункциональной версии бота {BOT_VERSION}")
    
    # Загрузка конфигурации
    load_config()
    
    # Создание бота
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Настройка Redis и хранилища 
    try:
        redis_cli = aioredis.from_url(REDIS_DSN)
        storage = RedisStorage(redis=redis_cli, state_ttl=3600)
        logger.info("Redis подключен для FSM хранилища")
    except Exception as e:
        logger.warning(f"Redis недоступен, используется память: {e}")
        storage = None
    
    # Создание диспетчера
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    
    async def render_main_menu(chat_id: int, user_id: int, callback_or_message=None):
        # Очищаем предупреждающие сообщения при возврате в главное меню
        user_warning_msgs.pop(user_id, None)
        kb = kb_main(is_admin=user_id == ADMIN_ID)
        msg_id = main_menu_msgs.get(user_id)
        
        # Пытаемся отредактировать существующее сообщение, если оно есть
        if msg_id:
            try:
                await bot.edit_message_text(
                    text=T["start"],
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=kb
                )
                return
            except (TelegramBadRequest, Exception):
                # Если не удалось отредактировать, удаляем из кэша и создаем новое
                main_menu_msgs.pop(user_id, None)
        
        # Если есть callback_or_message, пытаемся отредактировать его
        if callback_or_message:
            try:
                msg = await safe_edit_message(bot, callback_or_message, T["start"], reply_markup=kb)
                main_menu_msgs[user_id] = msg.message_id
                return msg
            except Exception:
                pass
        
        # Создаем новое сообщение только если не удалось отредактировать существующее
        msg = await bot.send_message(chat_id, T["start"], reply_markup=kb)
        main_menu_msgs[user_id] = msg.message_id
        return msg

    async def render_admin_menu(chat_id: int, user_id: int, callback_or_message=None):
        msg_id = admin_menu_msgs.get(user_id)
        
        # Пытаемся отредактировать существующее сообщение, если оно есть
        if msg_id:
            try:
                await bot.edit_message_text(
                    text=T["admin_panel"],
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=kb_admin()
                )
                return
            except (TelegramBadRequest, Exception):
                # Если не удалось отредактировать, удаляем из кэша и создаем новое
                admin_menu_msgs.pop(user_id, None)
        
        # Если есть callback_or_message, пытаемся отредактировать его
        if callback_or_message:
            try:
                msg = await safe_edit_message(bot, callback_or_message, T["admin_panel"], reply_markup=kb_admin())
                admin_menu_msgs[user_id] = msg.message_id
                return msg
            except Exception:
                pass
        
        # Создаем новое сообщение только если не удалось отредактировать существующее
        msg = await bot.send_message(chat_id, T["admin_panel"], reply_markup=kb_admin())
        admin_menu_msgs[user_id] = msg.message_id
        return msg

    
    # Подключение middleware
    dp.message.middleware(RateLimit())
    dp.callback_query.middleware(RateLimit())
    
    # Подключение к базе данных
    try:
        pool = await get_pool()
        logger.info("Подключение к базе данных установлено")
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        pool = None

    # Регистрация модульных обработчиков
    register_command_handlers(dp, pool, bot)
    register_callback_handlers(dp, pool, bot)
    register_registration_handlers(dp, pool, bot)
    register_account_handlers(dp, pool, bot)
    register_admin_handlers(dp, pool, bot)
    register_message_handlers(dp, pool, bot)
    
    logger.info("Все модульные обработчики зарегистрированы")
    logger.info("Полнофункциональный бот запущен и готов к работе")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка в polling: {e}")
    finally:
        if pool:
            pool.close()
            await pool.wait_closed()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
