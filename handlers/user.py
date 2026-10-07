from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_NAME
from db import add_user, execute, is_blocked
from services.ui import replace_screen, delete_user_input
from services.subscriptions import check_required_channels
from services.subscription import active, expiry, add_days
from services.referrals import apply_referral_reward, level_for_count, percent_for_level
from keyboards.user import main, back, subscription_check, plans, movie, profile, promo_payment

router = Router()

class Search(StatesGroup):
    number = State()

class Promo(StatesGroup):
    code = State()
    payment = State()

def discounted_stars(original: int, discount: int) -> int:
    return int((Decimal(original) * Decimal(100-discount) / Decimal(100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

async def clear_saved_screen(bot, chat_id: int, state: FSMContext):
    data = await state.get_data()
    mid = data.get('screen_message_id')
    if mid:
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

async def show_home(bot, chat_id, old=None):
    rows, missing = await check_required_channels(bot, chat_id)
    if rows and missing:
        text='🔐 <b>Доступ ограничен</b>\n\nЧтобы использовать ZYNT FILMS, подпишитесь на все обязательные каналы и нажмите «Проверить подписку».'
        return await replace_screen(bot,chat_id,old,text,subscription_check(rows),'subscription')
    return await replace_screen(bot,chat_id,old,f'🎬 <b>{BOT_NAME}</b>\n\nДобро пожаловать!\n\nВыберите действие ниже.',main(),'home')

@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    if await is_blocked(m.from_user.id):
        await m.answer('🚫 Ваш аккаунт заблокирован.')
        return
    referrer=None
    parts=(m.text or '').split(maxsplit=1)
    if len(parts)==2 and parts[1].startswith('ref_'):
        try: referrer=int(parts[1][4:])
        except ValueError: referrer=None
    await add_user(m.from_user,referrer)
    await show_home(m.bot,m.chat.id)

@router.callback_query(F.data=='u:checksub')
async def checksub(c:CallbackQuery):
    rows,missing=await check_required_channels(c.bot,c.from_user.id)
    if missing:
        await c.answer('❌ Вы подписаны не на все обязательные каналы.',show_alert=True); return
    await c.answer('✅ Подписка подтверждена!'); await show_home(c.bot,c.from_user.id,c.message)

@router.callback_query(F.data=='u:home')
async def home(c:CallbackQuery,state:FSMContext):
    await state.clear(); await c.answer(); await show_home(c.bot,c.from_user.id,c.message)

@router.callback_query(F.data=='u:search')
async def search(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.set_state(Search.number)
    msg=await replace_screen(c.bot,c.from_user.id,c.message,'🔎 <b>Поиск фильма</b>\n\nВведите номер фильма.',back(),'search')
    await state.update_data(screen_message_id=msg.message_id)

@router.message(Search.number)
async def search_number(m:Message,state:FSMContext):
    number=(m.text or '').strip(); await delete_user_input(m); await clear_saved_screen(m.bot,m.chat.id,state)
    movie_row=await execute('SELECT number,title,description,year,genre,poster_file_id FROM movies WHERE number=?',(number,),one=True)
    await execute('UPDATE users SET searches=searches+1 WHERE id=?',(m.from_user.id,))
    await state.clear()
    if not movie_row:
        await m.answer('❌ Фильм с таким номером не найден.',reply_markup=main()); return
    _,title,desc,year,genre,poster=movie_row
    text=f'🎬 <b>{title}</b>\n\n'
    if year:text+=f'📅 {year}\n'
    if genre:text+=f'🎭 {genre}\n'
    if desc:text+=f'\n📖 <b>Описание</b>\n{desc}\n'
    kb=movie(await active(m.from_user.id),number)
    if poster: await m.answer_photo(poster,caption=text,reply_markup=kb,parse_mode='HTML')
    else: await m.answer(text,reply_markup=kb,parse_mode='HTML')

@router.callback_query(F.data.startswith('u:watch:'))
async def watch(c:CallbackQuery):
    if not await active(c.from_user.id): await c.answer('🔒 Ваша подписка не активна.',show_alert=True); return
    number=c.data.split(':',2)[2]
    row=await execute('SELECT title,video_file_id FROM movies WHERE number=?',(number,),one=True)
    if not row: await c.answer('Фильм не найден.',show_alert=True); return
    await c.answer()
    try: await c.message.delete()
    except Exception: pass
    await c.bot.send_video(c.from_user.id,row[1],caption=f'🎬 <b>{row[0]}</b>',reply_markup=back(),parse_mode='HTML')
    await execute('UPDATE users SET views=views+1 WHERE id=?',(c.from_user.id,))

@router.callback_query(F.data=='u:plans')
async def plan_screen(c:CallbackQuery):
    rows=await execute('SELECT days,stars FROM plans WHERE enabled=1 ORDER BY days',fetch=True)
    await c.answer(); await replace_screen(c.bot,c.from_user.id,c.message,'💎 <b>Подписка ZYNT FILMS</b>\n\nВыберите тариф. Оплата проходит внутри Telegram Stars.',plans(rows),'subscription')

@router.callback_query(F.data.startswith('u:buy:'))
async def buy(c:CallbackQuery):
    days=int(c.data.split(':')[2]); row=await execute('SELECT stars FROM plans WHERE days=? AND enabled=1',(days,),one=True)
    if not row: await c.answer('Тариф недоступен.',show_alert=True); return
    await c.answer(); await c.bot.send_invoice(c.from_user.id,f'ZYNT FILMS — {days} дней',f'Доступ к каталогу на {days} дней.',payload=f'sub:{days}:',currency='XTR',prices=[LabeledPrice(label=f'{days} дней',amount=row[0])])

@router.pre_checkout_query()
async def pre_checkout(q:PreCheckoutQuery):
    parts=q.invoice_payload.split(':')
    if len(parts)<2 or parts[0]!='sub': await q.answer(ok=False,error_message='Некорректный заказ.'); return
    try: days=int(parts[1])
    except Exception: await q.answer(ok=False,error_message='Некорректный тариф.'); return
    promo=parts[2] if len(parts)>2 else ''
    plan=await execute('SELECT stars FROM plans WHERE days=? AND enabled=1',(days,),one=True)
    if not plan: await q.answer(ok=False,error_message='Тариф недоступен.'); return
    expected=plan[0]
    if promo:
        p=await execute('SELECT days,discount,max_uses,uses,enabled FROM promo_codes WHERE code=?',(promo,),one=True)
        if not p or not p[4] or p[0]!=days or p[3]>=p[2] or await execute('SELECT 1 FROM promo_used WHERE code=? AND user_id=?',(promo,q.from_user.id),one=True):
            await q.answer(ok=False,error_message='Промокод недействителен или уже использован.'); return
        expected=discounted_stars(plan[0],p[1])
    if q.currency!='XTR' or q.total_amount!=expected:
        await q.answer(ok=False,error_message='Цена заказа изменилась. Создайте заказ заново.'); return
    await q.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(m:Message,state:FSMContext):
    sp=m.successful_payment; parts=sp.invoice_payload.split(':')
    if len(parts)<2 or parts[0]!='sub': return
    try: days=int(parts[1])
    except Exception: return
    promo=parts[2] if len(parts)>2 else ''
    plan=await execute('SELECT stars FROM plans WHERE days=? AND enabled=1',(days,),one=True)
    if not plan or sp.currency!='XTR': return
    original=plan[0]; expected=original
    if promo:
        p=await execute('SELECT days,discount,max_uses,uses,enabled FROM promo_codes WHERE code=?',(promo,),one=True)
        if not p or not p[4] or p[0]!=days or p[3]>=p[2] or await execute('SELECT 1 FROM promo_used WHERE code=? AND user_id=?',(promo,m.from_user.id),one=True): return
        expected=discounted_stars(original,p[1])
    if sp.total_amount!=expected: return
    try:
        payment_id=await execute('INSERT INTO payments(user_id,plan_days,stars,original_stars,charge_id,promo_code) VALUES(?,?,?,?,?,?)',(m.from_user.id,days,sp.total_amount,original,sp.telegram_payment_charge_id,promo or None))
    except Exception: return
    if promo:
        await execute('INSERT INTO promo_used(code,user_id) VALUES(?,?)',(promo,m.from_user.id)); await execute('UPDATE promo_codes SET uses=uses+1 WHERE code=?',(promo,))
    exp=await add_days(m.from_user.id,days)
    referral=await apply_referral_reward(payment_id,m.from_user.id,sp.total_amount)
    await state.clear()
    await m.answer(f'✅ <b>Оплата прошла успешно!</b>\n\n💎 Тариф: {days} дней\n⭐ Оплачено: <b>{sp.total_amount} Stars</b>\n⏳ До: <b>{exp.strftime("%d.%m.%Y %H:%M UTC")}</b>',reply_markup=main(),parse_mode='HTML')
    if referral:
        rid,pct,reward,bonus,level=referral
        try:
            extra=f'\n💰 Реферальный бонус: <b>{reward:.2f} ⭐</b>' if pct else ''
            if bonus: extra+='\n🎁 Вы получили <b>+3 дня</b> за 10 оплаченных приглашённых!'
            await m.bot.send_message(rid,f'👥 <b>Реферальная система</b>\n\n🏆 Уровень: <b>{level}</b>\n📈 Процент: <b>{pct}%</b>{extra}',parse_mode='HTML')
        except Exception: pass

@router.callback_query(F.data=='u:profile')
async def profile_screen(c:CallbackQuery):
    row=await execute('SELECT searches,views,referral_paid_count,referral_level,referral_balance,referral_bonus_claimed FROM users WHERE id=?',(c.from_user.id,),one=True)
    exp=await expiry(c.from_user.id); now=__import__('services.subscription',fromlist=['now']).now()
    if exp and exp>now:
        left=exp-now; sub=f'Активна\n⏳ Осталось: <b>{left.days} дн. {left.seconds//3600} ч.</b>\n📅 До: <b>{exp.strftime("%d.%m.%Y %H:%M UTC")}</b>'
    else: sub='Не приобретена'
    paid=row[2] if row else 0; lvl=level_for_count(paid); pct=percent_for_level(lvl)
    me=await c.bot.me(); link=f'https://t.me/{me.username}?start=ref_{c.from_user.id}'
    text=f'👤 <b>Ваш профиль</b>\n\n🆔 ID: <code>{c.from_user.id}</code>\n🔎 Поисков: <b>{row[0] if row else 0}</b>\n🎬 Просмотрено: <b>{row[1] if row else 0}</b>\n\n🔐 Подписка: {sub}\n\n👥 <b>Рефералы</b>\nОплативших приглашённых: <b>{paid}</b>\nУровень: <b>{lvl}</b>\nПроцент: <b>{pct}%</b>\nБаланс: <b>{(row[4] if row else 0):.2f} ⭐</b>\n🎁 +3 дня: <b>{"получен ✅" if row and row[5] else "не получен"}</b>\n\n🔗 <code>{link}</code>'
    await c.answer(); await replace_screen(c.bot,c.from_user.id,c.message,text,profile(),'profile')

@router.callback_query(F.data=='u:ref')
async def ref_screen(c:CallbackQuery):
    row=await execute('SELECT referral_paid_count,referral_level,referral_balance,referral_bonus_claimed FROM users WHERE id=?',(c.from_user.id,),one=True) or (0,0,0,0)
    count,level,balance,claimed=row; me=await c.bot.me(); link=f'https://t.me/{me.username}?start=ref_{c.from_user.id}'
    text=f'👥 <b>Реферальная система</b>\n\n🔗 Ваша ссылка:\n<code>{link}</code>\n\n🥉 1 уровень — 1 оплата → 5%\n🥈 2 уровень — 10 оплат → 10%\n🥇 3 уровень — 25 оплат → 15%\n\n✅ Оплативших приглашённых: <b>{count}</b>\n🏆 Уровень: <b>{level}</b>\n💰 Баланс: <b>{balance:.2f} ⭐</b>\n🎁 Бонус +3 дня: <b>{"получен ✅" if claimed else "после 10 оплат"}</b>'
    await c.answer(); await replace_screen(c.bot,c.from_user.id,c.message,text,back('u:profile'),'profile')

@router.callback_query(F.data=='u:promo')
async def promo_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.set_state(Promo.code)
    msg=await replace_screen(c.bot,c.from_user.id,c.message,'🎟 <b>Промокод</b>\n\nВведите код одним сообщением.',back(),'promo')
    await state.update_data(screen_message_id=msg.message_id)

@router.message(Promo.code)
async def promo_apply(m:Message,state:FSMContext):
    code=(m.text or '').strip().upper(); await delete_user_input(m); await clear_saved_screen(m.bot,m.chat.id,state)
    row=await execute('SELECT days,discount,max_uses,uses,enabled FROM promo_codes WHERE code=?',(code,),one=True)
    if not row or not row[4]: await m.answer('❌ Промокод недействителен.',reply_markup=main()); await state.clear(); return
    days,discount,max_uses,uses,_=row
    if uses>=max_uses or await execute('SELECT 1 FROM promo_used WHERE code=? AND user_id=?',(code,m.from_user.id),one=True): await m.answer('❌ Промокод уже использован или лимит исчерпан.',reply_markup=main()); await state.clear(); return
    plan=await execute('SELECT stars FROM plans WHERE days=? AND enabled=1',(days,),one=True)
    if not plan: await m.answer('❌ Тариф с таким сроком недоступен.',reply_markup=main()); await state.clear(); return
    price=discounted_stars(plan[0],discount)
    text=f'🎟 <b>Промокод применён</b>\n\n⏳ Срок: <b>{days} дней</b>\n🏷 Скидка: <b>{discount}%</b>\n💎 К оплате: <b>{price} Stars</b>'
    if price==0:
        await execute('INSERT INTO promo_used(code,user_id) VALUES(?,?)',(code,m.from_user.id)); await execute('UPDATE promo_codes SET uses=uses+1 WHERE code=?',(code,)); exp=await add_days(m.from_user.id,days)
        await state.clear(); await m.answer(text+f'\n\n✅ Оплата не требуется.\n📅 До: <b>{exp.strftime("%d.%m.%Y %H:%M UTC")}</b>',reply_markup=main(),parse_mode='HTML'); return
    await state.set_state(Promo.payment); await state.update_data(code=code,days=days,price=price)
    await m.answer(text,reply_markup=promo_payment(days,price),parse_mode='HTML')

@router.callback_query(F.data=='u:promo_pay')
async def promo_buy(c:CallbackQuery,state:FSMContext):
    data=await state.get_data(); code=data.get('code'); days=data.get('days'); price=data.get('price')
    if not code or not days or price is None: await c.answer('Сначала примените промокод.',show_alert=True); return
    p=await execute('SELECT days,discount,max_uses,uses,enabled FROM promo_codes WHERE code=?',(code,),one=True)
    plan=await execute('SELECT stars FROM plans WHERE days=? AND enabled=1',(days,),one=True)
    if not p or not plan or not p[4] or p[3]>=p[2] or await execute('SELECT 1 FROM promo_used WHERE code=? AND user_id=?',(code,c.from_user.id),one=True): await c.answer('Промокод больше недоступен.',show_alert=True); return
    real=discounted_stars(plan[0],p[1])
    if real!=price: await c.answer('Цена изменилась. Примените промокод заново.',show_alert=True); return
    await c.answer(); await c.bot.send_invoice(c.from_user.id,f'ZYNT FILMS — {days} дней',f'Промокод {code}',payload=f'sub:{days}:{code}',currency='XTR',prices=[LabeledPrice(label=f'{days} дней со скидкой',amount=real)])
