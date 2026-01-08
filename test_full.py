#!/usr/bin/env python3
"""
Расширенный тест модульного бота с реальными данными
"""
import asyncio
import sys
import traceback
from src.config.settings import load_config, TOKEN, ADMIN_ID, DB_HOST, DB_PORT, DB_NAME, BOT_VERSION, CONFIG
from src.database.connection import get_pool

async def test_database_connection():
    """Тестирование подключения к базе данных"""
    print("🔄 Тестирование подключения к базе данных...")
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT 1 as test')
                result = await cur.fetchone()
                print(f"✅ Подключение к MySQL успешно! Результат: {result}")
                
                # Проверяем существование таблиц
                await cur.execute("SHOW TABLES")
                tables = await cur.fetchall()
                print(f"📋 Найдено таблиц в БД: {len(tables)}")
                for table in tables:
                    print(f"   📄 {table[0]}")
                
        pool.close()
        await pool.wait_closed()
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        traceback.print_exc()
        return False

async def test_bot_token():
    """Тестирование токена бота"""
    print("🔄 Проверка токена бота...")
    
    if TOKEN in ["YOUR_BOT_TOKEN", "TEST_TOKEN_NOT_REAL"]:
        print("⚠️ Токен не настроен - используется тестовое значение")
        return False
    
    try:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        
        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Пробуем получить информацию о боте
        me = await bot.get_me()
        print(f"✅ Бот активен: @{me.username} ({me.first_name})")
        print(f"   🆔 Bot ID: {me.id}")
        print(f"   🔧 Can join groups: {me.can_join_groups}")
        
        await bot.session.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка при проверке токена: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print(f"🧪 РАСШИРЕННОЕ ТЕСТИРОВАНИЕ МОДУЛЬНОГО БОТА")
    print(f"📊 Версия: {BOT_VERSION}")
    print("=" * 50)
    
    # Загружаем конфигурацию
    load_config()
    print(f"📋 Конфигурация загружена: {sum(CONFIG['features'].values())}/{len(CONFIG['features'])} функций активно")
    
    # Проверяем настройки
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"🗄️ База данных: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print()
    
    # Тестируем компоненты
    results = {}
    
    # 1. Тест токена
    results['bot_token'] = await test_bot_token()
    print()
    
    # 2. Тест БД
    results['database'] = await test_database_connection()
    print()
    
    # 3. Тест модулей (синхронные тесты)
    print("🔄 Тестирование модулей...")
    
    try:
        from src.utils.validators import validate_email, validate_nickname, validate_password
        print("✅ Валидаторы загружены")
        
        # Тесты валидации
        test_cases = [
            ("email", "user@domain.com", validate_email, True),
            ("nickname", "TestUser123", validate_nickname, True), 
            ("password_rus", "пароль123", validate_password, False),  # Должно быть False
            ("password_eng", "password123", validate_password, True)
        ]
        
        for test_name, value, validator, expected in test_cases:
            result = validator(value)
            status = "✅" if result == expected else "❌"
            print(f"   {status} {test_name}: {value} → {result} (ожидалось: {expected})")
        
        results['validators'] = True
    except Exception as e:
        print(f"❌ Ошибка в валидаторах: {e}")
        results['validators'] = False
    
    try:
        from src.keyboards.user_keyboards import kb_main
        kb = kb_main()
        print(f"✅ Клавиатуры: {len(kb.inline_keyboard)} рядов кнопок")
        results['keyboards'] = True
    except Exception as e:
        print(f"❌ Ошибка в клавиатурах: {e}")
        results['keyboards'] = False
    
    try:
        from src.states.user_states import RegistrationStates
        states = [RegistrationStates.nick, RegistrationStates.pwd, RegistrationStates.mail]
        print(f"✅ FSM состояния: {len(states)} состояний регистрации")
        results['states'] = True
    except Exception as e:
        print(f"❌ Ошибка в состояниях: {e}")
        results['states'] = False
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ:")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Результат: {passed_tests}/{total_tests} тестов пройдено")
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Модульный бот готов к работе!")
    elif results['bot_token'] and results['database']:
        print("🚀 Бот готов к запуску! (некоторые модули требуют доработки)")
    else:
        print("⚠️ Требуется настройка токена и/или базы данных")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        traceback.print_exc()
        sys.exit(1)