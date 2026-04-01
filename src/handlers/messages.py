"""
Обработчик общих сообщений — фильтр не-текста и «мусора».
"""
import logging

from ..config.settings import ADMIN_ID
from ..config.translations import TRANSLATIONS as T
from ..keyboards.user_keyboards import kb_main
from ..utils.notifications import record_message

logger = logging.getLogger("bot")


async def handle_fallback_message(api, user_id, peer_id, event, msg_id):
    """
    Вызывается когда сообщение не было обработано ни одним хендлером.
    В VK нет чётких типов «стикер/файл» на уровне message_new —
    но есть attachments; если есть вложения и нет текста — игнорируем (пытаемся удалить).
    """
    attachments = event.get("object", {}).get("message", {}).get("attachments", [])
    text = event.get("object", {}).get("message", {}).get("text", "")

    if attachments and not text.strip():
        try:
            await api.delete_message(peer_id, msg_id)
        except Exception:
            pass
        return

    if not text.strip():
        return

    mid = await api.send_message(
        peer_id,
        "Используйте меню или введите /start для начала.",
        kb_main(is_admin=user_id == ADMIN_ID),
    )
    record_message(user_id, mid, "command")


async def handle_fallback_callback(api, user_id, peer_id, cmd, event_id):
    """Необработанный payload callback-кнопки."""
    logger.info(f"Необработанный callback: {cmd} от vk_id={user_id}")
    await api.send_event_answer(
        event_id, user_id, peer_id,
        {"type": "show_snackbar", "text": "🔧 Функция в разработке"},
    )
