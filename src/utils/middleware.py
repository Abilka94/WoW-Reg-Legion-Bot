"""
Middleware для ограничения частоты запросов и защиты от повторных нажатий
"""
import time
import asyncio
from aiogram.types import CallbackQuery

class RateLimit:
    """Middleware для ограничения частоты запросов и блокировки параллельных запросов"""
    def __init__(self, seconds=1.0):
        self.seconds = seconds
        self.last = {}
        # Блокировки для каждого пользователя (предотвращает параллельные запросы)
        self.locks = {}
        # Обрабатываемые callback'и (предотвращает повторную обработку)
        self.processing_callbacks = set()

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None) or getattr(event.message, "from_user", None)
        
        if not user:
            return await handler(event, data)
        
        uid = user.id
        now = time.time()
        
        # Проверка rate limit
        if now - self.last.get(uid, 0) < self.seconds:
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("⏱ Слишком много запросов. Подождите немного.", show_alert=False)
                except Exception:
                    pass
            return
        
        # Для callback запросов - проверка на дубликаты
        if isinstance(event, CallbackQuery):
            callback_id = f"{uid}_{event.id}"
            if callback_id in self.processing_callbacks:
                try:
                    await event.answer("⏱ Запрос уже обрабатывается...", show_alert=False)
                except Exception:
                    pass
                return
            
            # Добавляем в обрабатываемые
            self.processing_callbacks.add(callback_id)
            
            # НЕ отвечаем на callback здесь - пусть обработчики отвечают сами
            # Это позволяет обработчикам отправлять alert'ы и другие ответы
        
        # Получаем или создаем блокировку для пользователя
        if uid not in self.locks:
            self.locks[uid] = asyncio.Lock()
        
        lock = self.locks[uid]
        
        # Проверяем, не заблокирован ли уже запрос
        if lock.locked():
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("⏱ Обрабатывается предыдущий запрос...", show_alert=False)
                except Exception:
                    pass
            return
        
        try:
            # Блокируем выполнение для этого пользователя
            async with lock:
                self.last[uid] = now
                return await handler(event, data)
        finally:
            # Удаляем callback из обрабатываемых после завершения
            if isinstance(event, CallbackQuery):
                callback_id = f"{uid}_{event.id}"
                self.processing_callbacks.discard(callback_id)
                
                # Очистка старых блокировок (если пользователь неактивен более 5 минут)
                if len(self.locks) > 1000:
                    # Простая очистка: удаляем блокировки для неактивных пользователей
                    inactive_users = [
                        u for u, last_time in self.last.items()
                        if now - last_time > 300  # 5 минут
                    ]
                    for inactive_uid in inactive_users[:100]:  # Удаляем максимум 100 за раз
                        self.locks.pop(inactive_uid, None)
                        self.last.pop(inactive_uid, None)