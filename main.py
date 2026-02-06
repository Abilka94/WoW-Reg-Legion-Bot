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
from src.utils.validators import validate_email, validate_nickname, validate_password, filter_text, is_text_only
from src.keyboards.user_keyboards import kb_main, kb_back, kb_account_list
from src.keyboards.admin_keyboards import kb_admin, kb_admin_back
from src.states.user_states import RegistrationStates, ForgotPasswordStates, ChangePasswordStates, AdminStates

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

    # ==================== КОМАНДЫ ====================
    
    @dp.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()
        # Удаляем сообщение пользователя, чтобы не накапливались
        try:
            await message.delete()
        except Exception:
            pass
        
        # Удаляем старое сообщение меню, если оно существует, чтобы не накапливались
        old_msg_id = main_menu_msgs.get(message.from_user.id)
        if old_msg_id:
            try:
                await bot.delete_message(message.chat.id, old_msg_id)
            except Exception:
                pass
            main_menu_msgs.pop(message.from_user.id, None)
        
        await render_main_menu(message.chat.id, message.from_user.id)
        logger.info(f"Команда /start от пользователя {message.from_user.id}")

    @dp.message(Command("version"))
    async def cmd_version(message: Message):
        text = f"{T['version_pre']}{BOT_VERSION}\n\n"
        text += "🧩 Полнофункциональная модульная архитектура:\n"
        text += f"✅ Конфигурация: {sum(CONFIG['features'].values())}/{len(CONFIG['features'])} функций\n"
        text += f"✅ База данных: {'подключена' if pool else 'не подключена'}\n"
        text += f"✅ Redis FSM: {'подключен' if storage else 'отключен'}\n"
        text += "✅ Регистрация пользователей\n"
        text += "✅ Управление аккаунтами\n"
        text += "✅ Админ панель"
        
        await message.answer(text, reply_markup=kb_back())
        logger.info(f"Команда /version от пользователя {message.from_user.id}")

    @dp.message(Command("admin"))
    async def cmd_admin(message: Message, state: FSMContext):
        await state.clear()
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass
        
        # Удаляем старое сообщение админ меню, если оно существует (как в /start)
        old_admin_id = admin_menu_msgs.get(message.from_user.id)
        if old_admin_id:
            try:
                await bot.delete_message(message.chat.id, old_admin_id)
            except Exception:
                pass
            admin_menu_msgs.pop(message.from_user.id, None)
        
        if message.from_user.id != ADMIN_ID:
            await message.answer(T["no_access"], reply_markup=kb_back())
            return
        
        await render_admin_menu(message.chat.id, message.from_user.id)
        logger.info(f"Админ панель открыта пользователем {message.from_user.id}")

    # ==================== CALLBACK ОСНОВНЫЕ ====================
    
    @dp.callback_query(F.data == "back_to_main")
    async def cb_back_main(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await render_main_menu(callback.message.chat.id, callback.from_user.id, callback)
        await callback.answer()
    @dp.callback_query(F.data == "show_info")
    async def cb_show_info(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        from src.utils.file_cache import FileCache
        info_cache = FileCache("connection_info.txt")
        text = await info_cache.get()
        
        if not text:
            text = "📋 Информация о подключении:\n\n" + \
                   "🔗 Для получения данных подключения к серверу обратитесь к администратору."
        
        await safe_edit_message(bot, callback, text, reply_markup=kb_back())
        await callback.answer()

    @dp.callback_query(F.data == "show_news")
    async def cb_show_news(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        from src.utils.file_cache import FileCache
        news_cache = FileCache("news.txt")
        text = await news_cache.get()
        
        if not text:
            text = "📰 Новости сервера:\n\n" + \
                   "В данный момент новостей нет.\nСледите за обновлениями!"
        
        await safe_edit_message(bot, callback, text, reply_markup=kb_back())
        await callback.answer()

    # ==================== УПРАВЛЕНИЕ АККАУНТАМИ ====================
    
    @dp.callback_query(F.data == "my_account")
    async def cb_my_account(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        if not pool:
            await callback.answer("База данных недоступна", show_alert=True)
            return
            
        accounts = await get_account_info(pool, callback.from_user.id)
        
        if not accounts:
            text = "❌ У вас нет зарегистрированного аккаунта.\n\n" + \
                   "Используйте кнопку 'Регистрация' для создания аккаунта."
        else:
            text = T["select_account_prompt"]
        
        await safe_edit_message(bot, callback, text, reply_markup=kb_account_list(accounts) if accounts else kb_back())
        await callback.answer()
        logger.info(f"Просмотр аккаунтов пользователем {callback.from_user.id}")

    @dp.callback_query(F.data.startswith("select_account_"))
    async def cb_select_account(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        email = callback.data.replace("select_account_", "")
        accounts = await get_account_info(pool, callback.from_user.id)
        
        if not accounts:
            await safe_edit_message(bot, callback, T["account_no_account"], reply_markup=kb_back())
            return
        
        selected = next((acc for acc in accounts if acc[0] == email), None)
        if not selected:
            await callback.answer("❌ Аккаунт не найден", show_alert=True)
            return
        
        email, username, is_temp, temp_password = selected
        pwd_status = f"🔄 Временный пароль: {temp_password}" if is_temp else "✅ Постоянный пароль"
        text = f"🔑 Ваш аккаунт:\nЛогин: <code>{username}</code>\nE-mail: <code>{email}</code>\nСтатус: {pwd_status}"
        
        await safe_edit_message(bot, callback, text, reply_markup=kb_account_list(accounts, selected_email=email))
        await callback.answer()

    @dp.callback_query(F.data.startswith("reset_password_"))
    async def cb_reset_password(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        email = callback.data.replace("reset_password_", "")
        accounts = await get_account_info(pool, callback.from_user.id)
        if not accounts:
            await callback.answer("❌ Аккаунт не найден", show_alert=True)
            return
        if not any(acc[0] == email for acc in accounts):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        tmp = await reset_password(pool, email)
        if tmp is None:
            await callback.answer(T["reset_err_not_found"], show_alert=True)
            return
        text_msg = T["reset_success"].format(password=tmp)
        await safe_edit_message(bot, callback, text_msg, reply_markup=kb_account_list(accounts, selected_email=email))
        await callback.answer()

    @dp.callback_query(F.data == "change_password")
    async def cb_change_password(callback: CallbackQuery, state: FSMContext):
        accounts = await get_account_info(pool, callback.from_user.id)
        if not accounts:
            await callback.answer("❌ Аккаунты не найдены", show_alert=True)
            return
        
        # Найти выбранный email из текста сообщения
        selected_email = None
        for email, *_ in accounts:
            if email in callback.message.text:
                selected_email = email
                break
        
        if not selected_email:
            await callback.answer("❌ Не удалось определить аккаунт", show_alert=True)
            return
        
        await state.set_state(ChangePasswordStates.new_password)
        await state.update_data(email=selected_email)
        await callback.message.edit_text(T["change_password_prompt"], reply_markup=kb_back())

    @dp.message(ChangePasswordStates.new_password)
    async def step_change_password(message: Message, state: FSMContext):
        # Проверяем, что это текстовое сообщение
        if not is_text_only(message) or not message.text:
            try:
                await message.delete()
            except Exception:
                pass
            # Редактируем существующее сообщение с ошибкой (используем main_menu_msgs как fallback)
            # В идеале нужно хранить ID сообщения для этого состояния, но для упрощения используем main_menu_msgs
            return
        
        data = await state.get_data()
        email = data.get("email")
        # Фильтруем текст перед обработкой
        new_password = filter_text(message.text.strip(), max_length=100)
        
        try:
            await message.delete()
        except Exception:
            pass
        
        if not new_password:
            # Просто возвращаемся, не создавая новых сообщений
            return
        
        if new_password in (T["to_main"], T["cancel"]):
            await state.clear()
            # Удаляем старое сообщение меню перед созданием нового (как в /start)
            old_menu_id = main_menu_msgs.get(message.from_user.id)
            if old_menu_id:
                try:
                    await bot.delete_message(message.chat.id, old_menu_id)
                except Exception:
                    pass
                main_menu_msgs.pop(message.from_user.id, None)
            await render_main_menu(message.chat.id, message.from_user.id)
            return
        
        # Валидация пароля с детальными сообщениями об ошибках
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            await message.answer(f"❌ {error_msg}")
            return
        
        try:
            await change_password(pool, email, new_password)
            await state.clear()
            # Удаляем старое сообщение меню перед созданием нового (как в /start)
            old_menu_id = main_menu_msgs.get(message.from_user.id)
            if old_menu_id:
                try:
                    await bot.delete_message(message.chat.id, old_menu_id)
                except Exception:
                    pass
                main_menu_msgs.pop(message.from_user.id, None)
            # Создаем новое сообщение меню
            await render_main_menu(message.chat.id, message.from_user.id)
        except Exception as e:
            logger.error(f"Ошибка смены пароля: {e}")
            await state.clear()
            # Удаляем старое сообщение меню перед созданием нового
            old_menu_id = main_menu_msgs.get(message.from_user.id)
            if old_menu_id:
                try:
                    await bot.delete_message(message.chat.id, old_menu_id)
                except Exception:
                    pass
                main_menu_msgs.pop(message.from_user.id, None)
            # Создаем новое сообщение меню
            await render_main_menu(message.chat.id, message.from_user.id)

    @dp.callback_query(F.data.startswith("delete_account_"))
    async def cb_delete_account(callback: CallbackQuery, state: FSMContext):
        email = callback.data.replace("delete_account_", "")
        
        # Показываем подтверждение удаления
        accounts = await get_account_info(pool, callback.from_user.id)
        selected = next((acc for acc in accounts if acc[0] == email), None)
        
        if not selected:
            await callback.answer("❌ Аккаунт не найден", show_alert=True)
            return
        
        email_addr, username, is_temp, temp_password = selected
        confirm_text = f"⚠️ ВНИМАНИЕ! Вы уверены, что хотите удалить аккаунт?\n\n" \
                       f"📧 E-mail: <code>{email_addr}</code>\n" \
                       f"👤 Логин: <code>{username}</code>\n\n" \
                       f"❌ Это действие нельзя отменить!"
        
        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_account_{email}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"select_account_{email}")
            ]
        ])
        
        await safe_edit_message(bot, callback, confirm_text, reply_markup=confirm_keyboard)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("confirm_delete_account_"))
    async def cb_confirm_delete_account(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        email = callback.data.replace("confirm_delete_account_", "")
        
        try:
            success = await delete_account(pool, callback.from_user.id, email)
            if success:
                await safe_edit_message(bot, callback, T["delete_account_success"], reply_markup=kb_back())
            else:
                await safe_edit_message(bot, callback, T["delete_account_error"], reply_markup=kb_back())
        except Exception as e:
            logger.error(f"Ошибка удаления аккаунта: {e}")
            await safe_edit_message(bot, callback, "❌ Ошибка при удалении аккаунта", reply_markup=kb_back())
        await callback.answer()
        

    # ==================== РЕГИСТРАЦИЯ ====================
    
    @dp.callback_query(F.data == "reg_start")
    async def cb_registration_start(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        # Очищаем предупреждающие сообщения при начале регистрации
        user_warning_msgs.pop(callback.from_user.id, None)
        
        # Удаляем старое wizard сообщение, если оно существует (как в /start)
        old_wizard_id = user_wizard_msg.get(callback.from_user.id)
        if old_wizard_id:
            try:
                await bot.delete_message(callback.message.chat.id, old_wizard_id)
            except Exception:
                pass
            user_wizard_msg.pop(callback.from_user.id, None)
        
        await state.set_state(RegistrationStates.nick)
        text = f"1/3 · {T['progress'][0]}"
        
        try:
            msg = await callback.message.edit_text(text, reply_markup=kb_wizard(0))
            user_wizard_msg[callback.from_user.id] = msg.message_id
        except:
            msg = await callback.message.answer(text, reply_markup=kb_wizard(0))
            user_wizard_msg[callback.from_user.id] = msg.message_id
        

    @dp.callback_query(F.data.in_(["wiz_back", "wiz_cancel"]))
    async def cb_wiz_nav(callback: CallbackQuery, state: FSMContext):
        current_state = await state.get_state()
        
        if callback.data == "wiz_cancel":
            await state.clear()
            await render_main_menu(callback.message.chat.id, callback.from_user.id, callback)
            await callback.answer()
            return
        
        # Обработка wiz_back
        if current_state == RegistrationStates.nick.state:
            await state.clear()
            await render_main_menu(callback.message.chat.id, callback.from_user.id, callback)
            await callback.answer()
        elif current_state == RegistrationStates.pwd.state:
            await state.set_state(RegistrationStates.nick)
            text = f"1/3 · {T['progress'][0]}"
            await safe_edit_message(bot, callback, text, reply_markup=kb_wizard(0))
            await callback.answer()
        elif current_state == RegistrationStates.mail.state:
            await state.set_state(RegistrationStates.pwd)
            text = f"2/3 · {T['progress'][1]}"
            await safe_edit_message(bot, callback, text, reply_markup=kb_wizard(1))
            await callback.answer()
        

    @dp.message(RegistrationStates.nick)
    async def step_nick(message: Message, state: FSMContext):
        # Проверяем, что это текстовое сообщение
        if not is_text_only(message) or not message.text:
            try:
                await message.delete()
            except Exception:
                pass
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text="❌ Пожалуйста, отправляйте только текстовые сообщения.",
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(0)
                    )
                except Exception:
                    pass
            return
        
        # Фильтруем текст перед обработкой
        nick = filter_text(message.text.strip(), max_length=50)
        
        try:
            await message.delete()
        except Exception:
            pass
        
        if not nick:
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text="❌ Никнейм содержит недопустимые символы. Используйте только буквы и цифры.",
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(0)
                    )
                except Exception:
                    pass
            return
        
        if not validate_nickname(nick):
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text=T["err_nick"],
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(0)
                    )
                except Exception:
                    pass
            return
        
        await state.update_data(nick=nick)
        await state.set_state(RegistrationStates.pwd)
        text = f"2/3 · {T['progress'][1]}"
        
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=user_wizard_msg.get(message.from_user.id),
                reply_markup=kb_wizard(1)
            )
        except:
            msg = await message.answer(text, reply_markup=kb_wizard(1))
            user_wizard_msg[message.from_user.id] = msg.message_id

    @dp.message(RegistrationStates.pwd)
    async def step_pwd(message: Message, state: FSMContext):
        # Проверяем, что это текстовое сообщение
        if not is_text_only(message) or not message.text:
            try:
                await message.delete()
            except Exception:
                pass
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text="❌ Пожалуйста, отправляйте только текстовые сообщения.",
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(1)
                    )
                except Exception:
                    pass
            return
        
        # Фильтруем текст перед обработкой
        pwd = filter_text(message.text.strip(), max_length=100)
        
        try:
            await message.delete()
        except Exception:
            pass
        
        if not pwd:
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text="❌ Пароль содержит недопустимые символы. Используйте только буквы, цифры и основные знаки препинания.",
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(1)
                    )
                except Exception:
                    pass
            return
        
        # Валидация пароля с детальными сообщениями об ошибках
        is_valid, error_msg = validate_password(pwd)
        if not is_valid:
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text=f"❌ {error_msg}",
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(1)
                    )
                except Exception:
                    pass
            return
        
        await state.update_data(pwd=pwd)
        await state.set_state(RegistrationStates.mail)
        text = f"3/3 · {T['progress'][2]}"
        
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=user_wizard_msg.get(message.from_user.id),
                reply_markup=kb_wizard(2)
            )
        except:
            msg = await message.answer(text, reply_markup=kb_wizard(2))
            user_wizard_msg[message.from_user.id] = msg.message_id

    @dp.message(RegistrationStates.mail)
    async def step_mail(message: Message, state: FSMContext):
        # Проверяем, что это текстовое сообщение
        if not is_text_only(message) or not message.text:
            try:
                await message.delete()
            except Exception:
                pass
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text="❌ Пожалуйста, отправляйте только текстовые сообщения.",
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(2)
                    )
                except Exception:
                    pass
            return
        
        # Фильтруем текст перед обработкой (email может содержать @ и точку)
        email = filter_text(message.text.strip(), max_length=100, allow_email_chars=True)
        
        try:
            await message.delete()
        except Exception:
            pass
        
        if not email:
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text="❌ E-mail содержит недопустимые символы.",
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(2)
                    )
                except Exception:
                    pass
            return
        
        # Строгая валидация email с проверкой известных провайдеров
        is_valid, error_msg = validate_email(email, strict=True)
        if not is_valid:
            # Редактируем существующее wizard сообщение с ошибкой
            wizard_id = user_wizard_msg.get(message.from_user.id)
            if wizard_id:
                try:
                    await bot.edit_message_text(
                        text=f"❌ {error_msg}\n\n{T['err_mail']}",
                        chat_id=message.chat.id,
                        message_id=wizard_id,
                        reply_markup=kb_wizard(2)
                    )
                except Exception:
                    pass
            return
        
        data = await state.get_data()
        
        try:
            login, error = await register_user(pool, data["nick"], data["pwd"], email, message.from_user.id)
            
            if not login:
                # Если ошибка с username, возвращаемся к шагу ввода никнейма
                if error == "err_username_exists":
                    await state.set_state(RegistrationStates.nick)
                    wizard_id = user_wizard_msg.get(message.from_user.id)
                    if wizard_id:
                        try:
                            await bot.edit_message_text(
                                text=f"❌ {T[error]}\n\n1/3 · {T['progress'][0]}",
                                chat_id=message.chat.id,
                                message_id=wizard_id,
                                reply_markup=kb_wizard(0)
                            )
                        except Exception:
                            pass
                    return
                
                # Для других ошибок завершаем регистрацию
                await state.clear()
                final_text = T[error].format(max_accounts=CONFIG["settings"]["max_accounts_per_user"])
            else:
                await state.clear()
                final_text = T["success"].format(username=login)
            
            # Удаляем старое wizard сообщение перед созданием нового меню (как в /start)
            wizard_msg_id = user_wizard_msg.pop(message.from_user.id, None)
            if wizard_msg_id:
                try:
                    await bot.delete_message(message.chat.id, wizard_msg_id)
                except Exception:
                    pass
            
            # Создаем новое сообщение меню
            await render_main_menu(message.chat.id, message.from_user.id)
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            await state.clear()
            # Удаляем старое wizard сообщение перед созданием нового меню
            wizard_msg_id = user_wizard_msg.pop(message.from_user.id, None)
            if wizard_msg_id:
                try:
                    await bot.delete_message(message.chat.id, wizard_msg_id)
                except Exception:
                    pass
            # Создаем новое сообщение меню
            await render_main_menu(message.chat.id, message.from_user.id)

    # ==================== АДМИН ПАНЕЛЬ ====================
    
    @dp.callback_query(F.data == "admin_check_db")
    async def cb_admin_check_db(callback: CallbackQuery):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
            
        if pool:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM battlenet_accounts")
                    count = (await cur.fetchone())[0]
                    text = f"✅ База данных работает корректно\n📊 Аккаунтов в системе: {count}"
        else:
            text = "❌ База данных не подключена"
            
        await safe_edit_message(bot, callback, text, reply_markup=kb_admin_back())
        await callback.answer()

    @dp.callback_query(F.data == "admin_delete_account")
    async def cb_admin_delete_account(callback: CallbackQuery, state: FSMContext):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        await state.set_state(AdminStates.delete_account_input)
        await safe_edit_message(bot, callback, T["admin_delete_prompt"], reply_markup=kb_admin_back())
        await callback.answer()

    @dp.message(AdminStates.delete_account_input)
    async def step_admin_delete_account(message: Message, state: FSMContext):
        # Проверяем, что это текстовое сообщение
        if not is_text_only(message) or not message.text:
            try:
                await message.delete()
            except Exception:
                pass
            # Редактируем существующее сообщение админ панели с ошибкой
            admin_id = admin_menu_msgs.get(message.from_user.id)
            if admin_id:
                try:
                    await bot.edit_message_text(
                        text="❌ Пожалуйста, отправляйте только текстовые сообщения.",
                        chat_id=message.chat.id,
                        message_id=admin_id,
                        reply_markup=kb_admin_back()
                    )
                except Exception:
                    pass
            return
        
        # Фильтруем текст перед обработкой (email может содержать @ и точку)
        email = filter_text(message.text.strip(), max_length=100, allow_email_chars=True)
        
        try:
            await message.delete()
        except Exception:
            pass
        
        if not email:
            # Редактируем существующее сообщение админ панели с ошибкой
            admin_id = admin_menu_msgs.get(message.from_user.id)
            if admin_id:
                try:
                    await bot.edit_message_text(
                        text="❌ E-mail содержит недопустимые символы.",
                        chat_id=message.chat.id,
                        message_id=admin_id,
                        reply_markup=kb_admin_back()
                    )
                except Exception:
                    pass
            return
        
        if not validate_email(email):
            # Редактируем существующее сообщение админ панели с ошибкой
            admin_id = admin_menu_msgs.get(message.from_user.id)
            if admin_id:
                try:
                    await bot.edit_message_text(
                        text="❌ Некорректный e-mail",
                        chat_id=message.chat.id,
                        message_id=admin_id,
                        reply_markup=kb_admin_back()
                    )
                except Exception:
                    pass
            return
        
        try:
            # Получаем информацию об аккаунте
            username, telegram_id = await get_account_by_email(pool, email)
            if not username:
                admin_id = admin_menu_msgs.get(message.from_user.id)
                if admin_id:
                    try:
                        await bot.edit_message_text(
                            text=T["admin_delete_error"].format(error="Аккаунт не найден"),
                            chat_id=message.chat.id,
                            message_id=admin_id,
                            reply_markup=kb_admin_back()
                        )
                    except Exception:
                        pass
                return
            
            # Сохраняем данные для подтверждения
            await state.update_data(email=email, username=username, telegram_id=telegram_id)
            await state.set_state(AdminStates.delete_account_confirm)
            
            # Показываем предупреждение с подтверждением
            confirm_text = T["admin_delete_confirm"].format(email=email, username=username)
            confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=T["admin_delete_confirm_yes"], callback_data="admin_confirm_delete"),
                    InlineKeyboardButton(text=T["admin_delete_confirm_no"], callback_data="admin_back")
                ]
            ])
            
            admin_id = admin_menu_msgs.get(message.from_user.id)
            if admin_id:
                try:
                    await bot.edit_message_text(
                        text=confirm_text,
                        chat_id=message.chat.id,
                        message_id=admin_id,
                        reply_markup=confirm_keyboard
                    )
                except Exception:
                    # Если не удалось отредактировать, отправляем новое сообщение
                    msg = await bot.send_message(message.chat.id, confirm_text, reply_markup=confirm_keyboard)
                    admin_menu_msgs[message.from_user.id] = msg.message_id
            else:
                msg = await bot.send_message(message.chat.id, confirm_text, reply_markup=confirm_keyboard)
                admin_menu_msgs[message.from_user.id] = msg.message_id
        except Exception as e:
            logger.error(f"Ошибка при получении информации об аккаунте: {e}")
            await state.clear()
            admin_id = admin_menu_msgs.get(message.from_user.id)
            if admin_id:
                try:
                    await bot.edit_message_text(
                        text=T["admin_delete_error"].format(error=str(e)),
                        chat_id=message.chat.id,
                        message_id=admin_id,
                        reply_markup=kb_admin_back()
                    )
                except Exception:
                    pass

    @dp.callback_query(F.data == "admin_confirm_delete")
    async def cb_admin_confirm_delete(callback: CallbackQuery, state: FSMContext):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        data = await state.get_data()
        email = data.get("email")
        username = data.get("username")
        telegram_id = data.get("telegram_id")
        
        if not email:
            await callback.answer("❌ Ошибка: данные не найдены", show_alert=True)
            await state.clear()
            await render_admin_menu(callback.message.chat.id, callback.from_user.id, callback)
            return
        
        try:
            # Удаляем аккаунт
            success, deleted_telegram_id = await admin_delete_account(pool, email)
            await state.clear()
            
            if success:
                # Отправляем уведомление пользователю, если он существует
                if deleted_telegram_id:
                    try:
                        notification_text = T["account_deleted_by_admin"].format(email=email, username=username)
                        await bot.send_message(deleted_telegram_id, notification_text)
                        logger.info(f"Уведомление об удалении отправлено пользователю {deleted_telegram_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось отправить уведомление пользователю {deleted_telegram_id}: {e}")
                
                # Уведомляем админа об успехе
                await safe_edit_message(bot, callback, T["admin_delete_success"].format(email=email), reply_markup=kb_admin_back())
            else:
                await safe_edit_message(bot, callback, T["admin_delete_error"].format(error="Не удалось удалить аккаунт"), reply_markup=kb_admin_back())
        
        except Exception as e:
            logger.error(f"Ошибка при удалении аккаунта админом: {e}")
            await state.clear()
            await safe_edit_message(bot, callback, T["admin_delete_error"].format(error=str(e)), reply_markup=kb_admin_back())
        
        await callback.answer()

    @dp.callback_query(F.data.in_(["admin_broadcast", "admin_reload_config"]))
    async def cb_admin_other_functions(callback: CallbackQuery):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        await callback.answer("🔧 Функция в разработке", show_alert=True)

    

    @dp.callback_query(F.data == "admin_back")
    async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await render_admin_menu(callback.message.chat.id, callback.from_user.id, callback)
        await callback.answer()


    @dp.callback_query(F.data == "admin_main")
    async def cb_admin_main(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        if callback.message:
            main_menu_msgs[callback.from_user.id] = callback.message.message_id
        await render_main_menu(callback.message.chat.id, callback.from_user.id, callback)
        await callback.answer()

    @dp.callback_query(F.data == "open_admin_panel")
    async def cb_open_admin_panel(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        if callback.from_user.id != ADMIN_ID:
            await callback.answer(T["no_access"], show_alert=True)
            return
        if callback.message:
            admin_menu_msgs[callback.from_user.id] = callback.message.message_id
        await render_admin_menu(callback.message.chat.id, callback.from_user.id, callback)
        await callback.answer()


    @dp.callback_query()
    async def cb_other(callback: CallbackQuery):
        await callback.answer("🔧 Функция в разработке")
        logger.info(f"Необработанный callback: {callback.data}")

    # Обработчик для блокировки нежелательных типов сообщений (файлы, стикеры и т.д.)
    # Этот обработчик должен быть ПЕРЕД общим обработчиком handle_private_messages
    @dp.message(F.chat.type == ChatType.PRIVATE)
    async def handle_non_text_messages(message: Message, state: FSMContext):
        """Блокирует файлы, стикеры, эмодзи и другие нежелательные типы сообщений"""
        current_state = await state.get_state()
        
        # Пропускаем сообщения в состояниях FSM (они обрабатываются отдельно)
        if current_state in (
            RegistrationStates.nick.state,
            RegistrationStates.pwd.state,
            RegistrationStates.mail.state,
            ChangePasswordStates.new_password.state,
            AdminStates.delete_account_input.state
        ):
            # В FSM состояниях тоже блокируем нежелательные типы
            if not is_text_only(message):
                try:
                    await message.delete()
                except Exception:
                    pass
                
                # Просто удаляем нежелательные типы сообщений без ответа
            return
        
        # Блокируем все нежелательные типы сообщений (кроме команд)
        if not is_text_only(message):
            # Команды обрабатываются отдельно, пропускаем их
            if message.text and message.text.startswith("/"):
                return
            try:
                await message.delete()
            except Exception:
                pass
            # Просто удаляем нежелательные типы сообщений без ответа
            return
        
        # Если это текстовое сообщение, но не команда - обрабатываем дальше
        if message.text and not message.text.startswith("/"):
            current_state = await state.get_state()
            
            # Пропускаем сообщения в состояниях FSM (они обрабатываются отдельными обработчиками)
            if current_state in (
                RegistrationStates.nick.state,
                RegistrationStates.pwd.state,
                RegistrationStates.mail.state,
                ChangePasswordStates.new_password.state,
                AdminStates.delete_account_input.state
            ):
                return
            
            # Вне процесса регистрации - просто удаляем сообщение пользователя без ответа
            try:
                await message.delete()
            except Exception:
                pass
            # Не отправляем никаких ответов - просто удаляем невалидное сообщение

    logger.info("Все полнофункциональные обработчики зарегистрированы")
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
