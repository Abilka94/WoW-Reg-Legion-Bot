"""
База популярных email провайдеров для валидации
"""
from typing import Tuple

# Популярные email провайдеры (топ-70+ самых распространенных)
POPULAR_EMAIL_PROVIDERS = {
    # Международные популярные
    'gmail.com',
    'yahoo.com',
    'outlook.com',
    'hotmail.com',
    'mail.com',
    'protonmail.com',
    'icloud.com',
    'aol.com',
    'gmx.com',
    'zoho.com',
    'live.com',
    'msn.com',
    'inbox.com',
    'fastmail.com',
    'tutanota.com',
    'hushmail.com',
    'rediffmail.com',
    'mailinator.com',
    
    # Яндекс (все домены, включая международные)
    'yandex.ru',  # Основной российский домен
    'yandex.com',  # Международный домен Яндекс
    'ya.ru',  # Короткий домен Яндекс
    'yandex.by',  # Беларусь
    'yandex.kz',  # Казахстан
    'yandex.ua',  # Украина
    'yandex.com.tr',  # Турция
    'mail.yandex.ru',  # Альтернативный формат (редко используется)
    
    # Mail.ru Group (все домены)
    'mail.ru',  # Основной домен
    'bk.ru',  # Бывший Bigmail.ru
    'list.ru',  # Бывший List.ru
    'inbox.ru',  # Бывший Inbox.ru
    'e.mail.ru',  # Альтернативный формат (редко используется)
    
    # Rambler
    'rambler.ru',
    'lenta.ru',  # Rambler Lenta (почтовый сервис)
    'myrambler.ru',  # Rambler почта
    
    # Другие популярные
    'qq.com',
    '163.com',
    '126.com',
    'sina.com',
    'sohu.com',
    'foxmail.com',
    'naver.com',
    'daum.net',
    'hanmail.net',
    'web.de',
    'gmx.de',
    't-online.de',
    'orange.fr',
    'laposte.net',
    'libero.it',
    'virgilio.it',
    'tiscali.it',
    'uol.com.br',
    'bol.com.br',
    'terra.com.br',
    'ig.com.br',
    'me.com',
    'mac.com',
    'icloud.com',
    'pm.me',
    'proton.me',
    'tutanota.de',
    'cock.li',
    'disroot.org',
    'riseup.net',
}

# Домены, которые точно не существуют (для проверки)
FAKE_DOMAINS = {
    'example.com',
    'test.com',
    'invalid.com',
    'fake.com',
    'nonexistent.com',
    'test.test',
    'example.org',
    'test.org',
}

def get_email_domain(email: str) -> str:
    """Извлекает домен из email адреса"""
    if '@' not in email:
        return ''
    return email.split('@')[1].lower().strip()

def is_popular_provider(email: str) -> bool:
    """Проверяет, является ли провайдер популярным"""
    domain = get_email_domain(email)
    return domain in POPULAR_EMAIL_PROVIDERS

def is_fake_domain(email: str) -> bool:
    """Проверяет, является ли домен тестовым/фейковым"""
    domain = get_email_domain(email)
    return domain in FAKE_DOMAINS

def validate_email_provider(email: str) -> Tuple[bool, str]:
    """
    Валидирует email провайдер
    
    Returns:
        (is_valid, error_message)
        is_valid: True если провайдер валиден или неизвестен (не блокируем)
        error_message: Сообщение об ошибке, если провайдер невалиден
    """
    domain = get_email_domain(email)
    
    if not domain:
        return False, "Некорректный формат email адреса"
    
    # Проверяем на фейковые домены
    if is_fake_domain(email):
        return False, f"Домен '{domain}' не является реальным email провайдером. Пожалуйста, используйте реальный email адрес."
    
    # Если провайдер популярный - всё ок
    if is_popular_provider(email):
        return True, ""
    
    # Для неизвестных провайдеров - предупреждение, но не блокируем
    # Можно добавить дополнительную проверку формата домена
    if len(domain) < 4:
        return False, f"Домен '{domain}' слишком короткий. Возможно, это опечатка."
    
    # Проверка на подозрительные домены (например, только цифры)
    if domain.replace('.', '').isdigit():
        return False, f"Домен '{domain}' выглядит подозрительно. Пожалуйста, используйте реальный email провайдер."
    
    # Если домен выглядит нормально, но не в списке - разрешаем с предупреждением
    # (можно сделать строже, если нужно)
    return True, ""
