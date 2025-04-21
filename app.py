import asyncio
import logging

from aiogram.enums import ParseMode

from config import load_config
from bot.setup import setup_bot


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    config = load_config()
    bot, dp = setup_bot(config)
    bot.parse_mode = ParseMode.MARKDOWN
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        logging.info("Bot ishga tushirilmoqda...")
        await dp.start_polling(bot)
    finally:
        logging.info("Bot to'xtatildi.")
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")