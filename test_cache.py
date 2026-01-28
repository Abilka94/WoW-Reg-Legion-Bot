import asyncio
from src.utils.file_cache import FileCache

async def test_file_cache():
    cache = FileCache('news.txt')
    content = await cache.get()
    print('Кэш файлов работает: ОК')
    print('Содержимое news.txt (первые 100 символов):')
    print(content[:100] + '...')

if __name__ == "__main__":
    asyncio.run(test_file_cache())