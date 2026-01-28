#!/usr/bin/env python3
"""
Быстрая проверка версии бота
"""
from src.config.settings import BOT_VERSION, load_config
import json

def check_version():
    """Проверяет текущую версию и changelog"""
    print(f"🤖 Версия бота: {BOT_VERSION}")
    
    # Проверяем changelog
    try:
        with open("changelog.json", "r", encoding="utf-8") as f:
            changelog = json.load(f)
        
        # Получаем базовую версию (без +XX)
        base_version = BOT_VERSION.split('+')[0]
        
        if base_version in changelog:
            print(f"📝 Changelog для версии {base_version}:")
            for change in changelog[base_version]["ru"]:
                print(f"   ✅ {change}")
        else:
            print(f"⚠️ Changelog для версии {base_version} не найден")
            
    except Exception as e:
        print(f"❌ Ошибка чтения changelog: {e}")
    
    # Проверяем конфигурацию
    load_config()
    print(f"\n🔧 Конфигурация загружена успешно")

if __name__ == "__main__":
    check_version()