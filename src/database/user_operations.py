"""
Модели и операции с пользователями
"""
import hashlib
import secrets
import logging
import pymysql
from ..config.settings import CONFIG

logger = logging.getLogger("bot")

async def email_exists(pool, email):
    """Проверяет, существует ли email в базе данных"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM battlenet_accounts WHERE email=%s", (email.upper(),))
            return bool(await cur.fetchone())

async def username_exists(pool, username):
    """Проверяет, существует ли username в базе данных"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM account WHERE username=%s", (username,))
            return bool(await cur.fetchone())

async def count_user_accounts(pool, telegram_id):
    """Подсчитывает количество аккаунтов пользователя"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM users WHERE telegram_id=%s", (telegram_id,))
            return (await cur.fetchone())[0]

async def register_user(pool, nick, pwd, mail, telegram_id):
    """Регистрирует нового пользователя"""
    mu, pu = mail.upper(), pwd.upper()
    current_accounts = await count_user_accounts(pool, telegram_id)
    
    if current_accounts >= CONFIG["settings"]["max_accounts_per_user"]:
        logger.warning(f"Попытка регистрации сверх лимита для telegram_id {telegram_id}")
        return None, "err_max_accounts"
    
    if await email_exists(pool, mu):
        logger.warning(f"Попытка регистрации с существующим e-mail: {mu}")
        return None, "err_exists"
    
    # Проверка уникальности username
    if await username_exists(pool, nick):
        logger.warning(f"Попытка регистрации с существующим username: {nick}")
        return None, "err_username_exists"
    
    # Хеширование пароля
    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{pu}".encode()).hexdigest().upper()
    bhash = bytes.fromhex(outer)[::-1].hex().upper()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Создание battlenet аккаунта
            await cur.execute(
                "INSERT INTO battlenet_accounts(email,sha_pass_hash,is_temp_password) VALUES(%s,%s,0)",
                (mu, bhash)
            )
            
            # Получение ID
            await cur.execute("SELECT id FROM battlenet_accounts WHERE email=%s", (mu,))
            bid = (await cur.fetchone())[0]
            # Используем введенный пользователем никнейм вместо bid#1
            username = nick
            
            # Создание аккаунта
            ah = hashlib.sha1(f"{username}:{pu}".encode()).hexdigest().upper()
            await cur.execute(
                "INSERT INTO account(username,sha_pass_hash,email,battlenet_account) "
                "VALUES(%s,%s,%s,%s)",
                (username, ah, mu, bid)
            )
            
            # Права доступа
            await cur.execute(
                "INSERT INTO account_access(id,gmlevel,RealmID) VALUES(%s,3,-1)", (bid,)
            )
            
            # Связка с Telegram
            await cur.execute(
                "INSERT INTO users(telegram_id,email) VALUES(%s,%s)",
                (telegram_id, mu)
            )
    
    logger.info(f"Успешная регистрация пользователя: {username} (e-mail: {mu})")
    return username, None

async def reset_password(pool, mail):
    """Сбрасывает пароль пользователя"""
    mu = mail.upper()
    tmp = secrets.token_hex(4).upper()
    
    # Хеширование временного пароля
    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{tmp}".encode()).hexdigest().upper()
    bhash = bytes.fromhex(outer)[::-1].hex().upper()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE battlenet_accounts SET sha_pass_hash=%s, is_temp_password=1, temp_password=%s WHERE email=%s",
                (bhash, tmp, mu)
            )
            affected = cur.rowcount
            
            await cur.execute("SELECT username FROM account WHERE email=%s", (mu,))
            row = await cur.fetchone()
            if row:
                uname = row[0]
                ah = hashlib.sha1(f"{uname}:{tmp}".encode()).hexdigest().upper()
                await cur.execute("UPDATE account SET sha_pass_hash=%s WHERE email=%s", (ah, mu))
                logger.info(f"Пароль успешно сброшен для e-mail: {mu}")
            else:
                logger.warning(f"Не удалось сбросить пароль: e-mail {mu} не найден в таблице account")
    
    if not affected:
        logger.warning(f"Не удалось сбросить пароль: e-mail {mu} не найден в battlenet_accounts")
        return None
    return tmp

async def change_password(pool, mail, new_password):
    """Изменяет пароль пользователя"""
    mu, pu = mail.upper(), new_password.upper()
    
    # Хеширование нового пароля
    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{pu}".encode()).hexdigest().upper()
    bhash = bytes.fromhex(outer)[::-1].hex().upper()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE battlenet_accounts SET sha_pass_hash=%s, is_temp_password=0, temp_password=NULL WHERE email=%s",
                (bhash, mu)
            )
            
            await cur.execute("SELECT username FROM account WHERE email=%s", (mu,))
            row = await cur.fetchone()
            if row:
                uname = row[0]
                ah = hashlib.sha1(f"{uname}:{pu}".encode()).hexdigest().upper()
                await cur.execute("UPDATE account SET sha_pass_hash=%s WHERE email=%s", (ah, mu))
                logger.info(f"Пароль успешно изменен для e-mail: {mu}")
            else:
                logger.warning(f"Не удалось изменить пароль: e-mail {mu} не найден в таблице account")
    
    return True

async def get_account_info(pool, telegram_id):
    """Получает информацию об аккаунтах пользователя"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT b.email, a.username, b.is_temp_password, b.temp_password "
                "FROM users u "
                "JOIN battlenet_accounts b ON u.email = b.email "
                "LEFT JOIN account a ON b.email = a.email "
                "WHERE u.telegram_id=%s",
                (telegram_id,)
            )
            return await cur.fetchall()

