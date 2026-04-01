"""
Операции с пользователями (идентификация по vk_id)
"""
import hashlib
import secrets
import logging
from ..config.settings import CONFIG

logger = logging.getLogger("bot")


async def email_exists(pool, email):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM battlenet_accounts WHERE email=%s", (email.upper(),)
            )
            return bool(await cur.fetchone())


async def username_exists(pool, username):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM account WHERE username=%s", (username,))
            return bool(await cur.fetchone())


async def count_user_accounts(pool, vk_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM users WHERE vk_id=%s", (vk_id,)
            )
            return (await cur.fetchone())[0]


async def register_user(pool, nick: str, pwd: str, mail: str, vk_id: int):
    mu, pu = mail.upper(), pwd.upper()
    current_accounts = await count_user_accounts(pool, vk_id)

    if current_accounts >= CONFIG["settings"]["max_accounts_per_user"]:
        logger.warning(f"Попытка регистрации сверх лимита для vk_id {vk_id}")
        return None, "err_max_accounts"

    if await email_exists(pool, mu):
        logger.warning(f"Попытка регистрации с существующим e-mail: {mu}")
        return None, "err_exists"

    if await username_exists(pool, nick):
        logger.warning(f"Попытка регистрации с существующим username: {nick}")
        return None, "err_username_exists"

    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{pu}".encode()).hexdigest().upper()
    bhash = bytes.fromhex(outer)[::-1].hex().upper()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO battlenet_accounts(email,sha_pass_hash,is_temp_password) VALUES(%s,%s,0)",
                (mu, bhash),
            )
            await cur.execute(
                "SELECT id FROM battlenet_accounts WHERE email=%s", (mu,)
            )
            bid = (await cur.fetchone())[0]
            username = nick

            ah = hashlib.sha1(f"{username}:{pu}".encode()).hexdigest().upper()
            await cur.execute(
                "INSERT INTO account(username,sha_pass_hash,email,battlenet_account) VALUES(%s,%s,%s,%s)",
                (username, ah, mu, bid),
            )
            await cur.execute(
                "INSERT INTO account_access(id,gmlevel,RealmID) VALUES(%s,3,-1)",
                (bid,),
            )
            await cur.execute(
                "INSERT INTO users(vk_id,email) VALUES(%s,%s)", (vk_id, mu)
            )

    logger.info(f"Регистрация: {username} (e-mail: {mu}, vk_id: {vk_id})")
    return username, None


async def reset_password(pool, mail: str):
    mu = mail.upper()
    tmp = secrets.token_hex(4).upper()

    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{tmp}".encode()).hexdigest().upper()
    bhash = bytes.fromhex(outer)[::-1].hex().upper()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE battlenet_accounts SET sha_pass_hash=%s, is_temp_password=1, temp_password=%s WHERE email=%s",
                (bhash, tmp, mu),
            )
            affected = cur.rowcount

            await cur.execute(
                "SELECT username FROM account WHERE email=%s", (mu,)
            )
            row = await cur.fetchone()
            if row:
                uname = row[0]
                ah = hashlib.sha1(f"{uname}:{tmp}".encode()).hexdigest().upper()
                await cur.execute(
                    "UPDATE account SET sha_pass_hash=%s WHERE email=%s", (ah, mu)
                )
                logger.info(f"Пароль сброшен для e-mail: {mu}")
            else:
                logger.warning(f"e-mail {mu} не найден в таблице account")

    if not affected:
        logger.warning(f"e-mail {mu} не найден в battlenet_accounts")
        return None
    return tmp


