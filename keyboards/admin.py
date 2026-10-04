from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def menu(owner=False):
    rows = [
        [InlineKeyboardButton(text="🎬 Фильмы",callback_data="a:movies"),
         InlineKeyboardButton(text="📢 Каналы",callback_data="a:channels")],
        [InlineKeyboardButton(text="🖼 Картинки",callback_data="a:images"),
         InlineKeyboardButton(text="💎 Тарифы",callback_data="a:plans")],
        [InlineKeyboardButton(text="🎟 Промокоды",callback_data="a:promos"),
         InlineKeyboardButton(text="📢 Рассылка",callback_data="a:broadcast")],
        [InlineKeyboardButton(text="📊 Статистика",callback_data="a:stats"),
         InlineKeyboardButton(text="👥 Пользователи",callback_data="a:users")]
    ]
    if owner:
        rows.append([InlineKeyboardButton(text="👑 Администраторы",callback_data="a:admins")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Админка",callback_data="a:home")]
    ])