async def delete_account(pool, telegram_id, email):
    """Удаляет аккаунт пользователя"""
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Проверяем принадлежность аккаунта пользователю
            await cur.execute("SELECT 1 FROM users WHERE telegram_id=%s AND email=%s", (telegram_id, mu))
            if not await cur.fetchone():
                logger.warning(f"Попытка удаления неподходящего аккаунта: telegram_id={telegram_id}, email={mu}")
                return False
            
            # Получаем ID аккаунта для удаления account_access
            await cur.execute("SELECT id FROM account WHERE email=%s", (mu,))
            account_row = await cur.fetchone()
            if account_row:
                account_id = account_row[0]
                await cur.execute("DELETE FROM account_access WHERE id=%s", (account_id,))
            
            # Удаление записей
            await cur.execute("DELETE FROM account WHERE email=%s", (mu,))
            await cur.execute("DELETE FROM battlenet_accounts WHERE email=%s", (mu,))
            await cur.execute("DELETE FROM users WHERE telegram_id=%s AND email=%s", (telegram_id, mu))
            
            affected = cur.rowcount
            if affected:
                logger.info(f"Аккаунт успешно удален: telegram_id={telegram_id}, email={mu}")
            else:
                logger.warning(f"Не удалось удалить аккаунт: telegram_id={telegram_id}, email={mu}")
            return affected > 0

async def get_account_by_email(pool, email):
    """Получает информацию об аккаунте по email (username, telegram_id)"""
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT a.username, u.telegram_id "
                "FROM account a "
                "JOIN users u ON a.email = u.email "
                "WHERE a.email=%s",
                (mu,)
            )
            row = await cur.fetchone()
            if row:
                return row[0], row[1]  # username, telegram_id
            return None, None

async def admin_delete_account(pool, email):
    """Удаляет аккаунт администратором. Возвращает (success, telegram_id)"""
    mu = email.upper()
    telegram_id = None
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Получаем telegram_id перед удалением
            await cur.execute("SELECT telegram_id FROM users WHERE email=%s LIMIT 1", (mu,))
            user_row = await cur.fetchone()
            if user_row:
                telegram_id = user_row[0]
            
            # Получаем ID аккаунта для удаления account_access
            await cur.execute("SELECT id FROM account WHERE email=%s", (mu,))
            account_row = await cur.fetchone()
            if account_row:
                account_id = account_row[0]
                await cur.execute("DELETE FROM account_access WHERE id=%s", (account_id,))
            
            await cur.execute("DELETE FROM account WHERE email=%s", (mu,))
            await cur.execute("DELETE FROM battlenet_accounts WHERE email=%s", (mu,))
            await cur.execute("DELETE FROM users WHERE email=%s", (mu,))
            
            affected = cur.rowcount
            if affected:
                logger.info(f"Админ удалил аккаунт: email={mu}, telegram_id={telegram_id}")
            else:
                logger.warning(f"Админ не смог удалить аккаунт: email={mu}")
            return affected > 0, telegram_id