# Source package

# Compatibility shim for tests expecting MemoryStorage.key_builder
try:
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.fsm.storage.base import StorageKey

    if not hasattr(MemoryStorage, "key_builder"):
        def _key_builder(self, *, bot_id: int, chat_id: int, user_id: int) -> StorageKey:
            return StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)

        setattr(MemoryStorage, "key_builder", _key_builder)
except Exception:
    # If aiogram is not available or API changed, ignore.
    pass
