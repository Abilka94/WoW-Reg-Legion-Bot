# WoW Registration Bot — Modular Version

Badges: version, Python, MIT, modular

Кратко: модульный Telegram‑бот для регистрации и управления аккаунтами WoW. Поддерживает MySQL, Redis (FSM), админ‑панель, сброс пароля и простую “витрину” валюты.

## Возможности
- Регистрация аккаунта и привязка к Telegram
- Сброс пароля и смена постоянного пароля
- Просмотр аккаунтов пользователя, удаление
- Админ‑панель: проверка БД, рассылка, выгрузка лога, удаление аккаунта, перезагрузка конфига
- Магазин валюты (заглушка) с выбором пакетов/своего количества

## Требования
- Python 3.11+
- aiogram 3.x, aiomysql, redis, python-dotenv

## Настройка
1) Установите зависимости: `pip install -r requirements.txt`
2) Создайте `.env` со значениями:
```
TOKEN=ваш_бот_токен
ADMIN_ID=ваш_telegram_id
DB_HOST=127.0.0.1
DB_PORT=3310
DB_USER=spp_user
DB_PASSWORD=password
DB_NAME=legion_auth
REDIS_DSN=redis://127.0.0.1:6379/0
```
3) Отредактируйте `config.json` по необходимости (включение/выключение фич).

## Запуск
`python main.py`

Логи: `bot.log`, `error.log`.

## Тесты (локальные проверки)
- Модульные импорты/валидаторы/клавиатуры: `python test_modules.py`

## Архитектура
- Модульные обработчики в `src/handlers/`
- Конфигурация/переводы в `src/config/`
- Работа с БД в `src/database/`
