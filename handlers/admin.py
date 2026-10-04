from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import OWNER_ID
from db import execute, is_admin
from keyboards.admin import menu, back
from services.ui import image_id

router=Router()

class A(StatesGroup):
    action=State()
    data=State()

async def guard(obj):
    uid=obj.from_user.id
    return await is_admin(uid)

async def show_admin(c, text="⚙️ <b>ZYNT FILMS — Админ-панель</b>"):
    await c.message.edit_text(text,reply_markup=menu(c.from_user.id==OWNER_ID),parse_mode="HTML")

@router.message(F.text=="/admin")
async def admin_cmd(m:Message):
    if not await is_admin(m.from_user.id): return
    await m.answer("⚙️ <b>ZYNT FILMS — Админ-панель</b>",reply_markup=menu(m.from_user.id==OWNER_ID),parse_mode="HTML")

@router.callback_query(F.data=="a:home")
async def admin_home(c:CallbackQuery,state:FSMContext):
    await state.clear()
    if await guard(c):
        await c.answer()
        await show_admin(c)

@router.callback_query(F.data=="a:stats")
async def stats(c:CallbackQuery):
    if not await guard(c): return
    u=(await execute("SELECT COUNT(*) FROM users",one=True))[0]
    m=(await execute("SELECT COUNT(*) FROM movies",one=True))[0]
    p=(await execute("SELECT COUNT(*) FROM payments",one=True))[0]
    stars=(await execute("SELECT COALESCE(SUM(stars),0) FROM payments",one=True))[0]
    active=(await execute("SELECT COUNT(*) FROM subscriptions WHERE expires_at>datetime('now')",one=True))[0]
    await c.answer()
    await c.message.edit_text(f"📊 <b>Статистика</b>\n\n👥 Пользователей: <b>{u}</b>\n🔐 Активных подписок: <b>{active}</b>\n🎬 Фильмов: <b>{m}</b>\n💳 Платежей: <b>{p}</b>\n⭐ Получено Stars: <b>{stars}</b>",reply_markup=back(),parse_mode="HTML")

@router.callback_query(F.data=="a:users")
async def users(c:CallbackQuery):
    if not await guard(c): return
    rows=await execute("SELECT COUNT(*),COALESCE(SUM(searches),0),COALESCE(SUM(views),0) FROM users",one=True)
    await c.answer()
    await c.message.edit_text(f"👥 <b>Пользователи</b>\n\nВсего: <b>{rows[0]}</b>\nПоисков: <b>{rows[1]}</b>\nПросмотров: <b>{rows[2]}</b>",reply_markup=back(),parse_mode="HTML")

