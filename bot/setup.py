from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from services.instagram_api import InstagramAPI
from config import Config
from middlewares.throttling import ThrottlingMiddleware
from bot.handlers import router


def setup_bot(config: Config):
    bot = Bot(token=config.bot.token)
    dp = Dispatcher(storage=MemoryStorage())
    instagram_api = InstagramAPI(
        api_key=config.instagram.rapidapi_key,
        api_host=config.instagram.rapidapi_host,
    )

    dp.message.middleware(ThrottlingMiddleware(rate_limit=1))
    dp.include_router(router)
    dp.workflow_data.update(instagram_api=instagram_api, config=config)
    return bot, dp