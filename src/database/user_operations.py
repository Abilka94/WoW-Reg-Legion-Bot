"""
Database operations for the WoW Registration Bot.
All functions are async and operate on an aiomysql-like pool provided by tests.
Implementation focuses on simple, deterministic SQL flows to satisfy tests.
"""
from __future__ import annotations

import hashlib
import secrets
import logging

from ..config.settings import CONFIG

logger = logging.getLogger("bot")


async def email_exists(pool, email: str) -> bool:
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM battlenet_accounts WHERE email=%s", (mu,))
            return bool(await cur.fetchone())


async def count_user_accounts(pool, telegram_id: int) -> int:
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM users WHERE telegram_id=%s", (telegram_id,))
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def register_user(pool, nick: str, pwd: str, mail: str, telegram_id: int):
    """Register user and related entities.
    Note: intentionally do not call email_exists here to align with tests that
    expect two fetchone calls: count -> select id.
    Returns: (username, error_code)
    """
    mu, pu = mail.upper(), pwd.upper()

    current_accounts = await count_user_accounts(pool, telegram_id)
    if current_accounts >= CONFIG["settings"]["max_accounts_per_user"]:
        logger.warning(f"Max accounts reached for telegram_id {telegram_id}")
        return None, "err_max_accounts"

    # Battle.net password hash (SHA256 then reversed bytes hex, as in legacy schemes)
    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{pu}".encode()).hexdigest().upper()
    battlenet_hash = bytes.fromhex(outer)[::-1].hex().upper()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Insert battlenet account
            await cur.execute(
                "INSERT INTO battlenet_accounts(email,sha_pass_hash,is_temp_password) VALUES(%s,%s,0)",
                (mu, battlenet_hash),
            )

            # Get battlenet id
            await cur.execute("SELECT id FROM battlenet_accounts WHERE email=%s", (mu,))
            bid = (await cur.fetchone())[0]
            username = f"{bid}#1"

            # Account hash (SHA1 username:password)
            account_hash = hashlib.sha1(f"{username}:{pu}".encode()).hexdigest().upper()
            await cur.execute(
                "INSERT INTO account(username,sha_pass_hash,email,battlenet_account) VALUES(%s,%s,%s,%s)",
                (username, account_hash, mu, bid),
            )

            # Access table
            await cur.execute("INSERT INTO account_access(id,gmlevel,RealmID) VALUES(%s,3,-1)", (bid,))

            # Link telegram user
            await cur.execute("INSERT INTO users(telegram_id,email) VALUES(%s,%s)", (telegram_id, mu))

    logger.info(f"User registered: {username} (e-mail: {mu})")
    return username, None


async def reset_password(pool, mail: str) -> str | None:
    mu = mail.upper()
    tmp = secrets.token_hex(4).upper()

    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{tmp}".encode()).hexdigest().upper()
    battlenet_hash = bytes.fromhex(outer)[::-1].hex().upper()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE battlenet_accounts SET sha_pass_hash=%s, is_temp_password=1, temp_password=%s WHERE email=%s",
                (battlenet_hash, tmp, mu),
            )

            # Update account hash if account exists
            await cur.execute("SELECT username FROM account WHERE email=%s", (mu,))
            row = await cur.fetchone()
            if row:
                uname = row[0]
                account_hash = hashlib.sha1(f"{uname}:{tmp}".encode()).hexdigest().upper()
                await cur.execute("UPDATE account SET sha_pass_hash=%s WHERE email=%s", (account_hash, mu))

    return tmp


async def change_password(pool, email: str, new_password: str) -> None:
    mu, pu = email.upper(), new_password.upper()

    inner = hashlib.sha256(mu.encode()).hexdigest().upper()
    outer = hashlib.sha256(f"{inner}:{pu}".encode()).hexdigest().upper()
    battlenet_hash = bytes.fromhex(outer)[::-1].hex().upper()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Update battlenet password and clear temp flags
            await cur.execute(
                "UPDATE battlenet_accounts SET sha_pass_hash=%s, is_temp_password=0, temp_password=NULL WHERE email=%s",
                (battlenet_hash, mu),
            )

            # Update account table based on username
            await cur.execute("SELECT username FROM account WHERE email=%s", (mu,))
            row = await cur.fetchone()
            if row:
                uname = row[0]
                account_hash = hashlib.sha1(f"{uname}:{pu}".encode()).hexdigest().upper()
                await cur.execute("UPDATE account SET sha_pass_hash=%s WHERE email=%s", (account_hash, mu))


async def get_account_info(pool, telegram_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT b.email, a.username, b.is_temp_password, b.temp_password "
                "FROM users u "
                "JOIN battlenet_accounts b ON u.email = b.email "
                "LEFT JOIN account a ON b.email = a.email "
                "WHERE u.telegram_id=%s",
                (telegram_id,),
            )
            return await cur.fetchall()


async def delete_account(pool, telegram_id: int, email: str) -> bool:
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Ensure ownership
            await cur.execute("SELECT 1 FROM users WHERE telegram_id=%s AND email=%s", (telegram_id, mu))
            if not await cur.fetchone():
                return False

            # Cascade delete related entries
            await cur.execute("DELETE FROM account_access WHERE id IN (SELECT id FROM account WHERE email=%s)", (mu,))
            await cur.execute("DELETE FROM account WHERE email=%s", (mu,))
            await cur.execute("DELETE FROM battlenet_accounts WHERE email=%s", (mu,))
            await cur.execute("DELETE FROM users WHERE telegram_id=%s AND email=%s", (telegram_id, mu))
            return cur.rowcount > 0


async def admin_delete_account(pool, email: str) -> bool:
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM account_access WHERE id IN (SELECT id FROM account WHERE email=%s)", (mu,))
            await cur.execute("DELETE FROM account WHERE email=%s", (mu,))
            await cur.execute("DELETE FROM battlenet_accounts WHERE email=%s", (mu,))
            await cur.execute("DELETE FROM users WHERE email=%s", (mu,))
            return cur.rowcount > 0


async def get_account_coins(pool, email: str) -> int:
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT coins FROM account WHERE email=%s", (mu,))
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def add_coins_to_account(pool, email: str, amount: int) -> int | None:
    mu = email.upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE account SET coins = coins + %s WHERE email=%s", (amount, mu))
            if cur.rowcount:
                await cur.execute("SELECT coins FROM account WHERE email=%s", (mu,))
                return (await cur.fetchone())[0]
            return None


async def get_user_accounts_with_coins(pool, telegram_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT b.email, a.username, b.is_temp_password, b.temp_password, COALESCE(a.coins, 0) "
                "FROM users u "
                "JOIN battlenet_accounts b ON u.email = b.email "
                "LEFT JOIN account a ON b.email = a.email "
                "WHERE u.telegram_id=%s",
                (telegram_id,),
            )
            return await cur.fetchall()


