"""
Middleware для ограничения частоты запросов
"""
import time
from aiogram.types import CallbackQuery

class RateLimit:
    """Middleware для ограничения частоты запросов"""
    def __init__(self, seconds=1.0):
        self.seconds = seconds
        self.last = {}

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None) or getattr(event.message, "from_user", None)
        if user:
            uid, now = user.id, time.time()
            if now - self.last.get(uid, 0) < self.seconds:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏱ Слишком много запросов", show_alert=False)
                return
            self.last[uid] = now
        return await handler(event, data)