"""
Клавиатуры для администратора
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..config.settings import CONFIG
from ..config.translations import TRANSLATIONS as T

def kb_admin():
    """Панель администратора"""
    buttons = []
    
    if CONFIG["features"]["admin_check_db"]:
        buttons.append([InlineKeyboardButton(text=T["admin_db"], callback_data="admin_check_db")])
    
    if CONFIG["features"]["admin_broadcast"]:
        buttons.append([InlineKeyboardButton(text=T["admin_bcast"], callback_data="admin_broadcast")])
    
    if CONFIG["features"]["admin_delete_account"]:
        buttons.append([InlineKeyboardButton(text=T["admin_delete_account"], callback_data="admin_delete_account")])
    
    if CONFIG["features"]["admin_download_log"]:
        buttons.append([InlineKeyboardButton(text=T["admin_log"], callback_data="admin_download_log")])
    
    if CONFIG["features"]["admin_reload_config"]:
        buttons.append([InlineKeyboardButton(text=T["admin_reload_config"], callback_data="admin_reload_config")])
    
    buttons.append([InlineKeyboardButton(text=T["admin_main"], callback_data="admin_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_admin_back():
    """Кнопка возврата в админ панель"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["admin_back"], callback_data="admin_back")]
    ])