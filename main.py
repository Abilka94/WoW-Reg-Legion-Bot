"""
Thin starter for the modular bot.
"""
import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage

from src.config.settings import load_config, TOKEN, REDIS_DSN, BOT_VERSION
from src.database.connection import get_pool
from src.utils.middleware import RateLimit

from src.handlers.commands import register_command_handlers, register_callback_handlers
from src.handlers.registration import register_registration_handlers
from src.handlers.account_management import register_account_handlers
from src.handlers.admin import register_admin_handlers
from src.handlers.messages import register_message_handlers
from src.handlers.currency_shop import register_currency_shop_handlers


def setup_logging():
    logger = logging.getLogger("bot")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    h_info = TimedRotatingFileHandler("bot.log", when="midnight", backupCount=7, encoding="utf-8")
    h_info.setLevel(logging.INFO)
    h_info.setFormatter(fmt)
    logger.addHandler(h_info)
    h_err = TimedRotatingFileHandler("error.log", when="midnight", backupCount=7, encoding="utf-8")
    h_err.setLevel(logging.ERROR)
    h_err.setFormatter(fmt)
    logger.addHandler(h_err)
    logger.addHandler(logging.StreamHandler())
    return logger


async def main():
    logger = setup_logging()
    logger.info(f"Starting bot version {BOT_VERSION}")

    load_config()

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Storage
    storage = None
    try:
        redis_cli = aioredis.from_url(REDIS_DSN)
        storage = RedisStorage(redis=redis_cli, state_ttl=3600)
        logger.info("Redis FSM storage enabled")
    except Exception as e:
        logger.warning(f"Redis unavailable, fallback to in-memory: {e}")

    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    dp.message.middleware(RateLimit())
    dp.callback_query.middleware(RateLimit())

    # DB pool
    try:
        pool = await get_pool()
        logger.info("DB connection OK")
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        pool = None

    # Register modular handlers
    register_command_handlers(dp, pool, bot)
    register_callback_handlers(dp, pool, bot)
    register_registration_handlers(dp, pool, bot)
    register_account_handlers(dp, pool, bot)
    register_admin_handlers(dp, pool, bot)
    register_currency_shop_handlers(dp, pool, bot)
    register_message_handlers(dp, pool, bot)

    logger.info("Polling...")
    try:
        await dp.start_polling(bot)
    finally:
        if pool:
            pool.close()
            await pool.wait_closed()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