@router.callback_query(F.data=="a:channels")
async def channels(c:CallbackQuery):
    if not await guard(c): return
    rows=await execute("SELECT id,chat_id,title,username FROM channels ORDER BY id",fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text="➕ Добавить канал",callback_data="a:chadd")]]
    for i,cid,title,username in rows:
        kb.append([InlineKeyboardButton(text=f"🗑 {title or username or cid}",callback_data=f"a:chdel:{i}")])
    kb.append([InlineKeyboardButton(text="◀️ Админка",callback_data="a:home")])
    txt="📢 <b>Обязательная подписка</b>\n\n"+("\n".join(f"• {t or u or cid}" for _,cid,t,u in rows) if rows else "Каналы не добавлены.")
    await c.answer(); await c.message.edit_text(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@router.callback_query(F.data=="a:chadd")
async def chadd(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await c.answer(); await state.set_state(A.action); await state.update_data(action="channel")
    await c.message.edit_text("📢 <b>Добавление канала</b>\n\nОтправьте одной строкой:\n<code>@username | https://t.me/...</code>\n\nДля публичного канала ссылка после | необязательна.",reply_markup=back(),parse_mode="HTML")

@router.callback_query(F.data.startswith("a:chdel:"))
async def chdel(c:CallbackQuery):
    if not await guard(c): return
    await execute("DELETE FROM channels WHERE id=?",(int(c.data.rsplit(":",1)[1]),))
    await channels(c)

@router.callback_query(F.data=="a:images")
async def images(c:CallbackQuery):
    if not await guard(c): return
    rows=await execute("SELECT key FROM images ORDER BY key",fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    keys=["home","subscription","search","profile","promo","admin"]
    kb=[[InlineKeyboardButton(text=f"🖼 {k} {'✅' if any(r[0]==k for r in rows) else '—'}",callback_data=f"a:img:{k}")] for k in keys]
    kb.append([InlineKeyboardButton(text="◀️ Админка",callback_data="a:home")])
    await c.answer(); await c.message.edit_text("🖼 <b>Изображения экранов</b>\n\nВыберите экран и отправьте новую фотографию.",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@router.callback_query(F.data.startswith("a:img:"))
async def image_select(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    key=c.data.split(":")[-1]
    await state.set_state(A.action); await state.update_data(action="image",key=key)
    await c.answer(); await c.message.edit_text(f"🖼 Отправьте фотографию для экрана <b>{key}</b>.",reply_markup=back(),parse_mode="HTML")

@router.callback_query(F.data=="a:plans")
async def plans(c:CallbackQuery):
    if not await guard(c): return
    rows=await execute("SELECT days,stars,enabled FROM plans ORDER BY days",fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text=f"✏️ {d} дней — {s} ⭐",callback_data=f"a:plan:{d}")] for d,s,e in rows]
    kb.append([InlineKeyboardButton(text="◀️ Админка",callback_data="a:home")])
    await c.answer(); await c.message.edit_text("💎 <b>Тарифы</b>\n\nНажмите на тариф, чтобы изменить цену.",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@router.callback_query(F.data.startswith("a:plan:"))
async def plan_select(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    days=int(c.data.split(":")[-1])
    row=await execute("SELECT stars FROM plans WHERE days=?",(days,),one=True)
    await state.set_state(A.action); await state.update_data(action="plan",days=days)
    await c.answer(); await c.message.edit_text(f"💎 {days} дней\n\nТекущая цена: <b>{row[0]} Stars</b>\n\nОтправьте новую цену целым числом.",reply_markup=back(),parse_mode="HTML")

@router.callback_query(F.data=="a:promos")
async def promos(c:CallbackQuery):
    if not await guard(c): return
    rows=await execute("SELECT code,days,max_uses,uses,enabled FROM promo_codes ORDER BY code",fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text="➕ Создать промокод",callback_data="a:promoadd")]]
    for code,d,lim,uses,en in rows:
        kb.append([InlineKeyboardButton(text=f"🗑 {code} ({uses}/{lim})",callback_data=f"a:promodel:{code}")])
    kb.append([InlineKeyboardButton(text="◀️ Админка",callback_data="a:home")])
    text="🎟 <b>Промокоды</b>\n\n"+("\n".join(f"• <code>{c}</code> — +{d} дн. — {u}/{l}" for c,d,l,u,e in rows) if rows else "Пока нет промокодов.")
    await c.answer(); await c.message.edit_text(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@router.callback_query(F.data=="a:promoadd")
async def promoadd(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.set_state(A.action); await state.update_data(action="promo")
    await c.answer(); await c.message.edit_text("🎟 Отправьте промокод, количество дней и лимит через `;`\n\nПример:\n<code>MOVIE2026;7;100</code>",reply_markup=back(),parse_mode="HTML")

@router.callback_query(F.data.startswith("a:promodel:"))
async def promodel(c:CallbackQuery):
    if not await guard(c): return
    code=c.data.split(":",2)[2]
    await execute("DELETE FROM promo_codes WHERE code=?",(code,))
    await promos(c)

@router.callback_query(F.data=="a:admins")
async def admins(c:CallbackQuery):
    if c.from_user.id!=OWNER_ID: await c.answer("Только главный администратор",show_alert=True); return
    rows=await execute("SELECT user_id FROM admins ORDER BY user_id",fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text="➕ Добавить администратора",callback_data="a:addadmin")]]
    for (uid,) in rows: kb.append([InlineKeyboardButton(text=f"🗑 {uid}",callback_data=f"a:deladmin:{uid}")])
    kb.append([InlineKeyboardButton(text="◀️ Админка",callback_data="a:home")])
    await c.answer(); await c.message.edit_text("👑 <b>Администраторы</b>\n\nГлавный: <code>%s</code>\n\n%s"%(OWNER_ID,"\n".join(f"• {r[0]}" for r in rows) or "Нет дополнительных админов."),reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@router.callback_query(F.data=="a:addadmin")
async def addadmin(c:CallbackQuery,state:FSMContext):
    if c.from_user.id!=OWNER_ID:return
    await state.set_state(A.action); await state.update_data(action="addadmin")
    await c.answer(); await c.message.edit_text("👑 Отправьте Telegram ID нового администратора.",reply_markup=back())

@router.callback_query(F.data.startswith("a:deladmin:"))
async def deladmin(c:CallbackQuery):
    if c.from_user.id!=OWNER_ID:return
    await execute("DELETE FROM admins WHERE user_id=?",(int(c.data.rsplit(":",1)[1]),))
    await admins(c)

@router.callback_query(F.data=="a:movies")
async def movies(c:CallbackQuery):
    if not await guard(c): return
    rows=await execute("SELECT number,title FROM movies ORDER BY number LIMIT 30",fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text="➕ Добавить фильм",callback_data="a:movieadd")]]
    for n,t in rows: kb.append([InlineKeyboardButton(text=f"🗑 {n} — {t[:35]}",callback_data=f"a:moviedel:{n}")])
    kb.append([InlineKeyboardButton(text="◀️ Админка",callback_data="a:home")])
    text="🎬 <b>Фильмы</b>\n\n"+("\n".join(f"• <code>{n}</code> — {t}" for n,t in rows) if rows else "Каталог пуст.")
    await c.answer(); await c.message.edit_text(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@router.callback_query(F.data=="a:movieadd")
async def movieadd(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    await state.set_state(A.action); await state.update_data(action="movie_video",movie={})
    await c.answer(); await c.message.edit_text("🎬 <b>Добавление фильма</b>\n\n1/6 Отправьте видео фильма.",reply_markup=back(),parse_mode="HTML")

@router.callback_query(F.data.startswith("a:moviedel:"))
async def moviedel(c:CallbackQuery):
    if not await guard(c):return
    await execute("DELETE FROM movies WHERE number=?",(c.data.split(":",2)[2],))
    await movies(c)

@router.callback_query(F.data=="a:broadcast")
async def broadcast(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    await state.set_state(A.action); await state.update_data(action="broadcast")
    await c.answer(); await c.message.edit_text(
        "📢 <b>Рассылка</b>\n\nОтправьте сюда сообщение, которое нужно разослать.\n"
        "Поддерживаются текст, фото, видео, GIF, документ, аудио, голосовые и стикеры.\n"
        "Кнопки/ссылки из исходного сообщения сохраняются при копировании.",
        reply_markup=back(),parse_mode="HTML")

@router.message(A.action)
async def admin_input(m:Message,state:FSMContext):
    if not await is_admin(m.from_user.id): return
    data=await state.get_data(); action=data.get("action")
    if action=="channel":
        parts=[x.strip() for x in (m.text or "").split("|",1)]
        ref=parts[0]; invite=parts[1] if len(parts)>1 else None
        try:
            chat=await m.bot.get_chat(ref)
            username=getattr(chat,"username",None)
            await execute("INSERT OR REPLACE INTO channels(chat_id,title,username,invite_url) VALUES(?,?,?,?)",(str(chat.id),chat.title or ref,username,invite))
            await m.answer("✅ Канал добавлен. Бот должен быть администратором канала для проверки подписки.",reply_markup=menu(m.from_user.id==OWNER_ID))
        except Exception:
            await m.answer("❌ Не удалось получить канал. Проверьте @username/ID и права бота.",reply_markup=menu(m.from_user.id==OWNER_ID))
        await state.clear(); return
    if action=="image":
        if not m.photo:
            await m.answer("❌ Нужна фотография."); return
        key=data["key"]; fid=m.photo[-1].file_id
        await execute("INSERT INTO images(key,file_id) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET file_id=excluded.file_id",(key,fid))
        await m.answer(f"✅ Изображение «{key}» сохранено.",reply_markup=menu(m.from_user.id==OWNER_ID))
        await state.clear(); return
    if action=="plan":
        try:
            price=int((m.text or "").strip())
            await execute("UPDATE plans SET stars=? WHERE days=?",(price,data["days"]))
            await m.answer("✅ Цена обновлена.",reply_markup=menu(m.from_user.id==OWNER_ID))
            await state.clear()
        except: await m.answer("❌ Введите целое число Stars."); 
        return
    if action=="promo":
        try:
            code,days,limit=[x.strip() for x in m.text.split(";")]
            days=int(days);limit=int(limit)
            if days<=0 or limit<=0: raise ValueError
            await execute("INSERT OR REPLACE INTO promo_codes(code,days,max_uses,uses,enabled) VALUES(?,?,?,0,1)",(code.upper(),days,limit))
            await m.answer("✅ Промокод создан.",reply_markup=menu(m.from_user.id==OWNER_ID)); await state.clear()
        except: await m.answer("❌ Формат: КОД;дни;лимит. Например MOVIE2026;7;100")
        return
    if action=="addadmin":
        try:
            uid=int((m.text or "").strip())
            if uid==OWNER_ID: raise ValueError
            await execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)",(uid,))
            await m.answer("✅ Администратор добавлен.",reply_markup=menu(True)); await state.clear()
        except: await m.answer("❌ Нужен корректный Telegram ID.")
        return
    if action=="movie_video":
        if not m.video: await m.answer("❌ Отправьте именно видео."); return
        movie=data["movie"];movie["video"]=m.video.file_id
        await state.update_data(action="movie_number",movie=movie)
        await m.answer("2/6 Введите номер фильма.")
        return
    if action=="movie_number":
        movie=data["movie"];movie["number"]=(m.text or "").strip()
        if not movie["number"]: await m.answer("❌ Номер не может быть пустым.");return
        await state.update_data(action="movie_title",movie=movie);await m.answer("3/6 Введите название.")
        return
    if action=="movie_title":
        movie=data["movie"];movie["title"]=(m.text or "").strip()
        await state.update_data(action="movie_desc",movie=movie);await m.answer("4/6 Введите описание.")
        return
    if action=="movie_desc":
        movie=data["movie"];movie["description"]=m.text or ""
        await state.update_data(action="movie_meta",movie=movie);await m.answer("5/6 Отправьте год и жанр через `;`\nНапример: `2014;Фантастика, драма`")
        return
    if action=="movie_meta":
        try: year,genre=[x.strip() for x in m.text.split(";",1)]
        except: await m.answer("❌ Формат: год;жанр");return
        movie=data["movie"];movie["year"]=year;movie["genre"]=genre
        await state.update_data(action="movie_poster",movie=movie);await m.answer("6/6 Отправьте постер фильма фотографией.")
        return
    if action=="movie_poster":
        if not m.photo: await m.answer("❌ Отправьте фотографию-постер.");return
        movie=data["movie"];movie["poster"]=m.photo[-1].file_id
        await execute("INSERT OR REPLACE INTO movies(number,title,description,year,genre,poster_file_id,video_file_id) VALUES(?,?,?,?,?,?,?)",
                      (movie["number"],movie["title"],movie["description"],movie["year"],movie["genre"],movie["poster"],movie["video"]))
        await m.answer("✅ Фильм добавлен в каталог.",reply_markup=menu(m.from_user.id==OWNER_ID));await state.clear()
        return
    if action=="broadcast":
        users=await execute("SELECT id FROM users",fetch=True)
        ok=bad=0
        for (uid,) in users:
            try:
                await m.bot.copy_message(uid,m.chat.id,m.message_id)
                ok+=1
            except Exception:
                bad+=1
        await m.answer(f"📢 <b>Рассылка завершена</b>\n\n✅ Успешно: {ok}\n❌ Ошибок: {bad}",reply_markup=menu(m.from_user.id==OWNER_ID),parse_mode="HTML")
        await state.clear()
