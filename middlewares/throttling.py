import time
from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 1):
        self.rate_limit = rate_limit
        self.users: Dict[int, float] = {}

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        current_time = time.time()

        if user_id in self.users and current_time - self.users[user_id] < self.rate_limit:
            await event.answer("Iltmos sabr bilan botni ishlating siz juda ko'p so'rov yubordingiz")
            return

        self.users[user_id] = current_time

        return await handler(event, data)