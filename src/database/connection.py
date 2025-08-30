"""
Подключение к базе данных
"""
import aiomysql
from ..config.settings import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

async def get_pool():
    """Создает пул соединений с MySQL"""
    return await aiomysql.create_pool(
        host=DB_HOST, 
        port=DB_PORT, 
        user=DB_USER,
        password=DB_PASS, 
        db=DB_NAME, 
        charset="utf8", 
        autocommit=True
    )