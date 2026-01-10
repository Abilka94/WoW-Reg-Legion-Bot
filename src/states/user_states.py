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
    delete_account_confirm = State()

class ChangePasswordStates(StatesGroup):
    """Состояния для смены пароля"""
    new_password = State()