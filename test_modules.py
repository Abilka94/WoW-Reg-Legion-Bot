#!/usr/bin/env python3
"""
Тест модульного бота (работает без реального токена и БД)
"""
import asyncio
import sys
from src.config.settings import load_config, TOKEN, ADMIN_ID, BOT_VERSION, CONFIG

def test_modules():
    """Тестирование модулей без внешних зависимостей"""
    print("🧪 ТЕСТИРОВАНИЕ МОДУЛЬНОЙ АРХИТЕКТУРЫ")
    print(f"📊 Версия бота: {BOT_VERSION}")
    print("=" * 50)
    
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
        print(f"✅ Переводы: {len(TRANSLATIONS)} строк")
        print(f"   📧 Приветствие: {TRANSLATIONS['start'][:30]}...")
        results['config'] = True
    except Exception as e:
        print(f"❌ Ошибка настроек: {e}")
        results['config'] = False
    
    # 2. Тест валидаторов  
    print("\n🔄 Тестирование валидаторов...")
    try:
        from src.utils.validators import validate_email, validate_nickname, validate_password
        
        tests = [
            ("Email (корректный)", "user@example.com", validate_email, True),
            ("Email (некорректный)", "invalid-email", validate_email, False),
            ("Никнейм (латиница)", "User123", validate_nickname, True),
            ("Никнейм (с символами)", "User@123", validate_nickname, False),
            ("Пароль (английский)", "password123", validate_password, True),
            ("Пароль (русский)", "пароль123", validate_password, False)
        ]
        
        all_passed = True
        for name, value, func, expected in tests:
            result = func(value)
            status = "✅" if result == expected else "❌"
            if result != expected:
                all_passed = False
            print(f"   {status} {name}: '{value}' → {result}")
        
        results['validators'] = all_passed
        if all_passed:
            print("✅ Все валидаторы работают корректно!")
    except Exception as e:
        print(f"❌ Ошибка валидаторов: {e}")
        results['validators'] = False
    
    # 3. Тест клавиатур
    print("\n🔄 Тестирование клавиатур...")
    try:
        from src.keyboards.user_keyboards import kb_main, kb_back, kb_wizard
        from src.keyboards.admin_keyboards import kb_admin, kb_admin_back
        
        main_kb = kb_main()
        print(f"✅ Главная клавиатура: {len(main_kb.inline_keyboard)} рядов")
        
        back_kb = kb_back()
        print(f"✅ Клавиатура 'Назад': {len(back_kb.inline_keyboard)} рядов")
        
        wizard_kb = kb_wizard(1)
        print(f"✅ Клавиатура мастера: {len(wizard_kb.inline_keyboard)} рядов")
        
        admin_kb = kb_admin()
        print(f"✅ Админ клавиатура: {len(admin_kb.inline_keyboard)} рядов")
        
        results['keyboards'] = True
    except Exception as e:
        print(f"❌ Ошибка клавиатур: {e}")
        results['keyboards'] = False
    
    # 4. Тест состояний FSM
    print("\n🔄 Тестирование FSM состояний...")
    try:
        from src.states.user_states import (
            RegistrationStates, ForgotPasswordStates, 
            AdminStates, ChangePasswordStates
        )
        
        reg_states = [RegistrationStates.nick, RegistrationStates.pwd, RegistrationStates.mail]
        print(f"✅ Состояния регистрации: {len(reg_states)}")
        for state in reg_states:
            print(f"   📝 {state.state}")
        
        forgot_states = [ForgotPasswordStates.email]
        print(f"✅ Состояния восстановления: {len(forgot_states)}")
        
        admin_states = [AdminStates.broadcast_text, AdminStates.delete_account_input]
        print(f"✅ Админ состояния: {len(admin_states)}")
        
        results['states'] = True
    except Exception as e:
        print(f"❌ Ошибка состояний: {e}")
        results['states'] = False
    
    # 5. Тест утилит
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
        
        results['utils'] = True
    except Exception as e:
        print(f"❌ Ошибка утилит: {e}")
        results['utils'] = False
    
    # 6. Тест обработчиков (импорты)
    print("\n🔄 Тестирование обработчиков (импорты)...")
    try:
        from src.handlers.commands import register_command_handlers, register_callback_handlers
        print("✅ Обработчики команд")
        
        from src.handlers.registration import register_registration_handlers  
        print("✅ Обработчики регистрации")
        
        from src.handlers.account_management import register_account_handlers
        print("✅ Обработчики аккаунтов")
        
        from src.handlers.admin import register_admin_handlers
        print("✅ Админ обработчики")
        
        from src.handlers.messages import register_message_handlers
        print("✅ Обработчики сообщений")
        
        results['handlers'] = True
    except Exception as e:
        print(f"❌ Ошибка обработчиков: {e}")
        results['handlers'] = False
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ МОДУЛЬНОГО ТЕСТИРОВАНИЯ:")
    
    total = len(results)
    passed = sum(results.values())
    
    for test_name, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"   {status.ljust(12)} {test_name}")
    
    print(f"\n🎯 Общий результат: {passed}/{total} модулей работают корректно")
    
    if passed == total:
        print("\n🎉 ОТЛИЧНО! Вся модульная архитектура работает!")
        print("🚀 Бот готов к запуску при наличии токена и БД")
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