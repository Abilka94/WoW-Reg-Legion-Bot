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
from ..utils.notifications import record_message, delete_all_bot_messages, delete_user_message, notify_admin, safe_edit_message
from ..database.user_operations import admin_delete_account, get_account_by_email

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
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            if c.from_user.id != ADMIN_ID:
                msg = await bot_instance.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            await state.set_state(AdminStates.broadcast_text)
            msg = await bot_instance.send_message(c.from_user.id, "Введите текст рассылки:", reply_markup=kb_admin_back())
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
            await delete_all_bot_messages(m.from_user.id, bot_instance)
            
            try:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT telegram_id FROM users")
                        users = await cur.fetchall()
                
                ok = fail = 0
                for (uid,) in users:
                    try:
                        await bot_instance.send_message(uid, m.text)
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
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            if c.from_user.id != ADMIN_ID:
                msg = await bot_instance.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            try:
                async with pool.acquire():
                    pass
                txt = T["db_ok"]
            except Exception as e:
                txt = f"❌ {e}"
                await notify_admin(bot_instance, str(e))
                logger.error(f"Ошибка проверки базы данных: {e}")
            
            msg = await bot_instance.send_message(c.from_user.id, txt, reply_markup=kb_admin_back())
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
                msg = await bot_instance.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            await state.set_state(AdminStates.delete_account_input)
            msg = await bot_instance.send_message(c.from_user.id, T["admin_delete_prompt"], reply_markup=kb_admin_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()

        @dp.message(AdminStates.delete_account_input)
        async def step_admin_delete_account(m: Message, state: FSMContext):
            if m.text.strip() in (T["cancel"], T["admin_back"]):
                await state.clear()
                await delete_all_bot_messages(m.from_user.id, bot_instance)
                msg = await bot_instance.send_message(m.from_user.id, T["admin_panel"], reply_markup=kb_admin())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            email = m.text.strip()
            
            try:
                is_valid, error_msg = validate_email(email, strict=True)
                if not is_valid:
                    msg = await bot_instance.send_message(m.from_user.id, T["admin_delete_error"].format(error=error_msg or "Некорректный e-mail"), reply_markup=kb_admin_back())
                    record_message(m.from_user.id, msg, "command")
                    await delete_user_message(m)
                    return
                
                # Получаем информацию об аккаунте
                username, telegram_id = await get_account_by_email(pool, email)
                if not username:
                    msg = await bot_instance.send_message(m.from_user.id, T["admin_delete_error"].format(error="Аккаунт не найден"), reply_markup=kb_admin_back())
                    record_message(m.from_user.id, msg, "command")
                    await delete_user_message(m)
                    return
                
                # Сохраняем данные для подтверждения
                await state.update_data(email=email, username=username, telegram_id=telegram_id)
                await state.set_state(AdminStates.delete_account_confirm)
                
                # Показываем предупреждение с подтверждением
                confirm_text = T["admin_delete_confirm"].format(email=email, username=username)
                confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text=T["admin_delete_confirm_yes"], callback_data="admin_confirm_delete"),
                        InlineKeyboardButton(text=T["admin_delete_confirm_no"], callback_data="admin_back")
                    ]
                ])
                
                await delete_user_message(m)
                # Отправляем новое сообщение с предупреждением
                msg = await bot_instance.send_message(m.from_user.id, confirm_text, reply_markup=confirm_keyboard)
                record_message(m.from_user.id, msg, "command")
            
            except Exception as e:
                logger.error(f"Ошибка при получении информации об аккаунте: {e}")
                await state.clear()
                msg = await bot_instance.send_message(m.from_user.id, T["admin_delete_error"].format(error=str(e)), reply_markup=kb_admin_back())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)

        @dp.callback_query(F.data == "admin_confirm_delete")
        async def cb_admin_confirm_delete(c: CallbackQuery, state: FSMContext):
            if c.from_user.id != ADMIN_ID:
                await c.answer(T["no_access"], show_alert=True)
                return
            
            data = await state.get_data()
            email = data.get("email")
            username = data.get("username")
            telegram_id = data.get("telegram_id")
            
            if not email:
                await c.answer("❌ Ошибка: данные не найдены", show_alert=True)
                await state.clear()
                await safe_edit_message(bot_instance, c, T["admin_panel"], reply_markup=kb_admin())
                return
            
            try:
                # Удаляем аккаунт
                success, deleted_telegram_id = await admin_delete_account(pool, email)
                await state.clear()
                
                if success:
                    # Отправляем уведомление пользователю, если он существует
                    if deleted_telegram_id:
                        try:
                            notification_text = T["account_deleted_by_admin"].format(email=email, username=username)
                            await bot_instance.send_message(deleted_telegram_id, notification_text)
                            logger.info(f"Уведомление об удалении отправлено пользователю {deleted_telegram_id}")
                        except Exception as e:
                            logger.warning(f"Не удалось отправить уведомление пользователю {deleted_telegram_id}: {e}")
                    
                    # Уведомляем админа об успехе
                    await safe_edit_message(bot_instance, c, T["admin_delete_success"].format(email=email), reply_markup=kb_admin_back())
                else:
                    await safe_edit_message(bot_instance, c, T["admin_delete_error"].format(error="Не удалось удалить аккаунт"), reply_markup=kb_admin_back())
            
            except Exception as e:
                logger.error(f"Ошибка при удалении аккаунта админом: {e}")
                await state.clear()
                await safe_edit_message(bot_instance, c, T["admin_delete_error"].format(error=str(e)), reply_markup=kb_admin_back())
            
            await c.answer()

    if CONFIG["features"]["admin_reload_config"]:
        @dp.callback_query(F.data == "admin_reload_config")
        async def cb_admin_reload_config(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_reload_config"]:
                await c.answer(T["feature_disabled"], show_alert=True)
                return
            
            await state.clear()
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            if c.from_user.id != ADMIN_ID:
                msg = await bot_instance.send_message(c.from_user.id, T["no_access"], reply_markup=kb_back())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
                return
            
            try:
                from ..config.settings import reload_config
                await reload_config(bot_instance)
                msg = await bot_instance.send_message(c.from_user.id, T["reload_config_success"], reply_markup=kb_admin())
            except Exception as e:
                logger.error(f"Ошибка при перезагрузке конфигурации: {e}")
                msg = await bot_instance.send_message(c.from_user.id, T["reload_config_error"].format(error=str(e)), reply_markup=kb_admin())
            
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
            msg = await bot_instance.send_message(c.from_user.id, T["start"], reply_markup=kb_main(is_admin=c.from_user.id == ADMIN_ID))
            record_message(c.from_user.id, msg, "command")
            await c.answer()