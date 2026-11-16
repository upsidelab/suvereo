from django.core.cache import cache


class ConversationTurnLock:
    # Frees a conversation whose worker died mid-answer.
    TIMEOUT_SECONDS = 600

    def __init__(self, conversation_id: int):
        self._key = f"conversation:{conversation_id}:turn"

    def acquire(self) -> bool:
        return cache.add(self._key, True, timeout=self.TIMEOUT_SECONDS)

    def release(self) -> None:
        cache.delete(self._key)
