#!/usr/bin/env python3
"""
Расширенный тест модульного бота с реальными данными
Обновлено для версии 1.6.2
"""
import asyncio
import sys
import traceback
from src.config.settings import (
    load_config, TOKEN, ADMIN_ID, DB_HOST, DB_PORT, 
    DB_NAME, DB_USER, DB_PASS, BOT_VERSION, CONFIG
)
from src.database.connection import get_pool

async def test_database_connection():
    """Тестирование подключения к базе данных"""
    print("🔄 Тестирование подключения к базе данных...")
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Простой тест подключения
                await cur.execute('SELECT 1 as test')
                result = await cur.fetchone()
                print(f"✅ Подключение к MySQL успешно! Результат: {result}")
                
                # Проверяем существование таблиц
                await cur.execute("SHOW TABLES")
                tables = await cur.fetchall()
                print(f"📋 Найдено таблиц в БД: {len(tables)}")
                for table in tables:
                    print(f"   📄 {table[0]}")
                
                # Проверяем структуру таблицы account (если существует)
                try:
                    await cur.execute("DESCRIBE account")
                    columns = await cur.fetchall()
                    print(f"\n   📊 Структура таблицы 'account':")
                    for col in columns:
                        print(f"      • {col[0]} ({col[1]})")
                except Exception as e:
                    print(f"   ⚠️ Не удалось получить структуру таблицы 'account': {e}")
                
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
    
    if TOKEN in ["YOUR_BOT_TOKEN", "TEST_TOKEN_NOT_REAL", "YOUR_BOT_TOKEN"]:
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
        print(f"   📝 Can read all group messages: {me.can_read_all_group_messages}")
        
        await bot.session.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка при проверке токена: {e}")
        return False

async def test_email_validation():
    """Тестирование улучшенной валидации email"""
    print("\n🔄 Тестирование улучшенной валидации email...")
    try:
        from src.utils.validators import validate_email
        from src.utils.email_providers import RUSSIAN_PROVIDERS, FOREIGN_PROVIDERS
        
        # Тесты с реальными провайдерами
        test_cases = [
            # Корректные email
            ("gmail.com", "test@gmail.com", True),
            ("yandex.ru", "user@yandex.ru", True),
            ("mail.ru", "test@mail.ru", True),
            ("outlook.com", "user@outlook.com", True),
            # Некорректные
            ("неизвестный провайдер", "test@unknown12345xyz.com", False),
            ("неверный формат", "invalid-email", False),
            ("без @", "userexample.com", False),
        ]
        
        all_passed = True
        for name, email, expected in test_cases:
            result, message = validate_email(email)
            status = "✅" if result == expected else "❌"
            if result != expected:
                all_passed = False
            print(f"   {status} {name}: {email} → {result} ({message[:30] if message else 'OK'})")
        
        return all_passed
    except Exception as e:
        print(f"❌ Ошибка в валидации email: {e}")
        return False

