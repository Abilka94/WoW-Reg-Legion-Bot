"""
Middleware для ограничения частоты запросов и защиты от повторных нажатий
"""
import time
import asyncio
from aiogram.types import CallbackQuery

class RateLimit:
    """Middleware для ограничения частоты запросов и защиты от повторных нажатий"""
    def __init__(self, seconds=1.0):
        self.seconds = seconds
        self.last = {}
        self.processing = set()  # Множество обрабатываемых callback'ов

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None) or getattr(event.message, "from_user", None)
        if user:
            uid, now = user.id, time.time()
            
            # Для callback query проверяем, не обрабатывается ли уже
            if isinstance(event, CallbackQuery):
                callback_id = f"{uid}_{event.data}_{event.message.message_id if event.message else 0}"
                if callback_id in self.processing:
                    await event.answer("⏳ Обработка предыдущего запроса...", show_alert=False)
                    return
                
                # Проверка частоты запросов
                if now - self.last.get(uid, 0) < self.seconds:
                    await event.answer("⏱ Слишком много запросов. Подождите немного.", show_alert=False)
                    return
                
                # Добавляем в обработку
                self.processing.add(callback_id)
                self.last[uid] = now
                
                try:
                    result = await handler(event, data)
                    return result
                finally:
                    # Удаляем из обработки после завершения
                    await asyncio.sleep(0.1)  # Небольшая задержка для предотвращения повторных нажатий
                    self.processing.discard(callback_id)
            else:
                # Для обычных сообщений только проверка частоты
                if now - self.last.get(uid, 0) < self.seconds:
                    return
                self.last[uid] = now
        
        return await handler(event, data)