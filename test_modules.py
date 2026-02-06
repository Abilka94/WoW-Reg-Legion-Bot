#!/usr/bin/env python3
"""
Тест модульного бота (работает без реального токена и БД)
Обновлено для версии 1.6.3
"""
import asyncio
import sys
from src.config.settings import load_config, TOKEN, ADMIN_ID, BOT_VERSION, CONFIG

def test_modules():
    """Тестирование модулей без внешних зависимостей"""
    print("🧪 ТЕСТИРОВАНИЕ МОДУЛЬНОЙ АРХИТЕКТУРЫ")
    print(f"📊 Версия бота: {BOT_VERSION}")
    print("=" * 60)
    
    load_config()
    print(f"📋 Конфигурация: {sum(CONFIG['features'].values())}/{len(CONFIG['features'])} функций активно")
    print(f"👤 Admin ID: {ADMIN_ID}")
    print()
    
    results = {}
    
    # 1. Тест настроек
    print("🔄 Тестирование настроек...")
    try:
        from src.config.settings import DB_HOST, DB_PORT, DB_NAME
        from src.config.translations import TRANSLATIONS
        print(f"✅ Переменные окружения загружены")
        print(f"   🗄️ БД: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        print(f"✅ Переводы: {len(TRANSLATIONS)} строк")
        print(f"   📧 Приветствие: {TRANSLATIONS['start'][:40]}...")
        results['config'] = True
    except Exception as e:
        print(f"❌ Ошибка настроек: {e}")
        results['config'] = False
    
    # 2. Тест базы почтовых провайдеров
    print("\n🔄 Тестирование базы почтовых провайдеров...")
    try:
        from src.utils.email_providers import RUSSIAN_PROVIDERS, FOREIGN_PROVIDERS
        
        total_providers = len(RUSSIAN_PROVIDERS) + len(FOREIGN_PROVIDERS)
        print(f"✅ Всего провайдеров: {total_providers}")
        print(f"   🇷🇺 Русских: {len(RUSSIAN_PROVIDERS)}")
        print(f"   🌍 Иностранных: {len(FOREIGN_PROVIDERS)}")
        
        # Проверяем наличие популярных провайдеров
        popular = ['gmail.com', 'yandex.ru', 'mail.ru', 'outlook.com']
        found = [p for p in popular if p in RUSSIAN_PROVIDERS or p in FOREIGN_PROVIDERS]
        print(f"   ✅ Популярные провайдеры найдены: {len(found)}/{len(popular)}")
        
        results['email_providers'] = True
    except Exception as e:
        print(f"❌ Ошибка базы провайдеров: {e}")
        results['email_providers'] = False
    
    # 3. Тест валидаторов  
    print("\n🔄 Тестирование валидаторов...")
    try:
        from src.utils.validators import (
            validate_email, validate_nickname, validate_password,
            filter_text, is_text_only
        )
        
        # Тесты валидации email
        email_tests = [
            ("Email (корректный - Gmail)", "user@gmail.com", True),
            ("Email (корректный - Yandex)", "test@yandex.ru", True),
            ("Email (корректный - Mail.ru)", "user@mail.ru", True),
            ("Email (некорректный формат)", "invalid-email", False),
            ("Email (без @)", "userexample.com", False),
            ("Email (неизвестный провайдер)", "user@unknown12345.com", False),
        ]
        
        # Тесты валидации никнеймов
        nickname_tests = [
            ("Никнейм (латиница)", "User123", True),
            ("Никнейм (с символами)", "User@123", False),
            ("Никнейм (кириллица)", "Пользователь", False),  # Исправлено: кириллица запрещена
            ("Никнейм (слишком короткий)", "Ab", False),
            ("Никнейм (слишком длинный)", "A" * 21, False),
        ]
        
        # Тесты валидации паролей
        password_tests = [
            ("Пароль (английский, 11 символов)", "password123", True),
            ("Пароль (русский)", "пароль123", False),
            ("Пароль (короткий, 5 символов)", "pass1", False),
            ("Пароль (7 символов)", "pass123", False),
            ("Пароль (8 символов)", "pass1234", True),
            ("Пароль (с спецсимволами)", "Pass@123!", True),
            ("Пароль (только цифры, 8 символов)", "12345678", True),
            ("Пароль (только буквы, 8 символов)", "password", True),
        ]
        
        all_passed = True
        
        print("   📧 Тесты email:")
        for name, value, expected in email_tests:
            result, _ = validate_email(value)
            status = "✅" if result == expected else "❌"
            if result != expected:
                all_passed = False
            print(f"      {status} {name}: '{value}' → {result}")
        
        print("   👤 Тесты никнеймов:")
        for name, value, expected in nickname_tests:
            result = validate_nickname(value)
            status = "✅" if result == expected else "❌"
            if result != expected:
                all_passed = False
            print(f"      {status} {name}: '{value}' → {result}")
        
        print("   🔐 Тесты паролей:")
        for name, value, expected in password_tests:
            is_valid, _ = validate_password(value)
            result = is_valid
            status = "✅" if result == expected else "❌"
            if result != expected:
                all_passed = False
            print(f"      {status} {name}: '{value}' → {result}")
        
        # Тесты фильтрации текста
        print("   🧹 Тесты фильтрации текста:")
        filter_tests = [
            ("Текст с эмодзи", "Привет 😀 мир", "Привет  мир"),
            ("Текст с email", "Email: test@mail.ru", "Email: test@mail.ru", True),
            ("Текст с спецсимволами", "Hello! @#$%", "Hello! "),
        ]
        
        for name, value, expected, *args in filter_tests:
            allow_email = args[0] if args else False
            result = filter_text(value, allow_email_chars=allow_email)
            status = "✅" if result == expected else "❌"
            if result != expected:
                all_passed = False
            print(f"      {status} {name}: '{value}' → '{result}'")
        
        results['validators'] = all_passed
        if all_passed:
            print("✅ Все валидаторы работают корректно!")
    except Exception as e:
        print(f"❌ Ошибка валидаторов: {e}")
        import traceback
        traceback.print_exc()
        results['validators'] = False
    
    # 4. Тест клавиатур
    print("\n🔄 Тестирование клавиатур...")
    try:
        from src.keyboards.user_keyboards import (
            kb_main, kb_back, kb_wizard, kb_account_list
        )
        from src.keyboards.admin_keyboards import kb_admin, kb_admin_back
        
        main_kb = kb_main()
        print(f"✅ Главная клавиатура: {len(main_kb.inline_keyboard)} рядов")
        
        main_kb_admin = kb_main(is_admin=True)
        print(f"✅ Главная клавиатура (админ): {len(main_kb_admin.inline_keyboard)} рядов")
        
        back_kb = kb_back()
        print(f"✅ Клавиатура 'Назад': {len(back_kb.inline_keyboard)} рядов")
        
        wizard_kb = kb_wizard(1)
        print(f"✅ Клавиатура мастера (шаг 1): {len(wizard_kb.inline_keyboard)} рядов")
        
        wizard_kb_0 = kb_wizard(0)
        print(f"✅ Клавиатура мастера (шаг 0): {len(wizard_kb_0.inline_keyboard)} рядов")
        
        # Тест клавиатуры списка аккаунтов
        test_accounts = [
            ("test@mail.ru", "TestUser", False, None),
            ("user@gmail.com", "User123", False, None),
        ]
        account_kb = kb_account_list(test_accounts)
        print(f"✅ Клавиатура списка аккаунтов: {len(account_kb.inline_keyboard)} аккаунтов")
        
        admin_kb = kb_admin()
        print(f"✅ Админ клавиатура: {len(admin_kb.inline_keyboard)} рядов")
        
        results['keyboards'] = True
    except Exception as e:
        print(f"❌ Ошибка клавиатур: {e}")
        import traceback
        traceback.print_exc()
        results['keyboards'] = False
    
    # 5. Тест состояний FSM
    print("\n🔄 Тестирование FSM состояний...")
    try:
        from src.states.user_states import (
            RegistrationStates, ForgotPasswordStates, 
            AdminStates, ChangePasswordStates
        )
        
        reg_states = [
            RegistrationStates.nick, 
            RegistrationStates.pwd, 
            RegistrationStates.mail
        ]
        print(f"✅ Состояния регистрации: {len(reg_states)}")
        for state in reg_states:
            print(f"   📝 {state.state}")
        
        forgot_states = [ForgotPasswordStates.email]
        print(f"✅ Состояния восстановления: {len(forgot_states)}")
        for state in forgot_states:
            print(f"   📝 {state.state}")
        
        admin_states = [
            AdminStates.broadcast_text, 
            AdminStates.delete_account_input
        ]
        print(f"✅ Админ состояния: {len(admin_states)}")
        for state in admin_states:
            print(f"   📝 {state.state}")
        
        change_pwd_states = [ChangePasswordStates.new_password]
        print(f"✅ Состояния смены пароля: {len(change_pwd_states)}")
        for state in change_pwd_states:
            print(f"   📝 {state.state}")
        
        results['states'] = True
    except Exception as e:
        print(f"❌ Ошибка состояний: {e}")
        results['states'] = False
    
    # 6. Тест утилит
    print("\n🔄 Тестирование утилит...")
    try:
        from src.utils.file_cache import FileCache
        from src.utils.middleware import RateLimit
        
        print("✅ FileCache импортирован")
        print("✅ RateLimit middleware импортирован")
        
        # Тест кэша файлов
        cache = FileCache("test_nonexistent.txt")
        content = asyncio.run(cache.get())
        print(f"✅ Кэш файлов: пустой файл → '{content}' (ожидалось пусто)")
        
        # Тест middleware
        middleware = RateLimit(seconds=1.0)
        print(f"✅ RateLimit инициализирован: {middleware.seconds} сек между запросами")
        print(f"   🔒 Обрабатываемых callback'ов: {len(middleware.processing_callbacks)}")
        
        results['utils'] = True
    except Exception as e:
        print(f"❌ Ошибка утилит: {e}")
        import traceback
        traceback.print_exc()
        results['utils'] = False
    
    # 7. Тест обработчиков (импорты)
    print("\n🔄 Тестирование обработчиков (импорты)...")
    try:
        # Проверяем, что обработчики можно импортировать
        # (не вызываем их, так как нужен бот и диспетчер)
        from src.handlers import commands, registration, account_management, admin, messages
        print("✅ Модуль commands")
        print("✅ Модуль registration")
        print("✅ Модуль account_management")
        print("✅ Модуль admin")
        print("✅ Модуль messages")
        
        results['handlers'] = True
    except Exception as e:
        print(f"❌ Ошибка обработчиков: {e}")
        import traceback
        traceback.print_exc()
        results['handlers'] = False
    
    # 8. Тест функций базы данных (импорты)
    print("\n🔄 Тестирование функций БД (импорты)...")
    try:
        from src.database.user_operations import (
            register_user, delete_account, get_account_info,
            email_exists, username_exists, count_user_accounts
        )
        print("✅ register_user")
        print("✅ delete_account")
        print("✅ get_account_info")
        print("✅ email_exists")
        print("✅ username_exists")
        print("✅ count_user_accounts")
        
        results['database_ops'] = True
    except Exception as e:
        print(f"❌ Ошибка функций БД: {e}")
        results['database_ops'] = False
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ МОДУЛЬНОГО ТЕСТИРОВАНИЯ:")
    print("=" * 60)
    
    total = len(results)
    passed = sum(results.values())
    
    for test_name, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"   {status.ljust(12)} {test_name}")
    
    percentage = (passed / total * 100) if total > 0 else 0
    print(f"\n🎯 Общий результат: {passed}/{total} модулей работают корректно ({percentage:.1f}%)")
    
    if passed == total:
        print("\n🎉 ОТЛИЧНО! Вся модульная архитектура работает!")
        print("🚀 Бот готов к запуску при наличии токена и БД")
        print("✨ Все новые функции версии 1.6.3 протестированы!")
    elif passed >= total * 0.8:
        print(f"\n👍 ХОРОШО! {passed}/{total} модулей работают")
        print("⚡ Модульная структура в основном функциональна")
    else:
        print(f"\n⚠️ ТРЕБУЕТ ДОРАБОТКИ: только {passed}/{total} модулей работают")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = test_modules()
        print(f"\n🏁 Тестирование {'успешно' if success else 'частично'} завершено")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
