"""
Конфигурация и настройки бота
"""

import os
import json
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Основные настройки
TOKEN = os.getenv("TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3310"))
DB_USER = os.getenv("DB_USER", "spp_user")
DB_PASS = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "legion_auth")
REDIS_DSN = os.getenv("REDIS_DSN", "redis://127.0.0.1:6379/0")
BOT_VERSION = "1.7.1"

# Конфигурация по умолчанию
DEFAULT_CONFIG = {
    "features": {
        "registration": True,
        "password_reset": True,
        "account_management": True,
        "admin_panel": True,
        "admin_broadcast": True,
        "admin_check_db": True,
        "admin_delete_account": True,
        "admin_reload_config": True,
    },
    "settings": {"max_accounts_per_user": 3},
}

# Глобальная переменная конфигурации
CONFIG = DEFAULT_CONFIG.copy()


def load_config():
    """Загружает конфигурацию из config.json или возвращает значения по умолчанию."""
    global CONFIG
    try:
        if os.path.exists("config.json"):
            with open("config.json", encoding="utf-8") as f:
                CONFIG = json.load(f)
            logging.info("Конфигурация успешно загружена из config.json")
        else:
            logging.warning(
                "Файл config.json не найден, используются настройки по умолчанию"
            )
    except json.JSONDecodeError as e:
        logging.error(
            f"Ошибка чтения config.json: {e}, используются настройки по умолчанию"
        )
    except Exception as e:
        logging.error(
            f"Неизвестная ошибка при загрузке config.json: {e}, используются настройки по умолчанию"
        )


async def reload_config(bot):
    """Перезагружает конфигурацию и уведомляет администратора."""
    from ..utils.notifications import notify_admin, delete_all_bot_messages

    global CONFIG
    old_config = CONFIG.copy()
    load_config()

    changes = []
    for key in old_config["features"]:
        if old_config["features"][key] != CONFIG["features"][key]:
            status = "включена" if CONFIG["features"][key] else "отключена"
            changes.append(f"Функция {key} {status}")

    if (
        old_config["settings"]["max_accounts_per_user"]
        != CONFIG["settings"]["max_accounts_per_user"]
    ):
        changes.append(
            f"Лимит аккаунтов изменён на {CONFIG['settings']['max_accounts_per_user']}"
        )

    if changes:
        change_text = "\n".join(changes)
        logging.info(f"Конфигурация перезагружена:\n{change_text}")
        await delete_all_bot_messages(ADMIN_ID, bot)
        await notify_admin(bot, f"Конфигурация перезагружена:\n{change_text}")
    else:
        logging.info("Конфигурация перезагружена: изменений нет")
        await delete_all_bot_messages(ADMIN_ID, bot)
        await notify_admin(bot, "Конфигурация перезагружена: изменений нет")

    return True
