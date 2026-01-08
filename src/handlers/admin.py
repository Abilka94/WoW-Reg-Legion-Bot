"""
Обработчики для административных функций
"""
import logging
import os
from aiogram import F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from ..config.settings import CONFIG, ADMIN_ID
from ..config.translations import TRANSLATIONS as T
from ..states.user_states import AdminStates
from ..keyboards.admin_keyboards import kb_admin, kb_admin_back
from ..keyboards.user_keyboards import kb_main, kb_back
from ..utils.validators import validate_email
from ..utils.notifications import record_message, delete_all_bot_messages, delete_user_message, notify_admin
from ..database.user_operations import admin_delete_account

logger = logging.getLogger("bot")

def register_admin_handlers(dp, pool, bot_instance):
    """Регистрирует обработчики административных функций"""
    
    if CONFIG["features"]["admin_broadcast"]:
        @dp.callback_query(F.data == "admin_broadcast")
        async def cb_admin_bcast(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_broadcast"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            
            if c.from_user.id != ADMIN_ID:
                from main import bot
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            await state.set_state(AdminStates.broadcast_text)
            from main import bot
            msg = await bot.send_message(c.from_user.id, "Введите текст рассылки:", reply_markup=kb_admin_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()

        @dp.message(AdminStates.broadcast_text)
        async def step_broadcast(m: Message, state: FSMContext):
            if not CONFIG["features"]["admin_broadcast"]:
                msg = await m.answer(T["feature_disabled"], reply_markup=kb_back())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            if m.text.strip() in (T["cancel"], T["admin_back"]):
                await state.clear()
                await delete_all_bot_messages(m.from_user.id)
                msg = await m.answer(T["admin_panel"], reply_markup=kb_admin())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            await state.clear()
            await delete_all_bot_messages(m.from_user.id)
            
            try:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT telegram_id FROM users")
                        users = await cur.fetchall()
                
                ok = fail = 0
                from main import bot
                for (uid,) in users:
                    try:
                        await bot.send_message(uid, m.text)
                        ok += 1
                    except Exception as e:
                        logger.warning(f"Не удалось отправить сообщение пользователю {uid}: {e}")
                        fail += 1
                
                txt = f"✅ Успех: {ok} | ❌ Ошибок: {fail}"
            except Exception as e:
                logger.error(f"Ошибка при выполнении рассылки: {e}")
                txt = f"❌ {e}"
            
            msg = await m.answer(txt, reply_markup=kb_admin_back())
            record_message(m.from_user.id, msg, "command")
            await delete_user_message(m)

    if CONFIG["features"]["admin_check_db"]:
        @dp.callback_query(F.data == "admin_check_db")
        async def cb_admin_db(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_check_db"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            
            if c.from_user.id != ADMIN_ID:
                from main import bot
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            try:
                async with pool.acquire():
                    pass
                txt = T["db_ok"]
            except Exception as e:
                txt = f"❌ {e}"
                from main import bot
                await notify_admin(bot, str(e))
                logger.error(f"Ошибка проверки базы данных: {e}")
            
            from main import bot
            msg = await bot.send_message(c.from_user.id, txt, reply_markup=kb_admin_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()
    if CONFIG["features"]["admin_delete_account"]:

        @dp.callback_query(F.data == "admin_delete_account")
        async def cb_admin_delete_account(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_delete_account"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            
            if c.from_user.id != ADMIN_ID:
                from main import bot
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            await state.set_state(AdminStates.delete_account_input)
            from main import bot
            msg = await bot.send_message(c.from_user.id, T["admin_delete_prompt"], reply_markup=kb_admin_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()

        @dp.message(AdminStates.delete_account_input)
        async def step_admin_delete_account(m: Message, state: FSMContext):
            if m.text.strip() in (T["cancel"], T["admin_back"]):
                await state.clear()
                await delete_all_bot_messages(m.from_user.id)
                msg = await m.answer(T["admin_panel"], reply_markup=kb_admin())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            email = m.text.strip()
            
            try:
                is_valid, error_msg = validate_email(email, strict=True)
                if not is_valid:
                    raise ValueError(error_msg or "Некорректный e-mail")
                
                success = await admin_delete_account(pool, email)
                await state.clear()
                await delete_all_bot_messages(m.from_user.id)
                
                if success:
                    msg = await m.answer(T["admin_delete_success"].format(email=email), reply_markup=kb_admin_back())
                else:
                    msg = await m.answer(T["admin_delete_error"].format(error="Аккаунт не найден"), reply_markup=kb_admin_back())
            
            except Exception as e:
                logger.error(f"Ошибка при удалении аккаунта админом: {e}")
                await state.clear()
                await delete_all_bot_messages(m.from_user.id)
                msg = await m.answer(T["admin_delete_error"].format(error=str(e)), reply_markup=kb_admin_back())
            
            record_message(m.from_user.id, msg, "command")
            await delete_user_message(m)

    if CONFIG["features"]["admin_reload_config"]:
        @dp.callback_query(F.data == "admin_reload_config")
        async def cb_admin_reload_config(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_reload_config"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            
            if c.from_user.id != ADMIN_ID:
                from main import bot
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            try:
                from ..config.settings import reload_config
                from main import bot
                await reload_config(bot)
                msg = await bot.send_message(c.from_user.id, T["reload_config_success"], reply_markup=kb_admin())
            except Exception as e:
                logger.error(f"Ошибка при перезагрузке конфигурации: {e}")
                from main import bot
                msg = await bot.send_message(c.from_user.id, T["reload_config_error"].format(error=str(e)), reply_markup=kb_admin())
            
            record_message(c.from_user.id, msg, "command")
            await c.answer()

    if CONFIG["features"]["admin_panel"]:
        @dp.callback_query(F.data == "admin_main")
        async def cb_admin_main(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_panel"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id)
            from main import bot
            msg = await bot.send_message(c.from_user.id, T["start"], reply_markup=kb_main())
            record_message(c.from_user.id, msg, "command")
            await c.answer()