async def change_password(pool, mail: str, new_password: str):
    mu, pu = mail.upper(), new_password.upper()

    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{pu}".encode()).hexdigest().upper()
    bhash = bytes.fromhex(outer)[::-1].hex().upper()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE battlenet_accounts SET sha_pass_hash=%s, is_temp_password=0, temp_password=NULL WHERE email=%s",
                (bhash, mu),
            )
            await cur.execute(
                "SELECT username FROM account WHERE email=%s", (mu,)
            )
            row = await cur.fetchone()
            if row:
                uname = row[0]
                ah = hashlib.sha1(f"{uname}:{pu}".encode()).hexdigest().upper()
                await cur.execute(
                    "UPDATE account SET sha_pass_hash=%s WHERE email=%s", (ah, mu)
                )
                logger.info(f"Пароль изменен для e-mail: {mu}")
            else:
                logger.warning(f"e-mail {mu} не найден в таблице account")
    return True


async def get_account_info(pool, vk_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT b.email, a.username, b.is_temp_password, b.temp_password "
                "FROM users u "
                "JOIN battlenet_accounts b ON u.email = b.email "
                "LEFT JOIN account a ON b.email = a.email "
                "WHERE u.vk_id=%s",
                (vk_id,),
            )
            return await cur.fetchall()


async def delete_account(pool, vk_id: int, email: str):
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM users WHERE vk_id=%s AND email=%s", (vk_id, mu)
            )
            if not await cur.fetchone():
                logger.warning(f"Нет доступа: vk_id={vk_id}, email={mu}")
                return False

            await cur.execute("SELECT id FROM account WHERE email=%s", (mu,))
            account_row = await cur.fetchone()
            if account_row:
                await cur.execute(
                    "DELETE FROM account_access WHERE id=%s", (account_row[0],)
                )

            await cur.execute("DELETE FROM account WHERE email=%s", (mu,))
            account_deleted = cur.rowcount > 0
            await cur.execute(
                "DELETE FROM battlenet_accounts WHERE email=%s", (mu,)
            )
            battlenet_deleted = cur.rowcount > 0
            await cur.execute(
                "DELETE FROM users WHERE vk_id=%s AND email=%s", (vk_id, mu)
            )
            users_deleted = cur.rowcount > 0

            success = account_deleted or battlenet_deleted or users_deleted
            if success:
                logger.info(f"Аккаунт удален: vk_id={vk_id}, email={mu}")
            else:
                logger.warning(f"Не удалось удалить: vk_id={vk_id}, email={mu}")
            return success


async def get_account_by_email(pool, email: str):
    """Возвращает (username, vk_id) по email."""
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT a.username, u.vk_id "
                "FROM account a "
                "JOIN users u ON a.email = u.email "
                "WHERE a.email=%s",
                (mu,),
            )
            row = await cur.fetchone()
            if row:
                return row[0], row[1]
            return None, None


async def admin_delete_account(pool, email: str):
    """Удаляет аккаунт администратором. Возвращает (success, vk_id)."""
    mu = email.upper()
    vk_id = None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT vk_id FROM users WHERE email=%s LIMIT 1", (mu,)
            )
            user_row = await cur.fetchone()
            if user_row:
                vk_id = user_row[0]

            await cur.execute("SELECT id FROM account WHERE email=%s", (mu,))
            account_row = await cur.fetchone()
            if account_row:
                await cur.execute(
                    "DELETE FROM account_access WHERE id=%s", (account_row[0],)
                )

            await cur.execute("DELETE FROM account WHERE email=%s", (mu,))
            account_deleted = cur.rowcount > 0
            await cur.execute(
                "DELETE FROM battlenet_accounts WHERE email=%s", (mu,)
            )
            battlenet_deleted = cur.rowcount > 0
            await cur.execute("DELETE FROM users WHERE email=%s", (mu,))
            users_deleted = cur.rowcount > 0

            success = account_deleted or battlenet_deleted or users_deleted
            if success:
                logger.info(f"Админ удалил аккаунт: email={mu}, vk_id={vk_id}")
            else:
                logger.warning(f"Админ не смог удалить: email={mu}")
            return success, vk_id


async def get_all_user_ids(pool):
    """Возвращает список всех vk_id для рассылки."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT DISTINCT vk_id FROM users")
            rows = await cur.fetchall()
            return [r[0] for r in rows]
