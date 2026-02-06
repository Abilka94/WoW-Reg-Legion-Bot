"""
Обработчики регистрации
"""
import logging
import pymysql
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from ..config.settings import CONFIG
from ..config.translations import TRANSLATIONS as T
from ..states.user_states import RegistrationStates
from ..keyboards.user_keyboards import kb_main, kb_wizard, kb_password_weak_choice
from ..utils.validators import validate_nickname, validate_password, validate_email, check_password_strength
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
            msg = await bot.send_message(c.from_user.id, T["start"], reply_markup=kb_main())
            record_message(c.from_user.id, msg, "command")
            logger.info(f"Регистрация отменена для user_id={c.from_user.id}")
            await c.answer()
            return
        
        if cur == RegistrationStates.nick.state:
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            from ..main import bot
            msg = await bot.send_message(c.from_user.id, T["start"], reply_markup=kb_main())
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
        # Если пользователь отправил команду, очищаем состояние и пропускаем обработку
        if m.text and m.text.startswith("/"):
            await state.clear()
            return
        
        # Если сообщение явно не является попыткой ввести никнейм (содержит пробелы, слишком длинное и т.д.)
        # очищаем состояние и показываем главное меню
        if m.text and (len(m.text.strip()) > 50 or " " in m.text.strip() or not m.text.strip()):
            await state.clear()
            await delete_user_message(m)
            from ..main import bot
            msg = await bot.send_message(m.from_user.id, T["start"], reply_markup=kb_main())
            record_message(m.from_user.id, msg, "command")
            logger.info(f"Очистка зависшего состояния регистрации для user_id={m.from_user.id}")
            return
        
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
        # Если пользователь отправил команду, очищаем состояние и пропускаем обработку
        if m.text and m.text.startswith("/"):
            await state.clear()
            return
        
        # Если сообщение явно не является попыткой ввести пароль (команда или слишком длинное)
        if m.text and (len(m.text.strip()) > 100 or not m.text.strip()):
            await state.clear()
            await delete_user_message(m)
            from ..main import bot
            msg = await bot.send_message(m.from_user.id, T["start"], reply_markup=kb_main())
            record_message(m.from_user.id, msg, "command")
            logger.info(f"Очистка зависшего состояния регистрации (pwd) для user_id={m.from_user.id}")
            return
        
        pwd = m.text.strip()
        
        # Валидация пароля с детальными сообщениями об ошибках
        is_valid, error_msg = validate_password(pwd)
        if not is_valid:
            msg = await m.answer(
                f"❌ {error_msg}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="OK", callback_data="error_ok")
                ]])
            )
            record_message(m.from_user.id, msg, "error")
            await delete_user_message(m)
            return
        
        # Проверка сложности пароля
        is_strong, warning_msg = check_password_strength(pwd)
        if not is_strong:
            # Пароль простой - показываем предупреждение с выбором
            await state.update_data(pwd=pwd)
            await state.set_state(RegistrationStates.pwd_confirm_weak)
            warning_text = T["password_weak_warning"].format(warning=warning_msg)
            from ..main import bot
            wizard_id = user_wizard_msg.get(m.from_user.id)
            try:
                await bot.edit_message_text(
                    text=warning_text,
                    chat_id=m.chat.id,
                    message_id=wizard_id,
                    reply_markup=kb_password_weak_choice()
                )
            except:
                msg = await bot.send_message(m.from_user.id, warning_text, reply_markup=kb_password_weak_choice())
                user_wizard_msg[m.from_user.id] = msg.message_id
                record_message(m.from_user.id, msg, "conversation")
            return
        
        # Пароль сложный - продолжаем регистрацию
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
        # Если пользователь отправил команду, очищаем состояние и пропускаем обработку
        if m.text and m.text.startswith("/"):
            await state.clear()
            return
        
        # Если сообщение явно не является попыткой ввести email (слишком длинное или пустое)
        if m.text and (len(m.text.strip()) > 254 or not m.text.strip()):
            await state.clear()
            await delete_user_message(m)
            from ..main import bot
            msg = await bot.send_message(m.from_user.id, T["start"], reply_markup=kb_main())
            record_message(m.from_user.id, msg, "command")
            logger.info(f"Очистка зависшего состояния регистрации (mail) для user_id={m.from_user.id}")
            return
        
        email = m.text.strip()
        
        # Строгая валидация email с проверкой известных провайдеров
        is_valid, error_msg = validate_email(email, strict=True)
        if not is_valid:
            msg = await m.answer(
                f"❌ {error_msg}\n\n{T['err_mail']}",
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