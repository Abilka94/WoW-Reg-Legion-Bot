# WoW Reg Bot — VK-версия

> **Версия: 0.0.1 (1) (alpha)**

Бот для регистрации аккаунтов WoW через сообщество ВКонтакте.
Использует Bots Long Poll API. Разворачивается в LXC-контейнере Proxmox.

## Требования

- Python 3.11+
- MySQL (таблицы `account`, `battlenet_accounts`, `users`)
- Redis (хранилище FSM)

## Быстрый старт

### 1. Подготовка сообщества VK

1. Создайте сообщество ВКонтакте (группу/паблик).
2. Настройки → Работа с API → Создать ключ доступа.
   - Права: **сообщения сообщества**, **управление сообществом**.
3. Настройки → Сообщения → включите «Сообщения сообщества».
4. Настройки → Работа с API → Long Poll API → включите, версия API `5.199`.
   - Типы событий: `message_new`, `message_event`.
5. Запишите **токен** и **ID сообщества** (число из адресной строки или раздел «Информация»).

### 2. Миграция БД

Если таблица `users` содержит колонку `telegram_id`, выполните миграцию:

```sql
ALTER TABLE users CHANGE COLUMN telegram_id vk_id BIGINT NOT NULL;
ALTER TABLE users ADD INDEX idx_vk_id (vk_id);
```

Для нового деплоя используйте скрипт `migrate_users_vk.sql`.

### 3. Конфигурация

Скопируйте `.env.example` в `.env` и заполните:

```
VK_TOKEN=ваш_токен_сообщества
VK_GROUP_ID=id_сообщества
VK_ADMIN_ID=ваш_vk_user_id
DB_HOST=127.0.0.1
DB_PORT=3310
DB_USER=spp_user
DB_PASSWORD=пароль
DB_NAME=legion_auth
REDIS_DSN=redis://127.0.0.1:6379/0
```

### 4. Установка зависимостей и запуск

```bash
pip install -r requirements.txt
python main.py
```

### 5. Автозапуск (systemd)

```ini
[Unit]
Description=WoW VK Reg Bot
After=network.target mysql.service redis.service

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/vk-bot
ExecStart=/opt/vk-bot/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Структура проекта

```
main.py                    — точка входа
config.json                — конфигурация фич и лимитов
connection_info.txt        — текст для «Инфо по подключению»
news.txt                   — текст для «Новости»
src/
├── config/
│   ├── settings.py        — переменные окружения, CONFIG
│   └── translations.py    — тексты (plain text, без HTML)
├── database/
│   ├── connection.py      — пул MySQL
│   └── user_operations.py — SQL-операции (vk_id)
├── handlers/
│   ├── commands.py        — /start, /version, /admin, меню, callback
│   ├── registration.py    — мастер регистрации 1/3→2/3→3/3
│   ├── account_management.py — просмотр, сброс/смена пароля, удаление
│   ├── admin.py           — проверка БД, рассылка, удаление аккаунта
│   └── messages.py        — fallback: не-текст, подсказка
├── keyboards/
│   ├── user_keyboards.py  — VK inline-клавиатуры
│   └── admin_keyboards.py — клавиатуры админки
├── states/
│   ├── fsm.py             — FSM на Redis
│   └── user_states.py     — константы состояний
└── utils/
    ├── vk_api.py          — VK API клиент (aiohttp)
    ├── longpoll.py        — Bots Long Poll цикл
    ├── middleware.py       — rate limit + защита от дублей
    ├── notifications.py   — трекинг сообщений бота
    ├── validators.py      — валидация email, пароля, ника
    ├── email_providers.py — база почтовых провайдеров
    └── file_cache.py      — кэш файлов
```
