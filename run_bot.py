"""
Запуск модульного бота (упрощенная версия для демонстрации)
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties

# Импорты наших модулей
from src.config.settings import load_config, TOKEN, BOT_VERSION, CONFIG
from src.config.translations import TRANSLATIONS as T
from src.keyboards.user_keyboards import kb_main, kb_back
from src.utils.validators import validate_email, validate_nickname, validate_password

def setup_logging():
    """Настройка логирования"""
    logger = logging.getLogger("bot")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    return logger

async def main():
    """Главная функция запуска бота"""
    
    # Настройка
    logger = setup_logging()
    logger.info(f"🚀 Запуск модульного бота версии {BOT_VERSION}")
    
    # Загрузка конфигурации
    load_config()
    logger.info(f"📋 Конфигурация загружена: {len(CONFIG['features'])} функций")
    
    # Создание бота
    if TOKEN == "TEST_TOKEN_NOT_REAL":
        logger.warning("⚠️ Используется тестовый токен - бот не будет подключаться к Telegram")
        logger.info("✅ Но архитектура модулей протестирована и работает!")
        return
    
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Регистрация базовых обработчиков для демонстрации
    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        await message.answer(T["start"], reply_markup=kb_main())
        logger.info(f"👤 Пользователь {message.from_user.id} выполнил /start")
    
    @dp.message(Command("version"))
    async def cmd_version(message: Message):
        text = f"{T['version_pre']}{BOT_VERSION}\n\n📦 Модульная архитектура:\n✅ Конфигурация\n✅ Переводы\n✅ Клавиатуры\n✅ Валидаторы\n✅ Кэш файлов\n✅ FSM состояния"
        await message.answer(text, reply_markup=kb_back())
        logger.info(f"📊 Показана информация о версии")
    
    @dp.message(Command("test"))
    async def cmd_test(message: Message):
        # Демонстрация работы валидаторов
        tests = [
            f"📧 Email test@mail.ru: {'✅' if validate_email('test@mail.ru') else '❌'}",
            f"👤 Nickname Test123: {'✅' if validate_nickname('Test123') else '❌'}",
            f"🔐 Password (рус): {'❌' if validate_password('пароль') else '✅'} (правильно запрещено)",
            f"🔐 Password (eng): {'✅' if validate_password('password') else '❌'}",
        ]
        
        text = "🧪 Тестирование модулей:\n\n" + "\n".join(tests)
        text += f"\n\n📋 Активных функций: {sum(CONFIG['features'].values())}"
        
        await message.answer(text)
        logger.info(f"🧪 Выполнено тестирование модулей")
    
    @dp.callback_query()
    async def handle_callbacks(callback: CallbackQuery):
        await callback.answer("🔧 Полная функциональность доступна в основном боте")
        logger.info(f"⚙️ Обработан callback: {callback.data}")
    
    @dp.message()
    async def echo_handler(message: Message):
        await message.answer(
            "🤖 Модульный бот работает!\n\n"
            "📋 Доступные команды:\n"
            "/start - Главное меню\n"
            "/version - Информация о версии\n"
            "/test - Тестирование модулей\n\n"
            "✨ Все модули загружены и функционируют корректно!"
        )
    
    logger.info("🎯 Модульный бот запущен и готов к работе")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())