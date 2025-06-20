# import asyncio
# import logging
# from aiogram import Bot, Dispatcher
# from aiogram.fsm.storage.memory import MemoryStorage
# from db.session import init_db
# from config import settings
# from bot.handlers import router

# logging.basicConfig(level=logging.INFO)

# async def main():
#     logging.info("Init DB...")
#     init_db()

#     logging.info("Starting bot...")
#     bot = Bot(token=settings.BOT_TOKEN)
#     dp = Dispatcher(storage=MemoryStorage())
#     dp.include_router(router)

#     try:
#         await dp.start_polling(bot)
#     except Exception as e:
#         logging.error(f"Exception in bot: {e}")
#     finally:
#         await bot.session.close()

# if __name__ == "__main__":
#     logging.info("Starting main event loop")
#     asyncio.run(main())



import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from db.session import init_db
from config import settings

# Импортируем роутеры из каждого модуля
from bot.handlers.common   import router as common_router
from bot.handlers.menu     import router as menu_router
from bot.handlers.info     import router as info_router
from bot.handlers.location import router as location_router
from bot.handlers.order    import router as order_router

logging.basicConfig(level=logging.INFO)

async def main():
    logging.info("Init DB...")
    init_db()

    logging.info("Starting bot...")
    bot = Bot(token=settings.BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    # Подключаем все роутеры
    dp.include_router(common_router)
    dp.include_router(menu_router)
    dp.include_router(info_router)
    dp.include_router(location_router)
    dp.include_router(order_router)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Exception in bot: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.info("Starting main event loop")
    asyncio.run(main())
