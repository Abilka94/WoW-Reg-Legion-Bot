"""
Клавиатуры для пользователей
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..config.settings import CONFIG
from ..config.translations import TRANSLATIONS as T

def kb_main(is_admin: bool = False):
    """Главное меню"""
    buttons = []
    
    if CONFIG["features"]["registration"]:
        buttons.append([InlineKeyboardButton(text=T["menu_reg"], callback_data="reg_start")])
    
    buttons.append([
        InlineKeyboardButton(text=T["menu_info"], callback_data="show_info"),
        InlineKeyboardButton(text=T["menu_news"], callback_data="show_news")
    ])
    
    row = []
    if CONFIG["features"]["account_management"]:
        row.append(InlineKeyboardButton(text=T["menu_acc"], callback_data="my_account"))
    if row:
        buttons.append(row)
    
    if is_admin:
        buttons.append([InlineKeyboardButton(text=T["menu_admin"], callback_data="open_admin_panel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_wizard(step):
    """Клавиатура для мастера регистрации"""
    btns = []
    if step > 0:
        btns.append(InlineKeyboardButton(text=T["back"], callback_data="wiz_back"))
    btns.append(InlineKeyboardButton(text=T["cancel"], callback_data="wiz_cancel"))
    return InlineKeyboardMarkup(inline_keyboard=[btns])

def kb_back():
    """Клавиатура с кнопкой назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["to_main"], callback_data="back_to_main")]
    ])

def kb_account_list(accounts, selected_email=None):
    """Клавиатура со списком аккаунтов"""
    buttons = []
    
    for email, username, is_temp, temp_password in accounts:
        text = f"📧 {email} {'✅' if email == selected_email else ''}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"select_account_{email}")])
    
    if selected_email:
        if CONFIG["features"]["account_management"]:
            buttons.append([InlineKeyboardButton(text=T["menu_fgt"], callback_data=f"reset_password_{selected_email}")])
            buttons.append([InlineKeyboardButton(text=T["change_password_prompt"], callback_data="change_password")])
            buttons.append([InlineKeyboardButton(text=T["delete_account_prompt"], callback_data=f"delete_account_{selected_email}")])
    
    buttons.append([InlineKeyboardButton(text=T["to_main"], callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)