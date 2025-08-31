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
from logging.handlers import TimedRotatingFileHandler

# Импорты модулей
from src.config.settings import load_config, TOKEN, REDIS_DSN, BOT_VERSION, CONFIG, ADMIN_ID
from src.config.translations import TRANSLATIONS as T
from src.database.connection import get_pool
from src.database.user_operations import (
    get_account_info, delete_account, admin_delete_account,
    register_user, reset_password, change_password
)
from src.utils.middleware import RateLimit
from src.utils.validators import validate_email, validate_nickname, validate_password
from src.keyboards.user_keyboards import kb_main, kb_back
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

def kb_account_list(accounts, selected_email=None):
    """Создаём клавиатуру для списка аккаунтов"""
    buttons = []
    
    for email, username, is_temp, temp_password in accounts:
        text = f"📧 {email} {'✅' if email == selected_email else ''}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"select_account_{email}")])
    
    if selected_email:
        buttons.append([InlineKeyboardButton(text="🔄 Сменить пароль", callback_data="change_password")])
        buttons.append([InlineKeyboardButton(text="🗑 Удалить аккаунт", callback_data=f"delete_account_{selected_email}")])
    
    buttons.append([InlineKeyboardButton(text=T["to_main"], callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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
        await message.answer(T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
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
        if message.from_user.id != ADMIN_ID:
            await message.answer(T["no_access"], reply_markup=kb_back())
            return
        
        await message.answer(T["admin_panel"], reply_markup=kb_admin())
        logger.info(f"Админ панель открыта пользователем {message.from_user.id}")

    # ==================== CALLBACK ОСНОВНЫЕ ====================
    
    @dp.callback_query(F.data == "back_to_main")
    async def cb_back_main(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        try:
            await callback.message.edit_text(T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
        except:
            await callback.message.answer(T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
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
        
        await callback.message.edit_text(text, reply_markup=kb_back())
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
        
        await callback.message.edit_text(text, reply_markup=kb_back())
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
        
        await callback.message.edit_text(text, reply_markup=kb_account_list(accounts) if accounts else kb_back())
        await callback.answer()
        logger.info(f"Просмотр аккаунтов пользователем {callback.from_user.id}")

    @dp.callback_query(F.data.startswith("select_account_"))
    async def cb_select_account(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        email = callback.data.replace("select_account_", "")
        accounts = await get_account_info(pool, callback.from_user.id)
        
        if not accounts:
            await callback.message.edit_text(T["account_no_account"], reply_markup=kb_back())
            await callback.answer()
            return
        
        selected = next((acc for acc in accounts if acc[0] == email), None)
        if not selected:
            await callback.answer("❌ Аккаунт не найден", show_alert=True)
            return
        
        email, username, is_temp, temp_password = selected
        pwd_status = f"🔄 Временный пароль: {temp_password}" if is_temp else "✅ Постоянный пароль"
        text = f"🔑 Ваш аккаунт:\nЛогин: <code>{username}</code>\nE-mail: <code>{email}</code>\nСтатус: {pwd_status}"
        
        await callback.message.edit_text(text, reply_markup=kb_account_list(accounts, selected_email=email))
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
        await callback.answer()

    @dp.message(ChangePasswordStates.new_password)
    async def step_change_password(message: Message, state: FSMContext):
        data = await state.get_data()
        email = data.get("email")
        new_password = message.text.strip()
        
        if new_password in (T["to_main"], T["cancel"]):
            await state.clear()
            await message.answer(T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
            return
        
        if not validate_password(new_password):
            await message.answer(T["err_pwd"])
            return
        
        try:
            await change_password(pool, email, new_password)
            await state.clear()
            await message.answer(T["change_password_success"], reply_markup=kb_main())
        except Exception as e:
            logger.error(f"Ошибка смены пароля: {e}")
            await message.answer("❌ Ошибка при смене пароля")

    @dp.callback_query(F.data.startswith("delete_account_"))
    async def cb_delete_account(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        email = callback.data.replace("delete_account_", "")
        
        try:
            success = await delete_account(pool, callback.from_user.id, email)
            if success:
                await callback.message.edit_text(T["delete_account_success"], reply_markup=kb_back())
            else:
                await callback.message.edit_text(T["delete_account_error"], reply_markup=kb_back())
        except Exception as e:
            logger.error(f"Ошибка удаления аккаунта: {e}")
            await callback.message.edit_text("❌ Ошибка при удалении аккаунта", reply_markup=kb_back())
        
        await callback.answer()

    # ==================== РЕГИСТРАЦИЯ ====================
    
    @dp.callback_query(F.data == "reg_start")
    async def cb_registration_start(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await state.set_state(RegistrationStates.nick)
        text = f"1/3 · {T['progress'][0]}"
        
        try:
            msg = await callback.message.edit_text(text, reply_markup=kb_wizard(0))
            user_wizard_msg[callback.from_user.id] = msg.message_id
        except:
            msg = await callback.message.answer(text, reply_markup=kb_wizard(0))
            user_wizard_msg[callback.from_user.id] = msg.message_id
        
        await callback.answer()

    @dp.callback_query(F.data.in_(["wiz_back", "wiz_cancel"]))
    async def cb_wiz_nav(callback: CallbackQuery, state: FSMContext):
        current_state = await state.get_state()
        
        if callback.data == "wiz_cancel":
            await state.clear()
            await callback.message.edit_text(T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
            await callback.answer()
            return
        
        # Обработка wiz_back
        if current_state == RegistrationStates.nick.state:
            await state.clear()
            await callback.message.edit_text(T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
        elif current_state == RegistrationStates.pwd.state:
            await state.set_state(RegistrationStates.nick)
            text = f"1/3 · {T['progress'][0]}"
            await callback.message.edit_text(text, reply_markup=kb_wizard(0))
        elif current_state == RegistrationStates.mail.state:
            await state.set_state(RegistrationStates.pwd)
            text = f"2/3 · {T['progress'][1]}"
            await callback.message.edit_text(text, reply_markup=kb_wizard(1))
        
        await callback.answer()

    @dp.message(RegistrationStates.nick)
    async def step_nick(message: Message, state: FSMContext):
        nick = message.text.strip()
        
        if not validate_nickname(nick):
            await message.answer(T["err_nick"])
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
        pwd = message.text.strip()
        
        if not validate_password(pwd):
            await message.answer(T["err_pwd"])
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
        email = message.text.strip()
        
        if not validate_email(email):
            await message.answer(T["err_mail"])
            return
        
        data = await state.get_data()
        
        try:
            login, error = await register_user(pool, data["nick"], data["pwd"], email, message.from_user.id)
            await state.clear()
            
            if login:
                await message.answer(T["success"].format(username=login), reply_markup=kb_main())
            else:
                error_msg = T[error].format(max_accounts=CONFIG["settings"]["max_accounts_per_user"])
                await message.answer(error_msg, reply_markup=kb_main())
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            await message.answer(T["err_exists"], reply_markup=kb_main())

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
            
        await callback.message.edit_text(text, reply_markup=kb_admin_back())
        await callback.answer()

    @dp.callback_query(F.data == "admin_delete_account")
    async def cb_admin_delete_account(callback: CallbackQuery, state: FSMContext):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        await state.set_state(AdminStates.delete_account_input)
        await callback.message.edit_text(T["admin_delete_prompt"], reply_markup=kb_admin_back())
        await callback.answer()

    @dp.message(AdminStates.delete_account_input)
    async def step_admin_delete_account(message: Message, state: FSMContext):
        email = message.text.strip()
        
        if not validate_email(email):
            await message.answer("❌ Некорректный e-mail")
            return
        
        try:
            success = await admin_delete_account(pool, email)
            await state.clear()
            
            if success:
                await message.answer(T["admin_delete_success"].format(email=email), reply_markup=kb_admin())
            else:
                await message.answer(T["admin_delete_error"].format(error="Аккаунт не найден"), reply_markup=kb_admin())
        except Exception as e:
            logger.error(f"Ошибка админ удаления: {e}")
            await message.answer(T["admin_delete_error"].format(error=str(e)), reply_markup=kb_admin())

    @dp.callback_query(F.data == "admin_download_log")
    async def cb_admin_download_log(callback: CallbackQuery):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            if os.path.exists("bot.log"):
                await callback.message.answer_document(FSInputFile("bot.log"), reply_markup=kb_admin_back())
            else:
                await callback.message.edit_text("❌ Лог файл не найден", reply_markup=kb_admin_back())
        except Exception as e:
            logger.error(f"Ошибка скачивания лога: {e}")
            await callback.message.edit_text(f"❌ Ошибка: {e}", reply_markup=kb_admin_back())
        
        await callback.answer()

    # Остальные админ функции
    @dp.callback_query(F.data.in_(["admin_broadcast", "admin_reload_config"]))
    async def cb_admin_other_functions(callback: CallbackQuery):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        await callback.answer("🔧 Функция в разработке", show_alert=True)

    @dp.callback_query(F.data == "admin_back")
    async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text(T["admin_panel"], reply_markup=kb_admin())
        await callback.answer()

    @dp.callback_query(F.data == "admin_main")
    async def cb_admin_main(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text(T["start"], reply_markup=kb_main())
        await callback.answer()

    # ==================== ОБЩИЕ ОБРАБОТЧИКИ ====================

    @dp.callback_query()
    async def cb_other(callback: CallbackQuery):
        await callback.answer("🔧 Функция в разработке")
        logger.info(f"Необработанный callback: {callback.data}")

    @dp.message(F.chat.type == ChatType.PRIVATE)
    async def handle_private_messages(message: Message, state: FSMContext):
        current_state = await state.get_state()
        
        # Пропускаем сообщения в состояниях FSM
        if current_state in (
            RegistrationStates.nick.state,
            RegistrationStates.pwd.state,
            RegistrationStates.mail.state,
            ChangePasswordStates.new_password.state,
            AdminStates.delete_account_input.state
        ):
            return
        
        if not message.text.startswith("/"):
            await message.answer("❓ Используйте меню или /start", reply_markup=kb_main())

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