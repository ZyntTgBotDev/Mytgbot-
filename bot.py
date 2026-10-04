import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db
from handlers.user import router as user_router
from handlers.admin import router as admin_router

async def main():
    if not BOT_TOKEN or BOT_TOKEN=="PASTE_NEW_TOKEN_HERE":
        raise RuntimeError("Укажи НОВЫЙ BOT_TOKEN в .env")
    logging.basicConfig(level=logging.INFO)
    await init_db()
    bot=Bot(BOT_TOKEN)
    dp=Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(user_router)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__":
    asyncio.run(main())
