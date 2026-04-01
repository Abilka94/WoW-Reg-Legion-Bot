"""
Обработчики команд и базовых callback: /start, /version, /admin, /reload_config,
back_to_main, show_info, show_news, error_ok, open_admin_panel, admin_back.
"""
import logging

from ..config.settings import CONFIG, BOT_VERSION, ADMIN_ID
from ..config.translations import TRANSLATIONS as T
from ..keyboards.user_keyboards import kb_main, kb_back, kb_ok
from ..keyboards.admin_keyboards import kb_admin, kb_admin_back
from ..utils.notifications import record_message, delete_all_bot_messages, safe_send_or_edit
from ..utils.file_cache import FileCache

logger = logging.getLogger("bot")

news_cache = FileCache("news.txt")
info_cache = FileCache("connection_info.txt")


async def handle_command(api, pool, user_id: int, peer_id: int, text: str, fsm, msg_id: int | None = None):
    """Обрабатывает текстовые команды (/start и т.д.). Возвращает True если обработано."""
    cmd = text.strip().lower()

    if cmd in ("/start", "начать", "start"):
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        mid = await api.send_message(peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID))
        record_message(user_id, mid, "command")
        await _try_delete_user_msg(api, peer_id, msg_id)
        return True

    if cmd in ("/version", "версия"):
        await delete_all_bot_messages(user_id, api)
        mid = await api.send_message(peer_id, f"{T['version_pre']}{BOT_VERSION}", kb_back())
        record_message(user_id, mid, "command")
        await _try_delete_user_msg(api, peer_id, msg_id)
        return True

    if cmd in ("/admin", "админ"):
        if not CONFIG["features"]["admin_panel"]:
            mid = await api.send_message(peer_id, T["feature_disabled"], kb_back())
            record_message(user_id, mid, "command")
            await _try_delete_user_msg(api, peer_id, msg_id)
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        if user_id != ADMIN_ID:
            mid = await api.send_message(peer_id, T["no_access"], kb_back())
        else:
            mid = await api.send_message(peer_id, T["admin_panel"], kb_admin())
        record_message(user_id, mid, "command")
        await _try_delete_user_msg(api, peer_id, msg_id)
        return True

    if cmd in ("/reload_config",):
        if not CONFIG["features"]["admin_reload_config"]:
            mid = await api.send_message(peer_id, T["feature_disabled"], kb_back())
            record_message(user_id, mid, "command")
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        if user_id != ADMIN_ID:
            mid = await api.send_message(peer_id, T["no_access"], kb_back())
            record_message(user_id, mid, "command")
            return True
        try:
            from ..config.settings import load_config
            load_config()
            mid = await api.send_message(peer_id, T["reload_config_success"], kb_admin())
        except Exception as e:
            logger.error(f"Ошибка перезагрузки конфига: {e}")
            mid = await api.send_message(peer_id, T["reload_config_error"].format(error=str(e)), kb_admin())
        record_message(user_id, mid, "command")
        return True

    return False


async def handle_callback(api, pool, user_id: int, peer_id: int, cmd: str, fsm, event_id: str, conversation_message_id: int | None = None):
    """Обрабатывает базовые callback-кнопки. Возвращает True если обработано."""

    if cmd == "back_to_main":
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        mid = await safe_send_or_edit(api, peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID), conversation_message_id)
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "show_info":
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        txt = await info_cache.get()
        mid = await api.send_message(peer_id, txt or "—", kb_back())
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "show_news":
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        txt = await news_cache.get()
        mid = await api.send_message(peer_id, txt or "—", kb_back())
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "error_ok":
        await api.delete_message(peer_id, conversation_message_id) if conversation_message_id else None
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "open_admin_panel":
        if not CONFIG["features"]["admin_panel"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        if user_id != ADMIN_ID:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["no_access"]})
            return True
        mid = await safe_send_or_edit(api, peer_id, T["admin_panel"], kb_admin(), conversation_message_id)
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "admin_back":
        if not CONFIG["features"]["admin_panel"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        if user_id != ADMIN_ID:
            mid = await api.send_message(peer_id, T["no_access"], kb_back())
            record_message(user_id, mid, "command")
            await api.send_event_answer(event_id, user_id, peer_id)
            return True
        if conversation_message_id:
            try:
                await api.delete_message(peer_id, conversation_message_id)
            except Exception:
                pass
        mid = await api.send_message(peer_id, T["admin_panel"], kb_admin())
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    if cmd == "admin_main":
        if not CONFIG["features"]["admin_panel"]:
            await api.send_event_answer(event_id, user_id, peer_id, {"type": "show_snackbar", "text": T["feature_disabled"]})
            return True
        ctx = fsm.get_context(user_id)
        await ctx.clear()
        await delete_all_bot_messages(user_id, api)
        mid = await api.send_message(peer_id, T["start"], kb_main(is_admin=user_id == ADMIN_ID))
        record_message(user_id, mid, "command")
        await api.send_event_answer(event_id, user_id, peer_id)
        return True

    return False


async def _try_delete_user_msg(api, peer_id, msg_id):
    if msg_id:
        try:
            await api.delete_message(peer_id, msg_id)
        except Exception:
            pass
