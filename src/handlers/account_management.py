"""
Обработчики для управления аккаунтами
"""
import logging
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from ..config.settings import CONFIG
from ..config.translations import TRANSLATIONS as T
from ..states.user_states import ChangePasswordStates
from ..keyboards.user_keyboards import kb_main, kb_back, kb_account_list
from ..utils.validators import validate_email, validate_password
from ..utils.notifications import record_message, delete_all_bot_messages, delete_user_message
from ..database.user_operations import reset_password, change_password, get_account_info, delete_account

logger = logging.getLogger("bot")

def register_account_handlers(dp, pool, bot_instance):
    """Регистрирует обработчики управления аккаунтами"""
    
    if CONFIG["features"]["account_management"]:
        @dp.callback_query(F.data == "my_account")
        async def cb_acc(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["account_management"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            accounts = await get_account_info(pool, c.from_user.id)
            
            if not accounts:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, T["account_no_account"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            text = T["select_account_prompt"]
            from ..main import bot
            msg = await bot.send_message(c.from_user.id, text, reply_markup=kb_account_list(accounts))
            record_message(c.from_user.id, msg, "command")
            await c.answer()

        @dp.callback_query(F.data.startswith("select_account_"))
        async def cb_select_account(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["account_management"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            email = c.data.replace("select_account_", "")
            accounts = await get_account_info(pool, c.from_user.id)
            
            if not accounts:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, T["account_no_account"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            selected = next((acc for acc in accounts if acc[0] == email), None)
            if not selected:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            email, username, is_temp, temp_password = selected
            pwd_status = T["reset_success"].format(password=temp_password) if is_temp else T["change_password_success"]
            text = T["account_info"].format(username=username, email=email, password_status=pwd_status)
            
            try:
                msg = await c.message.edit_text(text, reply_markup=kb_account_list(accounts, selected_email=email))
            except TelegramBadRequest as e:
                if "message is not modified" in str(e).lower():
                    await c.answer()
                    return
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, text, reply_markup=kb_account_list(accounts, selected_email=email))
            
            record_message(c.from_user.id, msg, "command")
            await c.answer()

        @dp.callback_query(F.data.startswith("reset_password_"))
        async def cb_reset_password(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["account_management"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return

            await state.clear()
            email = c.data.replace("reset_password_", "")
            accounts = await get_account_info(pool, c.from_user.id)
            if not any(acc[0] == email for acc in accounts):
                await c.answer("❌ ??????? ?? ??????", show_alert=True)
                return

            tmp = await reset_password(pool, email)
            if tmp is None:
                await c.answer(T["reset_err_not_found"], show_alert=True)
                return

            text_msg = T["reset_success"].format(password=tmp)
            try:
                await c.message.edit_text(text_msg, reply_markup=kb_account_list(accounts, selected_email=email))
            except TelegramBadRequest:
                from ..main import bot
                await bot.send_message(c.from_user.id, text_msg, reply_markup=kb_account_list(accounts, selected_email=email))
            await c.answer()

        @dp.callback_query(F.data == "change_password")
        async def cb_change_password(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["account_management"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            accounts = await get_account_info(pool, c.from_user.id)
            
            if not accounts:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, T["account_no_account"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            # Находим выбранный email из текста сообщения
            sel = None
            for email, *_ in accounts:
                if email in c.message.text:
                    sel = email
                    break
            
            if not sel:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, T["select_account_prompt"], reply_markup=kb_account_list(accounts))
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            await state.set_state(ChangePasswordStates.new_password)
            await state.update_data(email=sel)
            from ..main import bot
            msg = await bot.send_message(c.from_user.id, T["change_password_prompt"], reply_markup=kb_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()

        @dp.message(ChangePasswordStates.new_password)
        async def step_change_password(m: Message, state: FSMContext):
            data = await state.get_data()
            email = data.get("email")
            new_password = m.text.strip()
            
            if new_password in (T["to_main"], T["cancel"]):
                await state.clear()
                msg = await m.answer(T["start"], reply_markup=kb_main())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            if not validate_password(new_password):
                msg = await m.answer(T["err_pwd"], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="OK", callback_data="error_ok")]]))
                record_message(m.from_user.id, msg, "error")
                await delete_user_message(m)
                return
            
            await change_password(pool, email, new_password)
            await state.clear()
            await delete_all_bot_messages(m.from_user.id)
            msg = await m.answer(T["change_password_success"], reply_markup=kb_main())
            record_message(m.from_user.id, msg, "command")
            await delete_user_message(m)

        @dp.callback_query(F.data.startswith("delete_account_"))
        async def cb_delete_account(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["account_management"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            email = c.data.replace("delete_account_", "")
            success = await delete_account(pool, c.from_user.id, email)
            await delete_all_bot_messages(c.from_user.id)
            
            if not success:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, T["delete_account_error"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            accounts = await get_account_info(pool, c.from_user.id)
            if not accounts:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, T["account_no_account"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            text = T["delete_account_success"] + "\n\n" + T["select_account_prompt"]
            from ..main import bot
            msg = await bot.send_message(c.from_user.id, text, reply_markup=kb_account_list(accounts))
            record_message(c.from_user.id, msg, "command")
            await c.answer()