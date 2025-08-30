"""
Уведомления и работа с сообщениями
"""
import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger("bot")

# Трекинг сообщений
conv_msgs, cmd_msgs, error_msgs = {}, {}, {}

def record_message(user_id: int, msg: Message, typ: str = "conversation"):
    """Записывает сообщение для последующего удаления"""
    store = {"conversation": conv_msgs, "command": cmd_msgs, "error": error_msgs}.get(typ, conv_msgs)
    store[user_id] = (msg.chat.id, msg.message_id)

async def delete_messages(user_id: int, store: dict, bot=None):
    """Удаляет сообщения из указанного хранилища"""
    if user_id in store and bot:
        cid, mid = store.pop(user_id)
        try:
            await bot.delete_message(cid, mid)
        except:
            pass

async def delete_all_bot_messages(user_id: int, bot=None):
    """Удаляет все сообщения бота для пользователя"""
    for s in (conv_msgs, cmd_msgs, error_msgs):
        await delete_messages(user_id, s, bot)

async def delete_user_message(message: Message):
    """Удаляет сообщение пользователя"""
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение пользователя {message.from_user.id}: {e}")

async def notify_admin(bot, txt):
    """Отправляет уведомление администратору"""
    from ..config.settings import ADMIN_ID
    
    try:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="OK", callback_data="error_ok")]
        ])
        msg = await bot.send_message(ADMIN_ID, f"⚠ {txt}", reply_markup=markup)
        record_message(ADMIN_ID, msg, "error")
    except TelegramBadRequest:
        logger.error(f"Не удалось отправить уведомление администратору: {txt}")