import asyncio
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware
from config import BOT_TOKEN
from db import init_db, is_blocked, is_admin
from handlers.user import router as user_router
from handlers.admin import router as admin_router

class BlockedMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get('event_from_user') or getattr(event, 'from_user', None)
        if user and await is_blocked(user.id) and not await is_admin(user.id):
            if hasattr(event, 'answer'):
                try:
                    if event.__class__.__name__ == 'CallbackQuery':
                        await event.answer('🚫 Ваш аккаунт заблокирован.', show_alert=True)
                    else:
                        await event.answer('🚫 Ваш аккаунт заблокирован.')
                except Exception: pass
            return
        return await handler(event, data)

async def main():
    if not BOT_TOKEN or BOT_TOKEN == 'PASTE_NEW_TOKEN_HERE':
        raise RuntimeError('Укажи BOT_TOKEN в .env')
    logging.basicConfig(level=logging.INFO)
    await init_db()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(BlockedMiddleware())
    dp.callback_query.middleware(BlockedMiddleware())
    dp.include_router(admin_router)
    dp.include_router(user_router)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == '__main__':
    asyncio.run(main())
