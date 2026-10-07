from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔎 Найти фильм',callback_data='u:search')],
        [InlineKeyboardButton(text='💎 Подписка',callback_data='u:plans'),InlineKeyboardButton(text='👤 Профиль',callback_data='u:profile')]
    ])

def back(target='u:home'):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='◀️ Назад',callback_data=target)]])

def subscription_check(channels):
    rows=[]
    for ch in channels:
        title=ch[2] or ch[3] or 'Канал'
        url=ch[4] or (f'https://t.me/{ch[3].lstrip("@")}' if ch[3] else None)
        if url:
            rows.append([InlineKeyboardButton(text=f'📢 {title}',url=url)])
    rows.append([InlineKeyboardButton(text='✅ Проверить подписку',callback_data='u:checksub')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def plans(rows):
    buttons=[[InlineKeyboardButton(text=f'⭐ {d} дней — {s} Stars',callback_data=f'u:buy:{d}:0') ] for d,s in rows]
    buttons.append([InlineKeyboardButton(text='🎟 Применить промокод',callback_data='u:promo')])
    buttons.append([InlineKeyboardButton(text='◀️ Назад',callback_data='u:home')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def movie(access,number):
    first=InlineKeyboardButton(text='▶️ Смотреть' if access else '🔒 Приобрести подписку',callback_data=f'u:watch:{number}' if access else 'u:plans')
    return InlineKeyboardMarkup(inline_keyboard=[[first],[InlineKeyboardButton(text='◀️ Назад',callback_data='u:home')]])

def profile():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎟 Ввести промокод',callback_data='u:promo')],
        [InlineKeyboardButton(text='👥 Реферальная система',callback_data='u:ref')],
        [InlineKeyboardButton(text='💎 Купить/продлить',callback_data='u:plans')],
        [InlineKeyboardButton(text='◀️ Назад',callback_data='u:home')]
    ])

def promo_payment(days, price):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'⭐ Оплатить {price} Stars',callback_data='u:promo_pay')],[InlineKeyboardButton(text='❌ Отмена',callback_data='u:plans')]])
