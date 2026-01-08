"""
Утилиты для валидации данных
"""
import re
from .email_providers import KNOWN_EMAIL_PROVIDERS

# Более строгое регулярное выражение для проверки email
# Проверяет: локальная часть (до @) и домен (после @)
EMAIL_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$")

def validate_email(email: str, strict: bool = True) -> tuple[bool, str]:
    """
    Проверяет корректность email с проверкой известных провайдеров
    
    Args:
        email: Email адрес для проверки
        strict: Если True, проверяет наличие известного провайдера
    
    Returns:
        Кортеж (is_valid, error_message)
        is_valid: True если email валиден, False иначе
        error_message: Сообщение об ошибке (пустая строка если валиден)
    """
    if not email:
        return False, "Email не может быть пустым"
    
    # Нормализуем email (приводим к нижнему регистру, убираем пробелы)
    email = email.strip().lower()
    
    # Проверка базового формата
    if not EMAIL_RE.fullmatch(email):
        return False, "Некорректный формат email адреса"
    
    # Проверка длины
    if len(email) > 254:  # RFC 5321 максимальная длина
        return False, "Email слишком длинный (максимум 254 символа)"
    
    if len(email) < 5:  # Минимум: a@b.c
        return False, "Email слишком короткий"
    
    # Разделяем на локальную часть и домен
    try:
        local_part, domain = email.split('@', 1)
    except ValueError:
        return False, "Email должен содержать символ @"
    
    # Проверка локальной части
    if len(local_part) > 64:  # RFC 5321 максимальная длина локальной части
        return False, "Локальная часть email слишком длинная (максимум 64 символа)"
    
    if len(local_part) == 0:
        return False, "Локальная часть email не может быть пустой"
    
    # Проверка на запрещенные символы в начале/конце локальной части
    if local_part.startswith('.') or local_part.endswith('.'):
        return False, "Локальная часть не может начинаться или заканчиваться точкой"
    
    if '..' in local_part:
        return False, "Локальная часть не может содержать две точки подряд"
    
    # Проверка домена
    if len(domain) > 253:  # RFC 5321 максимальная длина домена
        return False, "Домен слишком длинный (максимум 253 символа)"
    
    if len(domain) < 4:  # Минимум: a.b
        return False, "Домен слишком короткий"
    
    # Проверка на запрещенные символы в домене
    if domain.startswith('.') or domain.endswith('.'):
        return False, "Домен не может начинаться или заканчиваться точкой"
    
    if '..' in domain:
        return False, "Домен не может содержать две точки подряд"
    
    # Проверка TLD (должен быть минимум 2 символа)
    domain_parts = domain.split('.')
    if len(domain_parts) < 2:
        return False, "Домен должен содержать как минимум одну точку"
    
    tld = domain_parts[-1]
    if len(tld) < 2:
        return False, "Доменная зона должна содержать минимум 2 символа"
    
    # Строгая проверка: домен должен быть в списке известных провайдеров
    if strict:
        if domain not in KNOWN_EMAIL_PROVIDERS:
            return False, f"Используйте email от известного почтового провайдера. Домен '{domain}' не поддерживается."
    
    return True, ""

def validate_email_simple(email: str) -> bool:
    """
    Простая проверка email (для обратной совместимости)
    
    Args:
        email: Email адрес для проверки
    
    Returns:
        True если email валиден, False иначе
    """
    is_valid, _ = validate_email(email, strict=False)
    return is_valid

def validate_nickname(nick):
    """Проверяет корректность никнейма (только латинские буквы и цифры)"""
    return re.fullmatch(r'[A-Za-z0-9]+', nick) is not None

def validate_password(pwd):
    """Проверяет пароль на отсутствие кириллицы"""
    return not re.search(r'[А-Яа-яЁё]', pwd)

def filter_text(text: str, max_length: int = 500, allow_email_chars: bool = False) -> str:
    """
    Фильтрует текст: удаляет эмодзи и оставляет только разрешенные символы
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина текста
        allow_email_chars: Если True, разрешает символы для email (@, точка и т.д.)
    
    Returns:
        Отфильтрованный текст
    """
    if not text:
        return ""
    
    # Удаляем эмодзи (Unicode диапазоны эмодзи)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # эмоциональные символы
        "\U0001F300-\U0001F5FF"  # символы и пиктограммы
        "\U0001F680-\U0001F6FF"  # транспорт и карты
        "\U0001F1E0-\U0001F1FF"  # флаги
        "\U00002702-\U000027B0"  # различные символы
        "\U000024C2-\U0001F251"  # дополнительные символы
        "\U0001F900-\U0001F9FF"  # дополнительные эмодзи
        "\U0001FA00-\U0001FA6F"  # шахматы и другие
        "\U0001FA70-\U0001FAFF"  # символы и пиктограммы
        "\U00002600-\U000026FF"  # различные символы
        "\U00002700-\U000027BF"  # Dingbats
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Оставляем только буквы (латиница, кириллица), цифры, пробелы и основные знаки препинания
    if allow_email_chars:
        # Для email разрешаем больше символов: буквы, цифры, @, точка, дефис, подчеркивание
        allowed_pattern = re.compile(r'[^\w\s@\.\-]', re.UNICODE)
    else:
        # Разрешенные символы: буквы, цифры, пробелы, точка, запятая, дефис, подчеркивание
        allowed_pattern = re.compile(r'[^\w\s\.\,\-\_]', re.UNICODE)
    text = allowed_pattern.sub('', text)
    
    # Удаляем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    
    # Обрезаем до максимальной длины
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

def is_text_only(message) -> bool:
    """
    Проверяет, является ли сообщение только текстом (без файлов, стикеров и т.д.)
    
    Args:
        message: Объект Message из aiogram
    
    Returns:
        True если сообщение содержит только текст, False иначе
    """
    # Проверяем наличие нежелательных типов контента
    if message.sticker or message.animation or message.document or message.photo:
        return False
    if message.video or message.video_note or message.voice or message.audio:
        return False
    if message.location or message.venue or message.contact:
        return False
    if message.poll or message.dice or message.game:
        return False
    if message.story or message.video_chat_started or message.video_chat_ended:
        return False
    
    # Если есть текст - это текстовое сообщение
    return message.text is not None