"""
Конфигурация и настройки VK-бота
"""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_GROUP_ID = int(os.getenv("VK_GROUP_ID", "0"))
ADMIN_ID = int(os.getenv("VK_ADMIN_ID", "0"))

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3310"))
DB_USER = os.getenv("DB_USER", "spp_user")
DB_PASS = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "legion_auth")
REDIS_DSN = os.getenv("REDIS_DSN", "redis://127.0.0.1:6379/0")

BOT_VERSION = "0.0.1 (1) (alpha)"

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

CONFIG = DEFAULT_CONFIG.copy()


def load_config():
    """Загружает конфигурацию из config.json."""
    global CONFIG
    try:
        if os.path.exists("config.json"):
            with open("config.json", encoding="utf-8") as f:
                CONFIG = json.load(f)
            logging.info("Конфигурация загружена из config.json")
        else:
            logging.warning("config.json не найден, используются настройки по умолчанию")
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка чтения config.json: {e}")
    except Exception as e:
        logging.error(f"Ошибка загрузки config.json: {e}")
