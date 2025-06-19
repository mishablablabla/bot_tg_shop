import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from db.session import init_db
from config import settings
from bot.handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    logging.info("Init DB...")
    init_db()

    logging.info("Starting bot...")
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Exception in bot: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.info("Starting main event loop")
    asyncio.run(main())
