"""
Клавиатуры для пользователей
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..config.settings import CONFIG
from ..config.translations import TRANSLATIONS as T

def kb_main():
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
    if CONFIG["features"]["password_reset"]:
        row.append(InlineKeyboardButton(text=T["menu_fgt"], callback_data="forgot"))
    if row:
        buttons.append(row)
    
    # Добавляем кнопку валютного магазина
    if CONFIG.get("features", {}).get("currency_shop", False) and CONFIG.get("currency_shop", {}).get("enabled", False):
        buttons.append([InlineKeyboardButton(text="💰 Купить валюту", callback_data="coins_menu")])
    
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
            buttons.append([InlineKeyboardButton(text=T["change_password_prompt"], callback_data="change_password")])
            buttons.append([InlineKeyboardButton(text=T["delete_account_prompt"], callback_data=f"delete_account_{selected_email}")])
    
    buttons.append([InlineKeyboardButton(text=T["to_main"], callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_coins_menu():
    """Клавиатура для меню валюты"""
    buttons = [
        [InlineKeyboardButton(text="💰 Купить валюту", callback_data="buy_coins")],
        [InlineKeyboardButton(text="💳 Мой баланс", callback_data="check_balance")],
        [InlineKeyboardButton(text=T["to_main"], callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_coins_packages():
    """Клавиатура с пакетами валюты"""
    buttons = [
        [InlineKeyboardButton(text="🪙 100 монет - 50₽", callback_data="buy_coins_100")],
        [InlineKeyboardButton(text="🪙 200 монет - 90₽", callback_data="buy_coins_200")],
        [InlineKeyboardButton(text="💰 300 монет - 130₽", callback_data="buy_coins_300")],
        [InlineKeyboardButton(text="💰 400 монет - 160₽", callback_data="buy_coins_400")],
        [InlineKeyboardButton(text="💎 500 монет - 200₽", callback_data="buy_coins_500")],
        [InlineKeyboardButton(text="✍️ Свое количество", callback_data="buy_coins_custom")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="coins_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_account_select_for_coins(accounts):
    """Клавиатура для выбора аккаунта для добавления валюты"""
    buttons = []
    
    for email, username, is_temp, temp_password, coins in accounts:
        text = f"📧 {email} (💰 {coins} монет)"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"coins_select_{email}")])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="coins_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)