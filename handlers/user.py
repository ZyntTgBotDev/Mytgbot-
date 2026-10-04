from datetime import timezone
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_NAME
from db import add_user, execute
from services.ui import replace_screen, delete_user_input
from services.subscriptions import check_required_channels
from services.subscription import active, expiry, add_days
from keyboards.user import main, back, subscription_check, plans, movie, profile

router = Router()

class Search(StatesGroup):
    number = State()

class Promo(StatesGroup):
    code = State()

async def show_home(bot, chat_id, old=None):
    rows, missing = await check_required_channels(bot, chat_id)
    if rows and missing:
        text = "🔐 <b>Доступ ограничен</b>\n\nЧтобы использовать ZYNT FILMS, подпишитесь на все обязательные каналы и нажмите «Проверить подписку»."
        return await replace_screen(bot, chat_id, old, text, subscription_check(rows), "subscription")
    return await replace_screen(bot, chat_id, old,
        f"🎬 <b>{BOT_NAME}</b>\n\nДобро пожаловать!\n\nВведите номер фильма через кнопку ниже.",
        main(), "home")

@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await add_user(m.from_user)
    await show_home(m.bot, m.chat.id, None)

@router.callback_query(F.data=="u:checksub")
async def checksub(c: CallbackQuery):
    rows, missing = await check_required_channels(c.bot, c.from_user.id)
    if missing:
        await c.answer("❌ Подписка найдена не на все каналы.", show_alert=True)
        return
    await c.answer("✅ Подписка подтверждена!")
    await show_home(c.bot, c.from_user.id, c.message)

