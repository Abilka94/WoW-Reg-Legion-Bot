"""
VK API клиент — отправка сообщений, редактирование, удаление, клавиатуры.
Работает поверх aiohttp для совместимости с asyncio-стеком проекта.
"""
import json
import random
import logging
import aiohttp

logger = logging.getLogger("bot")

API_VERSION = "5.199"
API_BASE = "https://api.vk.com/method"


class VkApi:
    def __init__(self, token: str, session: aiohttp.ClientSession | None = None):
        self.token = token
        self._own_session = session is None
        self.session = session or aiohttp.ClientSession()

    async def close(self):
        if self._own_session and self.session and not self.session.closed:
            await self.session.close()

    async def call(self, method: str, **params) -> dict:
        params["access_token"] = self.token
        params["v"] = API_VERSION
        url = f"{API_BASE}/{method}"
        async with self.session.post(url, data=params) as resp:
            data = await resp.json()
        if "error" in data:
            logger.error(f"VK API {method} error: {data['error']}")
        return data

    # ── Сообщения ──────────────────────────────────────────────

    async def send_message(
        self,
        peer_id: int,
        text: str,
        keyboard: dict | None = None,
    ) -> int | None:
        """Отправляет сообщение. Возвращает message_id или None."""
        params: dict = {
            "peer_id": peer_id,
            "message": text,
            "random_id": random.randint(1, 2**31),
        }
        if keyboard is not None:
            params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
        data = await self.call("messages.send", **params)
        return data.get("response")

    async def edit_message(
        self,
        peer_id: int,
        message_id: int,
        text: str,
        keyboard: dict | None = None,
    ) -> bool:
        """Редактирует сообщение. Возвращает True при успехе."""
        params: dict = {
            "peer_id": peer_id,
            "message_id": message_id,
            "message": text,
        }
        if keyboard is not None:
            params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
        data = await self.call("messages.edit", **params)
        return data.get("response") == 1

    async def delete_message(
        self, peer_id: int, message_ids: list[int] | int, delete_for_all: bool = True
    ) -> bool:
        if isinstance(message_ids, int):
            message_ids = [message_ids]
        params: dict = {
            "peer_id": peer_id,
            "message_ids": ",".join(str(m) for m in message_ids),
            "delete_for_all": int(delete_for_all),
        }
        data = await self.call("messages.delete", **params)
        return "response" in data

    async def send_event_answer(
        self, event_id: str, user_id: int, peer_id: int, event_data: dict | None = None
    ):
        """Ответ на message_event (callback-кнопка VK)."""
        params: dict = {
            "event_id": event_id,
            "user_id": user_id,
            "peer_id": peer_id,
        }
        if event_data:
            params["event_data"] = json.dumps(event_data, ensure_ascii=False)
        await self.call("messages.sendMessageEventAnswer", **params)
