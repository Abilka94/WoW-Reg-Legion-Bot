"""
РћР±СЂР°Р±РѕС‚С‡РёРєРё РґР»СЏ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РёРІРЅС‹С… С„СѓРЅРєС†РёР№
"""
import logging
import os
from aiogram import F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from ..config.settings import CONFIG, ADMIN_ID, BOT_VERSION
from ..config.translations import TRANSLATIONS as T
from ..states.user_states import AdminStates
from ..keyboards.admin_keyboards import kb_admin, kb_admin_back
from ..keyboards.user_keyboards import kb_main, kb_back
from ..utils.validators import validate_email
from ..utils.notifications import record_message, delete_all_bot_messages, delete_user_message, notify_admin
from ..database.user_operations import admin_delete_account

logger = logging.getLogger("bot")

def register_admin_handlers(dp, pool, bot_instance):
    """Р РµРіРёСЃС‚СЂРёСЂСѓРµС‚ РѕР±СЂР°Р±РѕС‚С‡РёРєРё Р°РґРјРёРЅРёСЃС‚СЂР°С‚РёРІРЅС‹С… С„СѓРЅРєС†РёР№"""
    
    if CONFIG["features"]["admin_broadcast"]:
        @dp.callback_query(F.data == "admin_broadcast")
        async def cb_admin_bcast(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_broadcast"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            if c.from_user.id != ADMIN_ID:
                bot = bot_instance
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            await state.set_state(AdminStates.broadcast_text)
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, T["admin_broadcast_prompt"], reply_markup=kb_admin_back())
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
                await delete_all_bot_messages(m.from_user.id, bot_instance)
                msg = await m.answer(T["admin_panel"], reply_markup=kb_admin())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            await state.clear()
            await delete_all_bot_messages(m.from_user.id, bot_instance)
            
            try:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT telegram_id FROM users")
                        users = await cur.fetchall()
                
                ok = fail = 0
                bot = bot_instance
                for (uid,) in users:
                    try:
                        await bot.send_message(uid, m.text)
                        ok += 1
                    except Exception as e:
                        logger.warning(f"Failed to send broadcast to user {uid}: {e}")
                        fail += 1
                
                txt = f"✅ Sent: {ok} | ❌ Failed: {fail}"
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
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
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            if c.from_user.id != ADMIN_ID:
                bot = bot_instance
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
                bot = bot_instance
                await notify_admin(bot, str(e))
                logger.error(f"Database check error: {e}")
            
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, txt, reply_markup=kb_admin_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()

    if CONFIG["features"]["admin_download_log"]:
        @dp.callback_query(F.data == "admin_download_log")
        async def cb_admin_log(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_download_log"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            if c.from_user.id != ADMIN_ID:
                bot = bot_instance
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            try:
                if not os.path.exists("bot.log"):
                    raise FileNotFoundError("Log file not found")
                
                msg = await c.message.answer_document(FSInputFile("bot.log"), reply_markup=kb_admin_back())
                record_message(c.from_user.id, msg, "command")
            except Exception as e:
                logger.error(f"Error sending log file: {e}")
                bot = bot_instance
                msg = await bot.send_message(c.from_user.id, T["admin_delete_error"].format(error=str(e)), reply_markup=kb_admin_back())
                record_message(c.from_user.id, msg, "command")
            
            await c.answer()

    if CONFIG["features"]["admin_delete_account"]:
        @dp.callback_query(F.data == "admin_delete_account")
        async def cb_admin_delete_account(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_delete_account"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            if c.from_user.id != ADMIN_ID:
                bot = bot_instance
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            await state.set_state(AdminStates.delete_account_input)
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, T["admin_delete_prompt"], reply_markup=kb_admin_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()

        @dp.message(AdminStates.delete_account_input)
        async def step_admin_delete_account(m: Message, state: FSMContext):
            if m.text.strip() in (T["cancel"], T["admin_back"]):
                await state.clear()
                await delete_all_bot_messages(m.from_user.id, bot_instance)
                msg = await m.answer(T["admin_panel"], reply_markup=kb_admin())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            email = m.text.strip()
            
            try:
                if not validate_email(email):
                    raise ValueError(T["err_mail"]) 
                
                success = await admin_delete_account(pool, email)
                await state.clear()
                await delete_all_bot_messages(m.from_user.id, bot_instance)
                
                if success:
                    msg = await m.answer(T["admin_delete_success"].format(email=email), reply_markup=kb_admin_back())
                else:
                    msg = await m.answer(T["admin_delete_error"].format(error=T["account_not_found_error"]), reply_markup=kb_admin_back())
            
            except Exception as e:
                logger.error(f"Admin delete account error: {e}")
                await state.clear()
                await delete_all_bot_messages(m.from_user.id, bot_instance)
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
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            if c.from_user.id != ADMIN_ID:
                bot = bot_instance
                msg = await bot.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            try:
                from ..config.settings import reload_config
                bot = bot_instance
                await reload_config(bot)
                msg = await bot.send_message(c.from_user.id, T["reload_config_success"], reply_markup=kb_admin())
            except Exception as e:
                logger.error(f"Reload config error: {e}")
                bot = bot_instance
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
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
            record_message(c.from_user.id, msg, "command")
            await c.answer()

