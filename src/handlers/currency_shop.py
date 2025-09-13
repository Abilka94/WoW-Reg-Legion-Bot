"""
Обработчики для магазина валюты
"""
import logging
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from ..config.settings import CONFIG, BOT_VERSION
from ..config.translations import TRANSLATIONS as T
from ..config.currency_config import CURRENCY_SHOP_CONFIG
from ..states.user_states import CurrencyShopStates
from ..keyboards.user_keyboards import kb_main, kb_back, kb_coins_menu, kb_coins_packages, kb_account_select_for_coins
from ..utils.notifications import record_message, delete_all_bot_messages, delete_user_message
from ..database.user_operations import get_user_accounts_with_coins, add_coins_to_account

logger = logging.getLogger("bot")

def register_currency_shop_handlers(dp, pool, bot_instance):
    """Регистрирует обработчики магазина валюты"""
    
    if not CONFIG["features"].get("currency_shop", False):
        return
    
    @dp.callback_query(F.data == "coins_menu")
    async def cb_coins_menu(c: CallbackQuery, state: FSMContext):
        if not CONFIG["features"].get("currency_shop", False) or not CONFIG.get("currency_shop", {}).get("enabled", False):
            await c.answer(T["feature_disabled"], show_alert=True)
            return
        
        if not CURRENCY_SHOP_CONFIG.get("shop_enabled", False):
            await c.answer(T["shop_disabled"], show_alert=True)
            return
        
        await state.clear()
        await delete_all_bot_messages(c.from_user.id, bot_instance)
        
        try:
            msg = await c.message.edit_text(T["coins_menu"], reply_markup=kb_coins_menu())
        except TelegramBadRequest:
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, T["coins_menu"], reply_markup=kb_coins_menu())
        
        record_message(c.from_user.id, msg, "command")
        await c.answer()

    @dp.callback_query(F.data == "buy_coins")
    async def cb_buy_coins(c: CallbackQuery, state: FSMContext):
        if not CONFIG["features"].get("currency_shop", False) or not CONFIG.get("currency_shop", {}).get("purchase", False):
            await c.answer(T["purchase_disabled"], show_alert=True)
            return
        
        await state.clear()
        await delete_all_bot_messages(c.from_user.id, bot_instance)
        
        try:
            msg = await c.message.edit_text(T["buy_coins"], reply_markup=kb_coins_packages())
        except TelegramBadRequest:
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, T["buy_coins"], reply_markup=kb_coins_packages())
        
        record_message(c.from_user.id, msg, "command")
        await c.answer()

    @dp.callback_query(F.data == "check_balance")
    async def cb_check_balance(c: CallbackQuery, state: FSMContext):
        if not CONFIG["features"].get("currency_shop", False) or not CONFIG.get("currency_shop", {}).get("balance_check", False):
            await c.answer(T["feature_disabled"], show_alert=True)
            return
        
        await state.clear()
        await delete_all_bot_messages(c.from_user.id, bot_instance)
        
        accounts = await get_user_accounts_with_coins(pool, c.from_user.id)
        
        if not accounts:
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, T["no_accounts_for_coins"], reply_markup=kb_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()
            return
        
        accounts_info = "\n".join([
            f"📧 {email} - 💰 {coins} монет"
            for email, username, is_temp, temp_password, coins in accounts
        ])
        
        text = T["account_balance"].format(accounts_info=accounts_info)
        
        try:
            msg = await c.message.edit_text(text, reply_markup=kb_back())
        except TelegramBadRequest:
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, text, reply_markup=kb_back())
        
        record_message(c.from_user.id, msg, "command")
        await c.answer()

    # Обработчики покупки пакетов валюты
    @dp.callback_query(F.data.startswith("buy_coins_"))
    async def cb_buy_coins_package(c: CallbackQuery, state: FSMContext):
        if not CONFIG["features"].get("currency_shop", False) or not CONFIG.get("currency_shop", {}).get("purchase", False):
            await c.answer(T["purchase_disabled"], show_alert=True)
            return
        
        package = c.data.replace("buy_coins_", "")
        
        if package == "custom":
            if not CURRENCY_SHOP_CONFIG.get("custom_purchase", {}).get("enabled", False):
                await c.answer(T["custom_purchases_disabled"], show_alert=True)
                return
            
            await state.set_state(CurrencyShopStates.custom_amount)
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, T["enter_coins_amount"], reply_markup=kb_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()
            return
        
        # Проверяем, есть ли такой пакет в конфигурации
        packages = CURRENCY_SHOP_CONFIG.get("currency_packages", {})
        if package not in packages:
            await c.answer(T["unknown_package"], show_alert=True)
            return
        
        amount = packages[package]["amount"]
        await state.update_data(amount=amount, package=package)
        
        # Получаем аккаунты пользователя
        accounts = await get_user_accounts_with_coins(pool, c.from_user.id)
        
        if not accounts:
            await delete_all_bot_messages(c.from_user.id, bot_instance)
            bot = bot_instance
            msg = await bot.send_message(c.from_user.id, T["no_accounts_for_coins"], reply_markup=kb_back())
            record_message(c.from_user.id, msg, "command")
            await c.answer()
            return
        
        await delete_all_bot_messages(c.from_user.id, bot_instance)
        bot = bot_instance
        msg = await bot.send_message(c.from_user.id, T["select_account_for_coins"], reply_markup=kb_account_select_for_coins(accounts))
        record_message(c.from_user.id, msg, "command")
        await c.answer()

    @dp.callback_query(F.data.startswith("coins_select_"))
    async def cb_coins_select_account(c: CallbackQuery, state: FSMContext):
        if not CONFIG["features"].get("currency_shop", False) or not CONFIG.get("currency_shop", {}).get("purchase", False):
            await c.answer(T["purchase_disabled"], show_alert=True)
            return
        
        email = c.data.replace("coins_select_", "")
        data = await state.get_data()
        amount = data.get("amount")
        
        if not amount:
            await c.answer(T["coins_amount_error"], show_alert=True)
            return
        
        # Имитация покупки (заглушка)
        if CURRENCY_SHOP_CONFIG.get("payment_stub_enabled", False):
            # Добавляем монеты на аккаунт
            new_balance = await add_coins_to_account(pool, email, amount)
            
            if new_balance is not None:
                await state.clear()
                await delete_all_bot_messages(c.from_user.id, bot_instance)
                
                text = T["coins_purchased"].format(amount=amount, email=email, balance=new_balance)
                bot = bot_instance
                msg = await bot.send_message(c.from_user.id, text, reply_markup=kb_main())
                record_message(c.from_user.id, msg, "command")
                await c.answer()
            else:
                await c.answer(T["coins_purchase_error"], show_alert=True)
        else:
            await c.answer(T["purchase_disabled"], show_alert=True)

    @dp.message(CurrencyShopStates.custom_amount)
    async def step_custom_amount(m: Message, state: FSMContext):
        text = m.text.strip()
        
        if text in (T["to_main"], T["cancel"]):
            await state.clear()
            msg = await m.answer(T["start"].format(version=BOT_VERSION), reply_markup=kb_main())
            record_message(m.from_user.id, msg, "command")
            await delete_user_message(m)
            return
        
        try:
            amount = int(text)
            custom_config = CURRENCY_SHOP_CONFIG.get("custom_purchase", {})
            min_amount = custom_config.get("min_amount", 1)
            max_amount = custom_config.get("max_amount", 1000)
            
            if amount < min_amount or amount > max_amount:
                msg = await m.answer(T["invalid_coins_amount"], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="OK", callback_data="error_ok")]]))
                record_message(m.from_user.id, msg, "error")
                await delete_user_message(m)
                return
            
            await state.update_data(amount=amount)
            
            # Получаем аккаунты пользователя
            accounts = await get_user_accounts_with_coins(pool, m.from_user.id)
            
            if not accounts:
                await delete_all_bot_messages(m.from_user.id, bot_instance)
                msg = await m.answer(T["no_accounts_for_coins"], reply_markup=kb_back())
                record_message(m.from_user.id, msg, "command")
                await delete_user_message(m)
                return
            
            await delete_all_bot_messages(m.from_user.id, bot_instance)
            msg = await m.answer(T["select_account_for_coins"], reply_markup=kb_account_select_for_coins(accounts))
            record_message(m.from_user.id, msg, "command")
            await delete_user_message(m)
            
        except ValueError:
            msg = await m.answer(T["invalid_coins_amount"], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="OK", callback_data="error_ok")]]))
            record_message(m.from_user.id, msg, "error")
            await delete_user_message(m)