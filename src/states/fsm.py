"""
FSM (конечный автомат) на Redis для VK-бота.
Хранит состояние и данные по ключу vk_user_id.
"""
import json
import logging
import redis.asyncio as aioredis

logger = logging.getLogger("bot")

STATE_TTL = 3600


class FSMContext:
    """Контекст состояния для конкретного пользователя."""

    def __init__(self, redis: aioredis.Redis, user_id: int):
        self._r = redis
        self._uid = user_id
        self._state_key = f"vk_fsm:state:{user_id}"
        self._data_key = f"vk_fsm:data:{user_id}"

    async def get_state(self) -> str | None:
        val = await self._r.get(self._state_key)
        return val.decode() if val else None

    async def set_state(self, state: str | None):
        if state is None:
            await self._r.delete(self._state_key)
        else:
            await self._r.set(self._state_key, state, ex=STATE_TTL)

    async def get_data(self) -> dict:
        val = await self._r.get(self._data_key)
        if val:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return {}
        return {}

    async def update_data(self, **kwargs):
        data = await self.get_data()
        data.update(kwargs)
        await self._r.set(self._data_key, json.dumps(data), ex=STATE_TTL)

    async def clear(self):
        await self._r.delete(self._state_key, self._data_key)


class FSMStorage:
    """Фабрика FSMContext, хранит ссылку на Redis."""

    def __init__(self, redis_dsn: str):
        self.redis: aioredis.Redis | None = None
        self._dsn = redis_dsn

    async def connect(self):
        self.redis = aioredis.from_url(self._dsn)
        logger.info("Redis подключен для FSM хранилища")

    async def close(self):
        if self.redis:
            await self.redis.close()

    def get_context(self, user_id: int) -> FSMContext:
        assert self.redis is not None, "FSMStorage не подключен"
        return FSMContext(self.redis, user_id)
