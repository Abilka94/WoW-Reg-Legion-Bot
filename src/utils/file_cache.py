"""
Кэширование файлов (идентично оригиналу)
"""
import os


class FileCache:
    def __init__(self, path):
        self.path = path
        self.ts = 0
        self.content = ""

    async def get(self):
        try:
            m = os.path.getmtime(self.path)
            if m != self.ts:
                with open(self.path, encoding="utf-8") as f:
                    self.content = f.read()
                self.ts = m
        except FileNotFoundError:
            self.content = ""
        return self.content
