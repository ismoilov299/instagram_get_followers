import logging
import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from services.instagram_api import InstagramAPI
from bot.handlers import router
from middlewares.throttling import ThrottlingMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(stream=sys.stdout)
    ]
)

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)


# Функция инициализации бота
async def main():
    # Загружаем конфигурацию
    config = load_config()

    # Инициализируем экземпляр InstagramAPI
    instagram_api = InstagramAPI(
        api_key=config.instagram.api_key,
        api_host=config.instagram.api_host
    )

    # Создаем хранилище состояний
    storage = MemoryStorage()

    # Инициализируем бота и диспетчер
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=storage)

    # Регистрируем middleware
    dp.message.middleware(ThrottlingMiddleware())

    # Регистрируем обработчики
    dp.include_router(router)

    # Регистрируем зависимость для InstagramAPI
    dp.workflow_data.update({"instagram_api": instagram_api})

    # Запускаем поллинг
    try:
        logger.info("Starting bot")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        if hasattr(instagram_api, 'close') and callable(instagram_api.close):
            await instagram_api.close()  # Закрываем сессию API если метод существует
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())