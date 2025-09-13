"""
FSM States для различных процессов
"""
from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    """Состояния для процесса регистрации"""
    nick = State()
    pwd = State()
    mail = State()

class ForgotPasswordStates(StatesGroup):
    """Состояния для восстановления пароля"""
    email = State()

class AdminStates(StatesGroup):
    """Состояния для административных функций"""
    broadcast_text = State()
    delete_account_input = State()

class ChangePasswordStates(StatesGroup):
    """Состояния для смены пароля"""
    new_password = State()

class BuyCoinsStates(StatesGroup):
    """Состояния для покупки валюты"""
    selecting_account = State()
    entering_amount = State()

class CurrencyShopStates(StatesGroup):
    """Состояния для магазина валюты"""
    custom_amount = State()