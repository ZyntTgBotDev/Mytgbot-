from aiogram import Bot
from db import execute

async def check_required_channels(bot: Bot, user_id: int):
    rows = await execute('SELECT id,chat_id,title,username,invite_url FROM channels ORDER BY id',fetch=True)
    missing = []
    for row in rows:
        try:
            member = await bot.get_chat_member(row[1], user_id)
            if member.status in ('left','kicked'):
                missing.append(row)
        except Exception:
            missing.append(row)
    return rows, missing
