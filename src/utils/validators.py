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