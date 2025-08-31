"""
Обработчики регистрации
"""
import logging
import pymysql
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from ..config.settings import CONFIG, BOT_VERSION
from ..config.translations import TRANSLATIONS as T
from ..states.user_states import RegistrationStates
from ..keyboards.user_keyboards import kb_main, kb_wizard
from ..utils.validators import validate_nickname, validate_password, validate_email
from ..utils.notifications import record_message, delete_all_bot_messages, delete_user_message
from ..database.user_operations import register_user

logger = logging.getLogger("bot")

def register_registration_handlers(dp, pool, bot_instance):
    """Регистрирует обработчики регистрации"""
    
    if not CONFIG["features"]["registration"]:
        return
    
    # Хранилище для ID сообщений мастера
    user_wizard_msg = {}
    
    @dp.callback_query(F.data == "reg_start")
    async def cb_reg_start(c: CallbackQuery, state: FSMContext):
        if not CONFIG["features"]["registration"]:
            await c.answer(T["feature_disabled"], show_alert=True)
            return
        
        await state.clear()
        await delete_all_bot_messages(c.from_user.id)
        await state.set_state(RegistrationStates.nick)
        text = f"1/3 · {T['progress'][0]}"
        
        try:
            msg = await c.message.edit_text(text, reply_markup=kb_wizard(0))
        except:
            from ..main import bot
            msg = await bot.send_message(c.from_user.id, text, reply_markup=kb_wizard(0))
        
        user_wizard_msg[c.from_user.id] = msg.message_id
        record_message(c.from_user.id, msg, "conversation")
        await c.answer()
        logger.info(f"Начало регистрации для user_id={c.from_user.id}, состояние=RegistrationStates.nick")

    @dp.callback_query(F.data.in_(["wiz_back", "wiz_cancel"]))
    async def cb_wiz_nav(c: CallbackQuery, state: FSMContext):
        if not CONFIG["features"]["registration"]:
            await c.answer(T["feature_disabled"], show_alert=True)
            return
        
        cur = await state.get_state()
        
        if c.data == "wiz_cancel":
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            from ..main import bot
            msg = await bot.send_message(c.from_user.id, T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
            record_message(c.from_user.id, msg, "command")
            logger.info(f"Регистрация отменена для user_id={c.from_user.id}")
            await c.answer()
            return
        
        if cur == RegistrationStates.nick.state:
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            from ..main import bot
            msg = await bot.send_message(c.from_user.id, T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
            record_message(c.from_user.id, msg, "command")
            logger.info(f"Возврат в главное меню из RegistrationStates.nick для user_id={c.from_user.id}")
            await c.answer()
            return
        
        if cur == RegistrationStates.pwd.state:
            await state.set_state(RegistrationStates.nick)
            text = f"1/3 · {T['progress'][0]}"
            try:
                from ..main import bot
                await bot.edit_message_text(
                    text=text,
                    chat_id=c.message.chat.id,
                    message_id=user_wizard_msg.get(c.from_user.id),
                    reply_markup=kb_wizard(0)
                )
            except:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, text, reply_markup=kb_wizard(0))
                user_wizard_msg[c.from_user.id] = msg.message_id
                record_message(c.from_user.id, msg, "conversation")
            logger.info(f"Возврат к RegistrationStates.nick для user_id={c.from_user.id}")
            await c.answer()
            return
        
        if cur == RegistrationStates.mail.state:
            await state.set_state(RegistrationStates.pwd)
            text = f"2/3 · {T['progress'][1]}"
            try:
                from ..main import bot
                await bot.edit_message_text(
                    text=text,
                    chat_id=c.message.chat.id,
                    message_id=user_wizard_msg.get(c.from_user.id),
                    reply_markup=kb_wizard(1)
                )
            except:
                from ..main import bot
                msg = await bot.send_message(c.from_user.id, text, reply_markup=kb_wizard(1))
                user_wizard_msg[c.from_user.id] = msg.message_id
                record_message(c.from_user.id, msg, "conversation")
            logger.info(f"Возврат к RegistrationStates.pwd для user_id={c.from_user.id}")
            await c.answer()
            return

    @dp.message(RegistrationStates.nick)
    async def step_nick(m: Message, state: FSMContext):
        nick = m.text.strip()
        
        if not validate_nickname(nick):
            msg = await m.answer(
                T["err_nick"],
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="OK", callback_data="error_ok")
                ]])
            )
            record_message(m.from_user.id, msg, "error")
            await delete_user_message(m)
            return
        
        await state.update_data(nick=nick)
        await state.set_state(RegistrationStates.pwd)
        text = f"2/3 · {T['progress'][1]}"
        
        try:
            from ..main import bot
            await bot.edit_message_text(
                text=text,
                chat_id=m.chat.id,
                message_id=user_wizard_msg.get(m.from_user.id),
                reply_markup=kb_wizard(1)
            )
        except:
            from ..main import bot
            msg = await bot.send_message(m.from_user.id, text, reply_markup=kb_wizard(1))
            user_wizard_msg[m.from_user.id] = msg.message_id
            record_message(m.from_user.id, msg, "conversation")
        
        await delete_user_message(m)
        logger.info(f"Переход к RegistrationStates.pwd для user_id={m.from_user.id}")

    @dp.message(RegistrationStates.pwd)
    async def step_pwd(m: Message, state: FSMContext):
        pwd = m.text.strip()
        
        if not validate_password(pwd):
            msg = await m.answer(
                T["err_pwd"],
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="OK", callback_data="error_ok")
                ]])
            )
            record_message(m.from_user.id, msg, "error")
            await delete_user_message(m)
            return
        
        await state.update_data(pwd=pwd)
        await state.set_state(RegistrationStates.mail)
        text = f"3/3 · {T['progress'][2]}"
        
        try:
            from ..main import bot
            await bot.edit_message_text(
                text=text,
                chat_id=m.chat.id,
                message_id=user_wizard_msg.get(m.from_user.id),
                reply_markup=kb_wizard(2)
            )
        except:
            from ..main import bot
            msg = await bot.send_message(m.from_user.id, text, reply_markup=kb_wizard(2))
            user_wizard_msg[m.from_user.id] = msg.message_id
            record_message(m.from_user.id, msg, "conversation")
        
        await delete_user_message(m)
        logger.info(f"Переход к RegistrationStates.mail для user_id={m.from_user.id}")

    @dp.message(RegistrationStates.mail)
    async def step_mail(m: Message, state: FSMContext):
        email = m.text.strip()
        
        if not validate_email(email):
            msg = await m.answer(
                T["err_mail"],
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="OK", callback_data="error_ok")
                ]])
            )
            record_message(m.from_user.id, msg, "error")
            await delete_user_message(m)
            return
        
        data = await state.get_data()
        
        try:
            login, error = await register_user(pool, data["nick"], data["pwd"], email, m.from_user.id)
            await state.clear()
            await delete_all_bot_messages(m.from_user.id)
            
            if login:
                msg = await m.answer(
                    T["success"].format(username=login),
                    reply_markup=kb_main()
                )
                record_message(m.from_user.id, msg, "command")
            else:
                error_msg = T[error].format(max_accounts=CONFIG["settings"]["max_accounts_per_user"])
                msg = await m.answer(error_msg, reply_markup=kb_main())
                record_message(m.from_user.id, msg, "command")
        
        except pymysql.err.IntegrityError as e:
            logger.error(f"Не удалось зарегистрировать пользователя с e-mail {email}: {e}")
            await state.clear()
            await delete_all_bot_messages(m.from_user.id)
            msg = await m.answer(T["err_exists"], reply_markup=kb_main())
            record_message(m.from_user.id, msg, "command")
        
        await delete_user_message(m)
        logger.info(f"Завершение регистрации для user_id={m.from_user.id}, email={email}")