async def test_database_operations():
    """Тестирование операций с базой данных (без реальных изменений)"""
    print("\n🔄 Тестирование операций с БД...")
    try:
        from src.database.user_operations import (
            email_exists, username_exists, count_user_accounts
        )
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Тест проверки существования email (без реального запроса)
            print("✅ Функция email_exists доступна")
            
            # Тест проверки существования username
            print("✅ Функция username_exists доступна")
            
            # Тест подсчета аккаунтов
            print("✅ Функция count_user_accounts доступна")
            
        pool.close()
        await pool.wait_closed()
        return True
    except Exception as e:
        print(f"❌ Ошибка в операциях БД: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print("🧪 РАСШИРЕННОЕ ТЕСТИРОВАНИЕ МОДУЛЬНОГО БОТА")
    print(f"📊 Версия: {BOT_VERSION}")
    print("=" * 60)
    
    # Загружаем конфигурацию
    load_config()
    print(f"📋 Конфигурация загружена: {sum(CONFIG['features'].values())}/{len(CONFIG['features'])} функций активно")
    
    # Проверяем настройки
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"🗄️ База данных: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"👤 DB User: {DB_USER}")
    print()
    
    # Тестируем компоненты
    results = {}
    
    # 1. Тест токена
    results['bot_token'] = await test_bot_token()
    print()
    
    # 2. Тест БД
    results['database'] = await test_database_connection()
    print()
    
    # 3. Тест улучшенной валидации email
    results['email_validation'] = await test_email_validation()
    print()
    
    # 4. Тест операций БД
    results['database_operations'] = await test_database_operations()
    print()
    
    # 5. Тест модулей (синхронные тесты)
    print("🔄 Тестирование модулей...")
    
    try:
        from src.utils.validators import validate_email, validate_nickname, validate_password, filter_text
        print("✅ Валидаторы загружены")
        
        # Тесты валидации
        test_cases = [
            ("email (gmail)", "user@gmail.com", validate_email, True),
            ("email (yandex)", "test@yandex.ru", validate_email, True),
            ("email (неизвестный)", "user@unknown12345.com", validate_email, False),
            ("nickname", "TestUser123", validate_nickname, True),
            ("nickname (короткий)", "Ab", validate_nickname, False),
            ("password_rus", "пароль123", validate_password, False),
            ("password_eng", "password123", validate_password, True),
            ("password (короткий)", "pass1", validate_password, False),
        ]
        
        all_passed = True
        for test_name, value, validator, expected in test_cases:
            if validator == validate_email:
                result, _ = validator(value)
            else:
                result = validator(value)
            status = "✅" if result == expected else "❌"
            if result != expected:
                all_passed = False
            print(f"   {status} {test_name}: {value} → {result} (ожидалось: {expected})")
        
        # Тест фильтрации текста
        filtered = filter_text("Привет 😀 мир! @#$%", allow_email_chars=False)
        print(f"   ✅ Фильтрация текста: 'Привет 😀 мир! @#$%' → '{filtered}'")
        
        results['validators'] = all_passed
    except Exception as e:
        print(f"❌ Ошибка в валидаторах: {e}")
        traceback.print_exc()
        results['validators'] = False
    
    try:
        from src.keyboards.user_keyboards import kb_main, kb_account_list
        kb = kb_main()
        print(f"✅ Клавиатуры: {len(kb.inline_keyboard)} рядов кнопок")
        
        # Тест клавиатуры списка аккаунтов
        test_accounts = [("test@mail.ru", "TestUser", False, None)]
        account_kb = kb_account_list(test_accounts)
        print(f"✅ Клавиатура списка аккаунтов работает")
        
        results['keyboards'] = True
    except Exception as e:
        print(f"❌ Ошибка в клавиатурах: {e}")
        results['keyboards'] = False
    
    try:
        from src.states.user_states import RegistrationStates, ChangePasswordStates
        states = [
            RegistrationStates.nick, 
            RegistrationStates.pwd, 
            RegistrationStates.mail
        ]
        print(f"✅ FSM состояния: {len(states)} состояний регистрации")
        print(f"✅ Состояния смены пароля: {ChangePasswordStates.new_password}")
        results['states'] = True
    except Exception as e:
        print(f"❌ Ошибка в состояниях: {e}")
        results['states'] = False
    
    try:
        from src.utils.middleware import RateLimit
        middleware = RateLimit(seconds=1.0)
        print(f"✅ Middleware RateLimit: {middleware.seconds} сек между запросами")
        results['middleware'] = True
    except Exception as e:
        print(f"❌ Ошибка в middleware: {e}")
        results['middleware'] = False
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ:")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    percentage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status.ljust(10)} {test_name}")
    
    print(f"\n🎯 Результат: {passed_tests}/{total_tests} тестов пройдено ({percentage:.1f}%)")
    
    if passed_tests == total_tests:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Модульный бот готов к работе!")
        print("✨ Все функции версии 1.6.2 работают корректно!")
    elif results.get('bot_token') and results.get('database'):
        print("\n🚀 Бот готов к запуску! (некоторые модули требуют доработки)")
    elif results.get('database'):
        print("\n⚠️ База данных работает, но требуется настройка токена")
    elif results.get('bot_token'):
        print("\n⚠️ Токен работает, но требуется настройка базы данных")
    else:
        print("\n⚠️ Требуется настройка токена и/или базы данных")
    
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
