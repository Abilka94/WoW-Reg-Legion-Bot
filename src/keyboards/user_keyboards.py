"""
Клавиатуры для пользователей
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..config.settings import CONFIG
from ..config.translations import TRANSLATIONS as T


def kb_main():
    """Главное меню"""
    buttons = []

    if CONFIG["features"].get("registration", False):
        buttons.append([InlineKeyboardButton(text=T["menu_reg"], callback_data="reg_start")])

    buttons.append([
        InlineKeyboardButton(text=T["menu_info"], callback_data="show_info"),
        InlineKeyboardButton(text=T["menu_news"], callback_data="show_news"),
    ])

    row = []
    if CONFIG["features"].get("account_management", False):
        row.append(InlineKeyboardButton(text=T["menu_acc"], callback_data="my_account"))
    if CONFIG["features"].get("password_reset", False):
        row.append(InlineKeyboardButton(text=T["menu_fgt"], callback_data="forgot"))
    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_wizard(step: int):
    """Клавиатура для мастера регистрации"""
    btns = []
    if step > 0:
        btns.append(InlineKeyboardButton(text=T["back"], callback_data="wiz_back"))
    btns.append(InlineKeyboardButton(text=T["cancel"], callback_data="wiz_cancel"))
    return InlineKeyboardMarkup(inline_keyboard=[btns])


def kb_back():
    """Клавиатура 'Назад' к главному меню"""
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=T["to_main"], callback_data="back_to_main")]])


def kb_account_list(accounts, selected_email=None):
    """Клавиатура со списком аккаунтов"""
    buttons = []

    for email, username, is_temp, temp_password in accounts:
        text = f"📧 {email} {'✅' if email == selected_email else ''}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"select_account_{email}")])

    if selected_email and CONFIG["features"].get("account_management", False):
        buttons.append([InlineKeyboardButton(text=T["change_password_btn"], callback_data="change_password")])
        buttons.append([InlineKeyboardButton(text=T["delete_account_prompt"], callback_data=f"delete_account_{selected_email}")])
        
        # Кнопка магазина валюты отображается ТОЛЬКО когда выбран конкретный аккаунт
        if CONFIG.get("features", {}).get("currency_shop", False) and CONFIG.get("currency_shop", {}).get("enabled", False):
            buttons.append([InlineKeyboardButton(text=T["btn_buy_coins"], callback_data="coins_menu")])

    buttons.append([InlineKeyboardButton(text=T["to_main"], callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_coins_menu():
    """Клавиатура меню валюты"""
    buttons = [
        [InlineKeyboardButton(text=T["btn_buy_coins"], callback_data="buy_coins")],
        [InlineKeyboardButton(text=T["btn_check_balance"], callback_data="check_balance")],
        [InlineKeyboardButton(text=T["to_main"], callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_coins_packages():
    """Клавиатура пакетов валюты"""
    buttons = [
        [InlineKeyboardButton(text=T["btn_pkg_100"], callback_data="buy_coins_100")],
        [InlineKeyboardButton(text=T["btn_pkg_200"], callback_data="buy_coins_200")],
        [InlineKeyboardButton(text=T["btn_pkg_300"], callback_data="buy_coins_300")],
        [InlineKeyboardButton(text=T["btn_pkg_400"], callback_data="buy_coins_400")],
        [InlineKeyboardButton(text=T["btn_pkg_500"], callback_data="buy_coins_500")],
        [InlineKeyboardButton(text=T["btn_pkg_custom"], callback_data="buy_coins_custom")],
        [InlineKeyboardButton(text=T["back"], callback_data="coins_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_account_select_for_coins(accounts):
    """Клавиатура выбора аккаунта для пополнения валюты"""
    buttons = []
    for email, username, is_temp, temp_password, coins in accounts:
        text = T["coins_entry"].format(email=email, coins=coins)
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"coins_select_{email}")])

    buttons.append([InlineKeyboardButton(text=T["back"], callback_data="coins_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