@router.callback_query(F.data=="u:home")
async def home(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    await show_home(c.bot, c.from_user.id, c.message)

@router.callback_query(F.data=="u:search")
async def search(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(Search.number)
    await replace_screen(c.bot,c.from_user.id,c.message,
        "🔎 <b>Поиск фильма</b>\n\nВведите номер фильма.",
        back(),"search")

@router.message(Search.number)
async def search_number(m: Message, state: FSMContext):
    number=(m.text or "").strip()
    await delete_user_input(m)
    movie_row=await execute(
        "SELECT number,title,description,year,genre,poster_file_id FROM movies WHERE number=?",
        (number,),one=True)
    await execute("UPDATE users SET searches=searches+1 WHERE id=?",(m.from_user.id,))
    if not movie_row:
        await m.answer("❌ Фильм с таким номером не найден.",reply_markup=main())
        await state.clear()
        return
    _,title,desc,year,genre,poster=movie_row
    text=f"🎬 <b>{title}</b>\n\n"
    if year: text+=f"📅 {year}\n"
    if genre: text+=f"🎭 {genre}\n"
    if desc: text+=f"\n📖 <b>Описание</b>\n{desc}\n"
    access=await active(m.from_user.id)
    kb=movie(access,number)
    if poster:
        await m.answer_photo(poster,caption=text,reply_markup=kb,parse_mode="HTML")
    else:
        await m.answer(text,reply_markup=kb,parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("u:watch:"))
async def watch(c: CallbackQuery):
    if not await active(c.from_user.id):
        await c.answer("🔒 Ваша подписка не активна.",show_alert=True)
        return
    number=c.data.split(":",2)[2]
    row=await execute("SELECT title,video_file_id FROM movies WHERE number=?",(number,),one=True)
    if not row:
        await c.answer("Фильм не найден.",show_alert=True); return
    await c.answer()
    try: await c.message.delete()
    except: pass
    await c.bot.send_video(c.from_user.id,row[1],caption=f"🎬 <b>{row[0]}</b>",parse_mode="HTML")
    await execute("UPDATE users SET views=views+1 WHERE id=?",(c.from_user.id,))

@router.callback_query(F.data=="u:plans")
async def plan_screen(c: CallbackQuery):
    await c.answer()
    rows=await execute("SELECT days,stars FROM plans WHERE enabled=1 ORDER BY days",fetch=True)
    await replace_screen(c.bot,c.from_user.id,c.message,
        "💎 <b>Подписка ZYNT FILMS</b>\n\nВыберите тариф. Оплата проходит внутри Telegram Stars.",
        plans(rows),"subscription")

@router.callback_query(F.data.startswith("u:buy:"))
async def buy(c: CallbackQuery):
    days=int(c.data.split(":")[2])
    row=await execute("SELECT stars FROM plans WHERE days=? AND enabled=1",(days,),one=True)
    if not row:
        await c.answer("Тариф недоступен.",show_alert=True); return
    await c.answer()
    await c.bot.send_invoice(
        c.from_user.id, f"ZYNT FILMS — {days} дней",
        f"Доступ к каталогу ZYNT FILMS на {days} дней.",
        payload=f"sub:{days}",currency="XTR",
        prices=[LabeledPrice(label=f"{days} дней",amount=row[0])]
    )

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    payload=q.invoice_payload
    if not payload.startswith("sub:"):
        await q.answer(ok=False,error_message="Некорректный заказ."); return
    try: days=int(payload.split(":")[1])
    except: days=0
    row=await execute("SELECT stars FROM plans WHERE days=? AND enabled=1",(days,),one=True)
    if not row or q.currency!="XTR" or q.total_amount!=row[0]:
        await q.answer(ok=False,error_message="Тариф изменился. Создайте новый заказ.")
        return
    await q.answer(ok=True)

@router.message(F.successful_payment)
async def payment(m: Message):
    sp=m.successful_payment
    if not sp.invoice_payload.startswith("sub:"): return
    days=int(sp.invoice_payload.split(":")[1])
    row=await execute("SELECT stars FROM plans WHERE days=? AND enabled=1",(days,),one=True)
    if not row or sp.currency!="XTR" or sp.total_amount!=row[0]:
        return
    # charge_id is unique, so duplicate delivery is prevented at DB level.
    try:
        await execute("INSERT INTO payments(user_id,plan_days,stars,charge_id) VALUES(?,?,?,?)",
                      (m.from_user.id,days,sp.total_amount,sp.telegram_payment_charge_id))
    except Exception:
        return
    exp=await add_days(m.from_user.id,days)
    await m.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"💎 Тариф: {days} дней\n"
        f"⏳ Действует до: <b>{exp.astimezone(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}</b>\n\n"
        "Теперь при поиске фильма он будет доступен для просмотра.",
        reply_markup=main(),parse_mode="HTML")

@router.callback_query(F.data=="u:profile")
async def profile_screen(c: CallbackQuery):
    await c.answer()
    row=await execute("SELECT searches,views FROM users WHERE id=?",(c.from_user.id,),one=True)
    exp=await expiry(c.from_user.id)
    if exp:
        now=__import__("services.subscription",fromlist=["now"]).now()
        if exp>now:
            left=exp-now
            days=left.days; hours=left.seconds//3600
            sub=f"Активна\n⏳ Осталось: <b>{days} дн. {hours} ч.</b>\n📅 До: <b>{exp.strftime('%d.%m.%Y %H:%M UTC')}</b>"
        else: sub="Не приобретена"
    else: sub="Не приобретена"
    text=f"👤 <b>Ваш профиль</b>\n\n🆔 ID: <code>{c.from_user.id}</code>\n🔎 Поисков: <b>{row[0] if row else 0}</b>\n🎬 Просмотрено: <b>{row[1] if row else 0}</b>\n\n🔐 Подписка: {sub}"
    await replace_screen(c.bot,c.from_user.id,c.message,text,profile(),"profile")

@router.callback_query(F.data=="u:promo")
async def promo_start(c: CallbackQuery,state:FSMContext):
    await c.answer()
    await state.set_state(Promo.code)
    await replace_screen(c.bot,c.from_user.id,c.message,
        "🎟 <b>Промокод</b>\n\nВведите промокод одним сообщением.",
        back(),"promo")

@router.message(Promo.code)
async def promo_apply(m: Message,state:FSMContext):
    code=(m.text or "").strip().upper()
    await delete_user_input(m)
    row=await execute("SELECT days,max_uses,uses,enabled FROM promo_codes WHERE code=?",(code,),one=True)
    if not row or not row[3]:
        await m.answer("❌ Промокод недействителен.",reply_markup=main()); await state.clear(); return
    days,max_uses,uses,_=row
    if uses>=max_uses:
        await m.answer("❌ Лимит активаций промокода исчерпан.",reply_markup=main()); await state.clear(); return
    if await execute("SELECT 1 FROM promo_used WHERE code=? AND user_id=?",(code,m.from_user.id),one=True):
        await m.answer("❌ Вы уже использовали этот промокод.",reply_markup=main()); await state.clear(); return
    await execute("INSERT INTO promo_used(code,user_id) VALUES(?,?)",(code,m.from_user.id))
    await execute("UPDATE promo_codes SET uses=uses+1 WHERE code=?",(code,))
    exp=await add_days(m.from_user.id,days)
    await m.answer(f"✅ Промокод активирован!\n\n💎 Добавлено: <b>{days} дней</b>\n📅 До: <b>{exp.strftime('%d.%m.%Y %H:%M UTC')}</b>",reply_markup=main(),parse_mode="HTML")
    await state.clear()
