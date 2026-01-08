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

async def safe_edit_message(bot, callback_or_message, text: str, reply_markup=None, **kwargs):
    """
    Безопасно редактирует сообщение с fallback на отправку нового сообщения.
    
    Args:
        bot: Экземпляр бота
        callback_or_message: CallbackQuery или Message объект
        text: Текст для отправки
        reply_markup: Клавиатура (опционально)
        **kwargs: Дополнительные параметры для edit_message_text
    
    Returns:
        Message: Отредактированное или новое сообщение
    """
    from aiogram.types import CallbackQuery, Message
    from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
    
    try:
        if isinstance(callback_or_message, CallbackQuery):
            message = callback_or_message.message
            chat_id = message.chat.id
            message_id = message.message_id
        else:
            message = callback_or_message
            chat_id = message.chat.id
            message_id = message.message_id
        
        # Пытаемся отредактировать сообщение
        try:
            edited_msg = await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup,
                **kwargs
            )
            return edited_msg
        except (TelegramBadRequest, TelegramAPIError) as e:
            error_msg = str(e).lower()
            # Если сообщение не изменилось или другие некритичные ошибки - просто возвращаем исходное
            if "message is not modified" in error_msg or "message to edit not found" in error_msg:
                return message
            
            # В остальных случаях отправляем новое сообщение
            logger.debug(f"Не удалось отредактировать сообщение {message_id}: {e}, отправляем новое")
            try:
                # Пытаемся удалить старое сообщение (не критично, если не получится)
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            except Exception:
                pass
            
            # Отправляем новое сообщение
            new_msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                **kwargs
            )
            return new_msg
            
    except Exception as e:
        logger.error(f"Ошибка при безопасном редактировании сообщения: {e}")
        # В крайнем случае пытаемся отправить новое сообщение
        try:
            if isinstance(callback_or_message, CallbackQuery):
                chat_id = callback_or_message.message.chat.id
            else:
                chat_id = callback_or_message.chat.id
            
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                **kwargs
            )
        except Exception as e2:
            logger.error(f"Критическая ошибка при отправке сообщения: {e2}")
            raise