from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from db import execute

async def image_id(key):
    row = await execute("SELECT file_id FROM images WHERE key=?", (key,), one=True)
    return row[0] if row else None

async def replace_screen(bot: Bot, chat_id: int, old_message, text: str,
                        keyboard: InlineKeyboardMarkup | None = None,
                        image_key: str | None = None):
    if old_message:
        try:
            await old_message.delete()
        except Exception:
            pass
    fid = await image_id(image_key) if image_key else None
    if fid:
        return await bot.send_photo(chat_id, fid, caption=text, reply_markup=keyboard, parse_mode="HTML")
    return await bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")

async def delete_user_input(message):
    try:
        await message.delete()
    except Exception:
        pass
