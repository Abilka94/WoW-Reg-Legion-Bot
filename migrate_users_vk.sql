-- Миграция таблицы users: telegram_id -> vk_id
-- Запустите этот скрипт на новой БД (или адаптируйте для миграции существующей)

-- Вариант 1: Новая таблица (для нового деплоя)
CREATE TABLE IF NOT EXISTS users (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    vk_id     BIGINT NOT NULL,
    email     VARCHAR(255) NOT NULL,
    UNIQUE KEY uk_vk_email (vk_id, email),
    INDEX idx_vk_id (vk_id),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Вариант 2: Миграция существующей таблицы (раскомментируйте при необходимости)
-- ALTER TABLE users CHANGE COLUMN telegram_id vk_id BIGINT NOT NULL;
-- ALTER TABLE users ADD INDEX idx_vk_id (vk_id);
