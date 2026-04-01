"""
WoW Reg Bot — VK-версия.
Bots Long Poll API, FSM на Redis, MySQL.
"""
import asyncio
import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler

from src.config.settings import load_config, VK_TOKEN, VK_GROUP_ID, BOT_VERSION, ADMIN_ID, REDIS_DSN
from src.database.connection import get_pool
from src.states.fsm import FSMStorage
from src.utils.vk_api import VkApi
from src.utils.longpoll import BotLongPoll
from src.utils.middleware import RateLimit

from src.handlers import commands as cmd_handler
from src.handlers import registration as reg_handler
from src.handlers import account_management as acc_handler
from src.handlers import admin as admin_handler
from src.handlers import messages as msg_handler


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


def init_config_files():
    for fp in ("connection_info.txt", "news.txt"):
        if not os.path.exists(fp):
            try:
                with open(fp, "w", encoding="utf-8") as f:
                    pass
                logging.info(f"Создан пустой файл: {fp}")
            except Exception as e:
                logging.error(f"Ошибка при создании {fp}: {e}")


def _parse_payload(raw) -> str | None:
    """Извлекает cmd из payload (строка или dict)."""
    if not raw:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if isinstance(raw, dict):
        return raw.get("cmd")
    return None


async def dispatch_message(api, pool, fsm, rate_limit, event):
    """Обработка события message_new."""
    msg = event.get("object", {}).get("message", {})
    user_id = msg.get("from_id", 0)
    peer_id = msg.get("peer_id", user_id)
    text = (msg.get("text") or "").strip()
    msg_id = msg.get("conversation_message_id")

    if user_id <= 0:
        return

    if not rate_limit.check(user_id):
        return

    try:
        ctx = fsm.get_context(user_id)
        cur_state = await ctx.get_state()

        if text:
            if await cmd_handler.handle_command(api, pool, user_id, peer_id, text, fsm, msg_id):
                return

        if cur_state and text:
            if await reg_handler.handle_text(api, pool, user_id, peer_id, text, fsm, msg_id):
                return
            if await acc_handler.handle_text(api, pool, user_id, peer_id, text, fsm, msg_id):
                return
            if await admin_handler.handle_text(api, pool, user_id, peer_id, text, fsm, msg_id):
                return

        await msg_handler.handle_fallback_message(api, user_id, peer_id, event, msg_id)
    finally:
        rate_limit.release(user_id)


async def dispatch_event(api, pool, fsm, rate_limit, event):
    """Обработка события message_event (callback-кнопка)."""
    obj = event.get("object", {})
    user_id = obj.get("user_id", 0)
    peer_id = obj.get("peer_id", user_id)
    event_id = obj.get("event_id", "")
    payload = obj.get("payload", {})
    conv_msg_id = obj.get("conversation_message_id")

    cmd = _parse_payload(payload)
    if not cmd or user_id <= 0:
        return

    if not rate_limit.check(user_id, event_id):
        try:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": "⏱ Подождите..."})
        except Exception:
            pass
        return

    try:
        if await cmd_handler.handle_callback(api, pool, user_id, peer_id, cmd, fsm, event_id, conv_msg_id):
            return
        if await reg_handler.handle_callback(api, pool, user_id, peer_id, cmd, fsm, event_id, conv_msg_id):
            return
        if await acc_handler.handle_callback(api, pool, user_id, peer_id, cmd, fsm, event_id, conv_msg_id):
            return
        if await admin_handler.handle_callback(api, pool, user_id, peer_id, cmd, fsm, event_id, conv_msg_id):
            return

        await msg_handler.handle_fallback_callback(api, user_id, peer_id, cmd, event_id)
    finally:
        rate_limit.release(user_id, event_id)


async def main():
    logger = setup_logging()
    logger.info(f"Запуск VK-бота v{BOT_VERSION}")

    if not VK_TOKEN or not VK_GROUP_ID:
        logger.error("VK_TOKEN и VK_GROUP_ID обязательны в .env")
        return

    load_config()
    init_config_files()

    api = VkApi(VK_TOKEN)
    pool = None
    fsm = FSMStorage(REDIS_DSN)
    rate_limit = RateLimit()

    try:
        pool = await get_pool()
        logger.info("MySQL подключен")
    except Exception as e:
        logger.error(f"Ошибка подключения к MySQL: {e}")
        await api.close()
        return

    try:
        await fsm.connect()
    except Exception as e:
        logger.warning(f"Redis недоступен, FSM работать не будет: {e}")
        await api.close()
        if pool:
            pool.close()
            await pool.wait_closed()
        return

    lp = BotLongPoll(api, VK_GROUP_ID)
    logger.info("Бот запущен, ожидание событий...")

    try:
        async for event in lp.listen():
            etype = event.get("type")
            if etype == "message_new":
                asyncio.create_task(dispatch_message(api, pool, fsm, rate_limit, event))
            elif etype == "message_event":
                asyncio.create_task(dispatch_event(api, pool, fsm, rate_limit, event))
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        await fsm.close()
        if pool:
            pool.close()
            await pool.wait_closed()
        await api.close()
        logger.info("Ресурсы освобождены")


if __name__ == "__main__":
    asyncio.run(main())
