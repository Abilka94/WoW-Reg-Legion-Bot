"""
Строковые константы состояний FSM.
В VK-версии FSM хранит строки, а не объекты StatesGroup.
"""

# Регистрация
REG_NICK = "reg:nick"
REG_PWD = "reg:pwd"
REG_PWD_WEAK = "reg:pwd_confirm_weak"
REG_MAIL = "reg:mail"

# Смена пароля
CHANGE_PWD = "change:new_password"
CHANGE_PWD_WEAK = "change:pwd_confirm_weak"

# Удаление аккаунта (подтверждение пользователем)
USER_DELETE_CONFIRM = "user:delete_confirm"

# Админ
ADMIN_BROADCAST = "admin:broadcast_text"
ADMIN_DELETE_INPUT = "admin:delete_account_input"
ADMIN_DELETE_CONFIRM = "admin:delete_account_confirm"
