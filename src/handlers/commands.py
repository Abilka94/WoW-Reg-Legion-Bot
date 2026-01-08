"""
Обработчики команд
"""
import logging
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..config.settings import CONFIG, BOT_VERSION, ADMIN_ID
from ..config.translations import TRANSLATIONS as T
from ..keyboards.user_keyboards import kb_main, kb_back
from ..keyboards.admin_keyboards import kb_admin, kb_admin_back
from ..utils.notifications import record_message, delete_all_bot_messages, delete_user_message
from ..utils.file_cache import FileCache

logger = logging.getLogger("bot")

# Кэш файлов
news_cache = FileCache("news.txt")
info_cache = FileCache("connection_info.txt")

def register_command_handlers(dp, pool, bot_instance):
    """Регистрирует обработчики команд"""
    
    @dp.message(Command("start"))
    async def cmd_start(m: Message, state: FSMContext):
        await state.clear()
        await delete_all_bot_messages(m.from_user.id, bot_instance)
        msg = await m.answer(T["start"], reply_markup=kb_main())
        record_message(m.from_user.id, msg, "command")
        await delete_user_message(m)

    @dp.message(Command("version"))
    async def cmd_version(m: Message):
        await delete_all_bot_messages(m.from_user.id, bot_instance)
        text = f"{T['version_pre']}{BOT_VERSION}"
        msg = await m.answer(text, reply_markup=kb_back())
        record_message(m.from_user.id, msg, "command")
        await delete_user_message(m)
    if CONFIG["features"]["admin_panel"]:

        @dp.message(Command("admin"))
        async def cmd_admin(m: Message, state: FSMContext):
            if not CONFIG["features"]["admin_panel"]:
                msg = await m.answer(T["feature_disabled"], reply_markup=kb_back())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            await state.clear()
            await delete_all_bot_messages(m.from_user.id, bot_instance)
            
            if m.from_user.id != ADMIN_ID:
                msg = await m.answer(T["no_access"], reply_markup=kb_back())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            msg = await m.answer(T["admin_panel"], reply_markup=kb_admin())
            record_message(m.from_user.id, msg, "command")
            await delete_user_message(m)

    if CONFIG["features"]["admin_reload_config"]:
        @dp.message(Command("reload_config"))
        async def cmd_reload_config(m: Message, state: FSMContext):
            if not CONFIG["features"]["admin_reload_config"]:
                msg = await m.answer(T["feature_disabled"], reply_markup=kb_back())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            await state.clear()
            await delete_all_bot_messages(m.from_user.id, bot_instance)
            
            if m.from_user.id != ADMIN_ID:
                msg = await m.answer(T["no_access"], reply_markup=kb_back())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            try:
                from ..config.settings import reload_config
                await reload_config(bot_instance)
                msg = await m.answer(T["reload_config_success"], reply_markup=kb_admin())
            except Exception as e:
                logger.error(f"Ошибка при перезагрузке конфигурации: {e}")
                msg = await m.answer(T["reload_config_error"].format(error=str(e)), reply_markup=kb_admin())
            
            record_message(m.from_user.id, msg, "command")
            await delete_user_message(m)

def register_callback_handlers(dp, pool, bot_instance):
    """Регистрирует обработчики callback'ов"""
    
    @dp.callback_query(F.data == "back_to_main")
    async def cb_back(c: CallbackQuery, state: FSMContext):
        await state.clear()
        await delete_all_bot_messages(c.from_user.id, bot_instance)
        try:
            msg = await c.message.edit_text(T["start"], reply_markup=kb_main())
        except:
            msg = await bot_instance.send_message(c.from_user.id, T["start"], reply_markup=kb_main())
        record_message(c.from_user.id, msg, "command")
        await c.answer()

    if CONFIG["features"]["admin_panel"]:
        @dp.callback_query(F.data == "admin_back")
        async def cb_admin_back(c: CallbackQuery, state: FSMContext):
            if not CONFIG["features"]["admin_panel"]:
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
                msg = await c.message.edit_text(T["admin_panel"], reply_markup=kb_admin())
            except:
                msg = await bot_instance.send_message(c.from_user.id, T["admin_panel"], reply_markup=kb_admin())
            record_message(c.from_user.id, msg, "command")
            await c.answer()

    @dp.callback_query(F.data == "show_info")
    async def cb_info(c: CallbackQuery, state: FSMContext):
        await state.clear()
        await delete_all_bot_messages(c.from_user.id, bot_instance)
        txt = await info_cache.get()
        msg = await bot_instance.send_message(c.from_user.id, txt or "—", reply_markup=kb_back())
        record_message(c.from_user.id, msg, "command")
        await c.answer()

    @dp.callback_query(F.data == "show_news")
    async def cb_news(c: CallbackQuery, state: FSMContext):
        await state.clear()
        await delete_all_bot_messages(c.from_user.id, bot_instance)
        txt = await news_cache.get()
        msg = await bot_instance.send_message(c.from_user.id, txt or "—", reply_markup=kb_back())
        record_message(c.from_user.id, msg, "command")
        await c.answer()
    @dp.callback_query(F.data == "error_ok")
    async def cb_error_ok(c: CallbackQuery):
        try:
            await c.message.delete()
        except:
            pass
        await c.answer()