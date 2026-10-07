from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def menu(owner=False):
    rows=[
        [InlineKeyboardButton(text='🎬 Фильмы',callback_data='a:movies'),InlineKeyboardButton(text='📢 Каналы',callback_data='a:channels')],
        [InlineKeyboardButton(text='🖼 Медиа',callback_data='a:images'),InlineKeyboardButton(text='💎 Тарифы',callback_data='a:plans')],
        [InlineKeyboardButton(text='🎟 Промокоды',callback_data='a:promos'),InlineKeyboardButton(text='📢 Рассылка',callback_data='a:broadcast')],
        [InlineKeyboardButton(text='👤 Пользователи',callback_data='a:users'),InlineKeyboardButton(text='📊 Статистика',callback_data='a:stats')]
    ]
    if owner:
        rows.append([InlineKeyboardButton(text='👑 Администраторы',callback_data='a:admins')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='◀️ Админка',callback_data='a:home')]])

def discounts():
    vals=(0,5,10,25,50,70,100)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'{v}%',callback_data=f'a:pd:{v}') for v in vals[:3]],
        [InlineKeyboardButton(text=f'{v}%',callback_data=f'a:pd:{v}') for v in vals[3:]],
        [InlineKeyboardButton(text='❌ Отмена',callback_data='a:promos')]
    ])
