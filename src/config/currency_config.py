"""
Конфигурация валютного магазина
"""
import json
import logging
import os

logger = logging.getLogger("bot")

def load_currency_shop_config():
    """Загружает конфигурацию валютного магазина"""
    config_path = "currency_shop_config.json"
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info("Конфигурация валютного магазина загружена")
            return config
        else:
            logger.warning(f"Файл конфигурации {config_path} не найден")
            return get_default_currency_config()
    except Exception as e:
        logger.error(f"Ошибка загрузки конфигурации валютного магазина: {e}")
        return get_default_currency_config()

def get_default_currency_config():
    """Возвращает конфигурацию по умолчанию"""
    return {
        "shop_enabled": False,
        "payment_stub_enabled": True,
        "payment_system": "stub",
        "currency_packages": {},
        "custom_purchase": {
            "enabled": False,
            "min_amount": 1,
            "max_amount": 1000,
            "price_per_coin": 1.0
        }
    }

# Глобальная переменная для конфигурации
CURRENCY_SHOP_CONFIG = load_currency_shop_config()

def reload_currency_config():
    """Перезагружает конфигурацию валютного магазина"""
    global CURRENCY_SHOP_CONFIG
    CURRENCY_SHOP_CONFIG = load_currency_shop_config()
    logger.info("Конфигурация валютного магазина перезагружена")
    return CURRENCY_SHOP_CONFIG