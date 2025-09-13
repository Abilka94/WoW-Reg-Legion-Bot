"""
Общие обработчики сообщений
"""
import logging
from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext

from ..states.user_states import RegistrationStates, ForgotPasswordStates, ChangePasswordStates, AdminStates, CurrencyShopStates
from ..keyboards.user_keyboards import kb_main
from ..utils.notifications import record_message, delete_user_message

logger = logging.getLogger("bot")

def register_message_handlers(dp, pool, bot_instance):
    """Регистрирует общие обработчики сообщений"""
    
    @dp.message(F.chat.type == ChatType.PRIVATE)
    async def handle_private_messages(m: Message, state: FSMContext):
        current_state = await state.get_state()
        
        # Пропускаем сообщения в состояниях FSM
        if current_state in (
            RegistrationStates.nick.state,
            RegistrationStates.pwd.state,
            RegistrationStates.mail.state,
            ForgotPasswordStates.email.state,
            ChangePasswordStates.new_password.state,
            AdminStates.broadcast_text.state,
            AdminStates.delete_account_input.state,
            CurrencyShopStates.custom_amount.state
        ):
            return
        
        await delete_user_message(m)
        
        # Игнорируем команды (они обрабатываются отдельно)
        if not m.text.startswith("/"):
            from ..config.translations import TRANSLATIONS as T
            msg = await m.answer(T["use_menu_or_start"], reply_markup=kb_main())
            record_message(m.from_user.id, msg, "command")

    @dp.message()
    async def unknown(m: Message):
        """Обработчик неизвестных сообщений"""
        from ..config.translations import TRANSLATIONS as T
        msg = await m.answer(T["use_menu_or_start"])
        record_message(m.from_user.id, msg, "command")
