"""
Валидация данных — автономная копия для VK-бота.
"""
import re
from .email_providers import KNOWN_EMAIL_PROVIDERS

EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$"
)


def validate_email(email: str, strict: bool = True) -> tuple[bool, str]:
    if not email:
        return False, "Email не может быть пустым"

    email = email.strip().lower()

    if not EMAIL_RE.fullmatch(email):
        return False, "Некорректный формат email адреса"

    if len(email) > 254:
        return False, "Email слишком длинный (максимум 254 символа)"

    if len(email) < 5:
        return False, "Email слишком короткий"

    try:
        local_part, domain = email.split("@", 1)
    except ValueError:
        return False, "Email должен содержать символ @"

    if len(local_part) > 64:
        return False, "Локальная часть email слишком длинная (максимум 64 символа)"

    if not local_part:
        return False, "Локальная часть email не может быть пустой"

    if local_part.startswith(".") or local_part.endswith("."):
        return False, "Локальная часть не может начинаться или заканчиваться точкой"

    if ".." in local_part:
        return False, "Локальная часть не может содержать две точки подряд"

    if len(domain) > 253:
        return False, "Домен слишком длинный (максимум 253 символа)"

    if len(domain) < 4:
        return False, "Домен слишком короткий"

    if domain.startswith(".") or domain.endswith("."):
        return False, "Домен не может начинаться или заканчиваться точкой"

    if ".." in domain:
        return False, "Домен не может содержать две точки подряд"

    domain_parts = domain.split(".")
    if len(domain_parts) < 2:
        return False, "Домен должен содержать как минимум одну точку"

    tld = domain_parts[-1]
    if len(tld) < 2:
        return False, "Доменная зона должна содержать минимум 2 символа"

    if strict:
        if domain not in KNOWN_EMAIL_PROVIDERS:
            return False, f"Используйте email от известного почтового провайдера. Домен '{domain}' не поддерживается."

    return True, ""


def validate_nickname(nick: str) -> bool:
    """Только латинские буквы и цифры."""
    return re.fullmatch(r"[A-Za-z0-9]+", nick) is not None


def validate_password(pwd: str) -> tuple[bool, str]:
    if not pwd:
        return False, "Пароль не может быть пустым"

    if len(pwd) < 8:
        return False, "Пароль должен содержать минимум 8 символов"

    if re.search(r"[А-Яа-яЁё]", pwd):
        return False, "Пароль должен содержать только латинские буквы. Кириллица запрещена."

    allowed = re.compile(r"^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?/]+$")
    if not allowed.match(pwd):
        return False, "Пароль содержит недопустимые символы. Используйте только латинские буквы, цифры и основные специальные символы."

    return True, ""


def check_password_strength(pwd: str) -> tuple[bool, str]:
    if not pwd or len(pwd) < 8:
        return True, ""

    if re.match(r"^[A-Za-z]+$", pwd):
        return False, "⚠️ Ваш пароль содержит только буквы. Рекомендуется добавить цифры и специальные символы для повышения безопасности."

    if re.match(r"^\d+$", pwd):
        return False, "⚠️ Ваш пароль содержит только цифры. Рекомендуется добавить буквы и специальные символы для повышения безопасности."

    if re.match(r"^[a-z]+[0-9]*$", pwd) or re.match(r"^[A-Z]+[0-9]*$", pwd):
        if len(pwd) < 10:
            return False, "⚠️ Ваш пароль содержит только буквы одного регистра. Рекомендуется использовать заглавные и строчные буквы, цифры и специальные символы."

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/]", pwd) and len(pwd) < 10:
        return False, "⚠️ Ваш пароль довольно короткий и не содержит специальных символов. Рекомендуется использовать пароль длиной от 10 символов с буквами, цифрами и специальными символами."

    return True, ""
