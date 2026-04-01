"""
Трекинг и управление сообщениями бота в VK.
Хранит message_id последних сообщений для возможности edit/delete.
"""
import logging

logger = logging.getLogger("bot")

conv_msgs: dict[int, int] = {}
cmd_msgs: dict[int, int] = {}
error_msgs: dict[int, int] = {}


def record_message(user_id: int, message_id: int | None, typ: str = "conversation"):
    if message_id is None:
        return
    store = {"conversation": conv_msgs, "command": cmd_msgs, "error": error_msgs}.get(typ, conv_msgs)
    store[user_id] = message_id


async def delete_messages(user_id: int, store: dict, api=None):
    if user_id in store and api:
        mid = store.pop(user_id)
        try:
            await api.delete_message(user_id, mid)
        except Exception:
            pass


async def delete_all_bot_messages(user_id: int, api=None):
    for s in (conv_msgs, cmd_msgs, error_msgs):
        await delete_messages(user_id, s, api)


async def safe_send_or_edit(api, peer_id: int, text: str, keyboard=None, edit_msg_id: int | None = None) -> int | None:
    """Пытается отредактировать edit_msg_id; при неудаче — отправляет новое."""
    if edit_msg_id:
        try:
            ok = await api.edit_message(peer_id, edit_msg_id, text, keyboard)
            if ok:
                return edit_msg_id
        except Exception:
            pass
    return await api.send_message(peer_id, text, keyboard)


async def notify_admin(api, admin_id: int, text: str):
    from ..keyboards.user_keyboards import kb_ok
    try:
        mid = await api.send_message(admin_id, f"⚠ {text}", kb_ok())
        record_message(admin_id, mid, "error")
    except Exception:
        logger.error(f"Не удалось отправить уведомление администратору: {text}")
