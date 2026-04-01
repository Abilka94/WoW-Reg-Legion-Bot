"""
Bots Long Poll API — цикл получения событий.
"""
import logging
import asyncio
import aiohttp

logger = logging.getLogger("bot")


class BotLongPoll:
    """
    Обёртка над groups.getLongPollServer + цикл опроса.
    Возвращает список «updates» при каждом poll.
    """

    def __init__(self, api, group_id: int):
        self.api = api
        self.group_id = group_id
        self.server: str = ""
        self.key: str = ""
        self.ts: str = ""

    async def _update_server(self):
        data = await self.api.call(
            "groups.getLongPollServer", group_id=self.group_id
        )
        resp = data.get("response", {})
        self.server = resp.get("server", "")
        self.key = resp.get("key", "")
        self.ts = resp.get("ts", "")
        logger.info("Long Poll сервер обновлён")

    async def listen(self):
        """Бесконечный генератор событий."""
        await self._update_server()

        while True:
            url = f"{self.server}?act=a_check&key={self.key}&ts={self.ts}&wait=25"
            try:
                async with self.api.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    data = await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Long Poll ошибка сети: {e}, переподключение...")
                await asyncio.sleep(1)
                await self._update_server()
                continue

            if "failed" in data:
                code = data["failed"]
                if code == 1:
                    self.ts = data.get("ts", self.ts)
                elif code in (2, 3):
                    await self._update_server()
                else:
                    logger.error(f"Long Poll неизвестный failed={code}")
                    await asyncio.sleep(2)
                    await self._update_server()
                continue

            self.ts = data.get("ts", self.ts)
            for update in data.get("updates", []):
                yield update
