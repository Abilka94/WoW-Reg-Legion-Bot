"""
Общие обработчики сообщений
"""
import logging
from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from ..states.user_states import RegistrationStates, ForgotPasswordStates, ChangePasswordStates, AdminStates
from ..keyboards.user_keyboards import kb_main
from ..utils.notifications import record_message, delete_user_message, delete_all_bot_messages

logger = logging.getLogger("bot")

# Хранилище для ID последних предупреждающих сообщений (для предотвращения накопления)
user_warning_msgs = {}

def register_message_handlers(dp, pool, bot_instance):
    """Регистрирует общие обработчики сообщений"""
    
    @dp.message(F.chat.type == ChatType.PRIVATE)
    async def handle_private_messages(m: Message, state: FSMContext):
        current_state = await state.get_state()
        
        # Пропускаем сообщения в состояниях FSM (регистрация и другие процессы)
        if current_state in (
            RegistrationStates.nick.state,
            RegistrationStates.pwd.state,
            RegistrationStates.mail.state,
            ForgotPasswordStates.email.state,
            ChangePasswordStates.new_password.state,
            AdminStates.broadcast_text.state,
            AdminStates.delete_account_input.state
        ):
            return
        
        # Игнорируем команды (они обрабатываются отдельно)
        if m.text and m.text.startswith("/"):
            return
        
        # Вне процесса регистрации - просто удаляем сообщение пользователя без ответа
        await delete_user_message(m)
        # Не отправляем никаких ответов - просто удаляем невалидное сообщение

    @dp.message()
    async def unknown(m: Message):
        """Обработчик неизвестных сообщений"""
        msg = await m.answer("❓ Используйте меню или /start")
        record_message(m.from_user.id, msg, "command")