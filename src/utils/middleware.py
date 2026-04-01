"""
Rate-limit и защита от дублирующих событий для VK.
"""
import time
import logging

logger = logging.getLogger("bot")


class RateLimit:
    def __init__(self, seconds: float = 1.0):
        self.seconds = seconds
        self.last: dict[int, float] = {}
        self.processing: set[str] = set()

    def check(self, user_id: int, event_id: str | None = None) -> bool:
        """Возвращает True если запрос разрешён."""
        now = time.time()
        if now - self.last.get(user_id, 0) < self.seconds:
            return False
        if event_id:
            key = f"{user_id}_{event_id}"
            if key in self.processing:
                return False
            self.processing.add(key)
        self.last[user_id] = now
        return True

    def release(self, user_id: int, event_id: str | None = None):
        if event_id:
            self.processing.discard(f"{user_id}_{event_id}")

    def cleanup(self):
        """Удаляет записи старше 5 минут."""
        now = time.time()
        stale = [uid for uid, t in self.last.items() if now - t > 300]
        for uid in stale[:100]:
            self.last.pop(uid, None)
