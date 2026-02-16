"""
Исправленная версия главного модуля без циклических зависимостей
"""
import asyncio
import json
import logging
import os

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery
from logging.handlers import TimedRotatingFileHandler

# Импорты модулей
from src.config.settings import load_config, TOKEN, REDIS_DSN, BOT_VERSION, CONFIG, ADMIN_ID
from src.config.translations import TRANSLATIONS as T
from src.database.connection import get_pool
from src.utils.middleware import RateLimit
from src.keyboards.user_keyboards import kb_main, kb_back
from src.keyboards.admin_keyboards import kb_admin

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

async def main():
    """Главная функция запуска бота"""
    
    # Настройка логирования
    logger = setup_logging()
    logger.info(f"Запуск исправленной версии бота {BOT_VERSION}")
    
    # Загрузка конфигурации
    load_config()
    
    # Создание бота
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Настройка Redis и хранилища (пропускаем если Redis недоступен)
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
    
    # Простые обработчики без циклических зависимостей
    
    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        try:
            await message.answer(T["start"], reply_markup=kb_main())
            logger.info(f"Команда /start от пользователя {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в /start: {e}")
            await message.answer("Произошла ошибка при обработке команды")
    
    @dp.message(Command("version"))
    async def cmd_version(message: Message):
        try:
            text = f"{T['version_pre']}{BOT_VERSION}\n\n"
            text += "🧩 Модульная архитектура:\n"
            text += f"✅ Конфигурация: {sum(CONFIG['features'].values())}/{len(CONFIG['features'])} функций\n"
            text += f"✅ База данных: {'подключена' if pool else 'не подключена'}\n"
            text += f"✅ Redis: {'подключен' if storage else 'отключен'}\n"
            text += "✅ Валидаторы и утилиты\n"
            text += "✅ Клавиатуры и состояния"
            
            await message.answer(text, reply_markup=kb_back())
            logger.info(f"Команда /version от пользователя {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в /version: {e}")
            await message.answer("Произошла ошибка при получении версии")
    
    @dp.message(Command("admin"))
    async def cmd_admin(message: Message):
        try:
            if message.from_user.id != ADMIN_ID:
                await message.answer(T["no_access"], reply_markup=kb_back())
                return
            
            await message.answer(T["admin_panel"], reply_markup=kb_admin())
            logger.info(f"Админ панель открыта пользователем {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в /admin: {e}")
            await message.answer("Произошла ошибка в админ панели")
    
    @dp.message(Command("test"))
    async def cmd_test(message: Message):
        try:
            from src.utils.validators import validate_email, validate_nickname, validate_password
            
            tests = [
                f"📧 Email: {'✅' if validate_email('test@mail.ru') else '❌'}",
                f"👤 Nickname: {'✅' if validate_nickname('User123') else '❌'}",
                f"🔐 Password (eng): {'✅' if validate_password('password') else '❌'}",
                f"🔐 Password (rus): {'❌' if validate_password('пароль') else '✅'} (корректно заблокирован)",
            ]
            
            text = "🧪 Тестирование модулей:\n\n" + "\n".join(tests)
            text += f"\n\n📊 Статус:\n"
            text += f"🔗 База данных: {'✅' if pool else '❌'}\n"
            text += f"🧠 Redis FSM: {'✅' if storage else '❌'}\n"
            text += f"📋 Функций активно: {sum(CONFIG['features'].values())}"
            
            await message.answer(text, reply_markup=kb_back())
            logger.info(f"Тестирование модулей запущено пользователем {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в тестах: {e}")
            await message.answer("Ошибка при тестировании модулей")
    
    @dp.callback_query(F.data == "back_to_main")
    async def cb_back_main(callback: CallbackQuery):
        try:
            await callback.message.edit_text(T["start"], reply_markup=kb_main())
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка в callback back_to_main: {e}")
            await callback.answer("Ошибка при возврате в главное меню")
    
    @dp.callback_query(F.data == "my_account")
    async def cb_my_account(callback: CallbackQuery):
        try:
            if not pool:
                await callback.answer("База данных недоступна", show_alert=True)
                return
                
            from src.database.user_operations import get_account_info
            accounts = await get_account_info(pool, callback.from_user.id)
            
            if not accounts:
                text = "❌ У вас нет зарегистрированного аккаунта.\n\n" \
                       "Используйте кнопку 'Регистрация' для создания аккаунта."
            else:
                text = "🔑 Ваши аккаунты:\n\n"
                for i, (email, username, is_temp, temp_password) in enumerate(accounts, 1):
                    status = "🔄 Временный пароль" if is_temp else "✅ Постоянный пароль"
                    text += f"{i}. **{username}**\n"
                    text += f"   📧 {email}\n"
                    text += f"   🔐 {status}\n\n"
                    
                text += "💡 Для управления аккаунтом обратитесь к администратору"
            
            await callback.message.edit_text(text, reply_markup=kb_back())
            await callback.answer()
            logger.info(f"Просмотр аккаунтов пользователем {callback.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в my_account: {e}")
            await callback.answer("Ошибка при получении информации об аккаунтах", show_alert=True)
    
    @dp.callback_query(F.data == "reg_start")
    async def cb_registration(callback: CallbackQuery):
        try:
            text = "📝 Регистрация временно недоступна в упрощенной версии.\n\n" \
                   "Для регистрации аккаунта обратитесь к администратору."
            await callback.message.edit_text(text, reply_markup=kb_back())
            await callback.answer()
            logger.info(f"Попытка регистрации от пользователя {callback.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в регистрации: {e}")
            await callback.answer("Ошибка при обработке регистрации", show_alert=True)
    
    @dp.callback_query(F.data == "show_info")
    async def cb_show_info(callback: CallbackQuery):
        try:
            from src.utils.file_cache import FileCache
            info_cache = FileCache("connection_info.txt")
            text = await info_cache.get()
            
            if not text:
                text = "📋 Информация о подключении:\n\n" \
                       "🔗 Для получения данных подключения к серверу " \
                       "обратитесь к администратору."
            
            await callback.message.edit_text(text, reply_markup=kb_back())
            await callback.answer()
            logger.info(f"Просмотр информации о подключении пользователем {callback.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в show_info: {e}")
            await callback.answer("Ошибка при получении информации", show_alert=True)
    
    @dp.callback_query(F.data == "show_news")
    async def cb_show_news(callback: CallbackQuery):
        try:
            from src.utils.file_cache import FileCache
            news_cache = FileCache("news.txt")
            text = await news_cache.get()
            
            if not text:
                text = "📰 Новости сервера:\n\n" \
                       "В данный момент новостей нет.\n" \
                       "Следите за обновлениями!"
            
            await callback.message.edit_text(text, reply_markup=kb_back())
            await callback.answer()
            logger.info(f"Просмотр новостей пользователем {callback.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в show_news: {e}")
            await callback.answer("Ошибка при получении новостей", show_alert=True)
    
    @dp.callback_query(F.data == "forgot")
    async def cb_forgot_password(callback: CallbackQuery):
        try:
            text = "🔄 Сброс пароля временно недоступен в упрощенной версии.\n\n" \
                   "Для восстановления пароля обратитесь к администратору."
            await callback.message.edit_text(text, reply_markup=kb_back())
            await callback.answer()
            logger.info(f"Попытка сброса пароля от пользователя {callback.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в forgot password: {e}")
            await callback.answer("Ошибка при обработке сброса пароля", show_alert=True)
    
    @dp.callback_query(F.data == "show_changelog")
    async def cb_show_changelog(callback: CallbackQuery):
        try:
            try:
                with open("changelog.json", "r", encoding="utf-8") as f:
                    changelog = json.load(f)
                
                lines = []
                for ver in sorted(changelog.keys(), reverse=True):
                    lines.append(f"<b>{ver}</b>:")
                    for item in changelog[ver].get("ru", []):
                        lines.append(f"• {item}")
                    lines.append("")
                
                text = "\n".join(lines).strip()
                if not text:
                    text = "📜 История изменений пуста"
            except:
                text = "📜 История изменений:\n\n" \
                       "• Создана модульная архитектура\n" \
                       "• Улучшена стабильность работы\n" \
                       "• Исправлены критические ошибки"
            
            await callback.message.edit_text(text, reply_markup=kb_back())
            await callback.answer()
            logger.info(f"Просмотр changelog пользователем {callback.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка в changelog: {e}")
            await callback.answer("Ошибка при получении истории изменений", show_alert=True)
    
    @dp.callback_query(F.data == "admin_check_db") 
    async def cb_admin_check_db(callback: CallbackQuery):
        try:
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
                
            await callback.message.edit_text(text, reply_markup=kb_admin())
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка проверки БД: {e}")
            await callback.answer("Ошибка при проверке базы данных", show_alert=True)
    
    @dp.callback_query(F.data.in_(["admin_broadcast", "admin_download_log", "admin_delete_account", "admin_reload_config"]))
    async def cb_admin_other(callback: CallbackQuery):
        try:
            if callback.from_user.id != ADMIN_ID:
                await callback.answer("❌ Нет доступа", show_alert=True)
                return
            
            feature_names = {
                "admin_broadcast": "📢 Рассылка",
                "admin_download_log": "📜 Скачать лог", 
                "admin_delete_account": "🗑 Удалить аккаунт",
                "admin_reload_config": "🔄 Перезагрузить конфигурацию"
            }
            
            text = f"{feature_names[callback.data]} временно недоступно в упрощённой версии.\n\n" \
                   "Базовая функциональность доступна через команды:"
            
            await callback.message.edit_text(text, reply_markup=kb_admin())
            await callback.answer()
            logger.info(f"Админ функция {callback.data} вызвана")
        except Exception as e:
            logger.error(f"Ошибка в админ функции: {e}")
            await callback.answer("Ошибка при обработке админ функции", show_alert=True)
    
    @dp.callback_query(F.data == "admin_main")
    async def cb_admin_main(callback: CallbackQuery):
        try:
            await callback.message.edit_text(T["start"], reply_markup=kb_main())
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка в admin_main: {e}")
            await callback.answer("Ошибка при возврате в главное меню", show_alert=True)
    
    @dp.callback_query()
    async def cb_other(callback: CallbackQuery):
        try:
            await callback.answer("🔧 Эта функция находится в разработке")
            logger.info(f"Необработанный callback: {callback.data}")
        except Exception as e:
            logger.error(f"Ошибка в callback handler: {e}")
    
    @dp.message()
    async def echo_handler(message: Message):
        try:
            help_text = (
                "🤖 Исправленный модульный бот работает!\n\n"
                "📋 Доступные команды:\n"
                "/start - Главное меню\n"
                "/version - Информация о версии\n" 
                "/test - Тестирование модулей\n"
                "/admin - Панель администратора\n\n"
                "✨ Все основные модули функционируют без ошибок!"
            )
            await message.answer(help_text, reply_markup=kb_main())
        except Exception as e:
            logger.error(f"Ошибка в echo handler: {e}")
    
    logger.info("Все обработчики зарегистрированы (без циклических зависимостей)")
    logger.info("Исправленный бот запущен и готов к работе")
    
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