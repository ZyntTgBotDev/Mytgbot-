from aiogram import Bot
from db import execute

async def check_required_channels(bot: Bot, user_id: int):
    rows = await execute("SELECT id,chat_id,title,username,invite_url FROM channels ORDER BY id", fetch=True)
    missing = []
    for row in rows:
        cid = row[1]
        try:
            member = await bot.get_chat_member(cid, user_id)
            if member.status in ("left", "kicked"):
                missing.append(row)
        except Exception:
            # If the bot cannot inspect the channel, treat it as missing rather than granting access.
            missing.append(row)
    return rows, missing
