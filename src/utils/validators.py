"""
Утилиты для валидации данных
"""
import re

# Регулярное выражение для проверки email
EMAIL_RE = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

def validate_email(email):
    """Проверяет корректность email"""
    return EMAIL_RE.fullmatch(email) is not None

def validate_nickname(nick):
    """Проверяет корректность никнейма (только латинские буквы и цифры)"""
    return re.fullmatch(r'[A-Za-z0-9]+', nick) is not None

def validate_password(pwd):
    """Проверяет пароль на отсутствие кириллицы"""
    return not re.search(r'[А-Яа-яЁё]', pwd)