from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import OWNER_ID
from db import execute, is_admin
from keyboards.admin import menu, back, discounts
from services.subscription import add_days, remove as remove_subscription

router=Router()

class A(StatesGroup):
    action=State()

async def guard(obj):
    return await is_admin(obj.from_user.id)

async def notify_role(bot, uid, added):
    try:
        if added:
            await bot.send_message(uid,'🎉 <b>Поздравляем!</b>\n\nВам назначена роль администратора ZYNT FILMS.\nТеперь вам доступны административные функции бота.',parse_mode='HTML')
        else:
            await bot.send_message(uid,'ℹ️ Ваша роль администратора ZYNT FILMS была снята.\nСпасибо за вашу работу! ❤️')
    except Exception:
        pass

@router.message(Command("versionup"))
async def versionup_cmd(m: Message):
    if not await is_admin(m.from_user.id):
        return
    row = await execute('SELECT version,description,image_file_id FROM bot_version WHERE id=1', one=True)
    version, description, image_file_id = row or ('1.0.0', '', None)
    caption = f"🚀 <b>ZYNT FILMS — версия {version}</b>\n\n{description or 'Информация об обновлении пока не добавлена.'}"
    if image_file_id:
        await m.answer_photo(image_file_id, caption=caption, parse_mode='HTML')
    else:
        await m.answer(caption, parse_mode='HTML')

@router.callback_query(F.data=='a:version')
async def version_settings(c: CallbackQuery, state: FSMContext):
    if not await guard(c): return
    await state.clear()
    row = await execute('SELECT version,description,image_file_id FROM bot_version WHERE id=1', one=True)
    version, description, image_file_id = row or ('1.0.0', '', None)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔢 Изменить версию', callback_data='a:version:editver')],
        [InlineKeyboardButton(text='📝 Изменить описание', callback_data='a:version:editdesc')],
        [InlineKeyboardButton(text=f"🖼 Изображение {'✅' if image_file_id else '—'}", callback_data='a:version:editimg')],
        [InlineKeyboardButton(text='👁 Предпросмотр', callback_data='a:version:preview')],
        [InlineKeyboardButton(text='◀️ Админка', callback_data='a:home')]
    ])
    text = f"🚀 <b>Версия / обновление</b>\n\n<b>Версия:</b> <code>{version}</code>\n<b>Описание:</b> {description or '—'}\n<b>Изображение:</b> {'установлено' if image_file_id else 'нет'}"
    await c.answer()
    await c.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@router.callback_query(F.data=='a:version:editver')
async def version_editver(c: CallbackQuery, state: FSMContext):
    if not await guard(c): return
    await state.set_state(A.action)
    await state.update_data(action='version_version')
    await c.answer()
    await c.message.edit_text('🔢 Отправьте номер новой версии.\nНапример: <code>2.1.0</code>', reply_markup=back(), parse_mode='HTML')

@router.callback_query(F.data=='a:version:editdesc')
async def version_editdesc(c: CallbackQuery, state: FSMContext):
    if not await guard(c): return
    await state.set_state(A.action)
    await state.update_data(action='version_description')
    await c.answer()
    await c.message.edit_text('📝 Отправьте краткое описание обновления.', reply_markup=back(), parse_mode='HTML')

@router.callback_query(F.data=='a:version:editimg')
async def version_editimg(c: CallbackQuery, state: FSMContext):
    if not await guard(c): return
    await state.set_state(A.action)
    await state.update_data(action='version_image')
    await c.answer()
    await c.message.edit_text('🖼 Отправьте фотографию для сообщения /versionup.', reply_markup=back(), parse_mode='HTML')

@router.callback_query(F.data=='a:version:preview')
async def version_preview(c: CallbackQuery):
    if not await guard(c): return
    row = await execute('SELECT version,description,image_file_id FROM bot_version WHERE id=1', one=True)
    version, description, image_file_id = row or ('1.0.0', '', None)
    caption = f"🚀 <b>ZYNT FILMS — версия {version}</b>\n\n{description or 'Информация об обновлении пока не добавлена.'}"
    await c.answer()
    if image_file_id:
        await c.message.answer_photo(image_file_id, caption=caption, parse_mode='HTML')
    else:
        await c.message.answer(caption, parse_mode='HTML')

@router.message(F.text=='/admin')
async def admin_cmd(m:Message):
    if await is_admin(m.from_user.id):
        await m.answer('⚙️ <b>ZYNT FILMS — Админ-панель</b>',reply_markup=menu(m.from_user.id==OWNER_ID),parse_mode='HTML')

@router.callback_query(F.data=='a:home')
async def home(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.clear(); await c.answer()
    await c.message.edit_text('⚙️ <b>ZYNT FILMS — Админ-панель</b>',reply_markup=menu(c.from_user.id==OWNER_ID),parse_mode='HTML')


@router.callback_query(F.data=='a:movies')
async def movies(c:CallbackQuery):
    if not await guard(c): return
    rows=await execute('SELECT number,title FROM movies ORDER BY number LIMIT 50',fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text='➕ Добавить фильм',callback_data='a:movieadd')],[InlineKeyboardButton(text='✏️ Изменить фильм',callback_data='a:movieedit')]]
    kb += [[InlineKeyboardButton(text=f'🗑 {n} — {t[:35]}',callback_data=f'a:moviedel:{n}')] for n,t in rows]
    kb.append([InlineKeyboardButton(text='◀️ Админка',callback_data='a:home')])
    text='🎬 <b>Фильмы</b>\n\n'+('\n'.join(f'• <code>{n}</code> — {t}' for n,t in rows) if rows else 'Каталог пуст.')
    await c.answer(); await c.message.edit_text(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode='HTML')

@router.callback_query(F.data=='a:movieadd')
async def movieadd(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.set_state(A.action); await state.update_data(action='movie_video',movie={}); await c.answer(); await c.message.edit_text('🎬 <b>Добавление фильма</b>\n\n1/6 Отправьте видео фильма.',reply_markup=back(),parse_mode='HTML')

@router.callback_query(F.data.startswith('a:moviedel:'))
async def moviedel(c:CallbackQuery):
    if not await guard(c): return
    number=c.data.split(':',2)[2]; await execute('DELETE FROM movies WHERE number=?',(number,)); await c.answer('Фильм удалён.',show_alert=True); await movies(c)

@router.callback_query(F.data=='a:movieedit')
async def movieedit(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.set_state(A.action); await state.update_data(action='movie_edit_number'); await c.answer(); await c.message.edit_text('✏️ Введите номер фильма для редактирования:',reply_markup=back())

@router.callback_query(F.data.startswith('a:moviefield:'))
async def moviefield(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    field=c.data.split(':')[2]; data=await state.get_data(); number=data.get('movie_number')
    if not number: await c.answer('Сначала выберите фильм.',show_alert=True); return
    await state.set_state(A.action); await state.update_data(action='movie_edit_value',field=field); await c.answer();
    prompts={'title':'Название','description':'Описание','year':'Год','genre':'Жанр','poster':'Постер-фото','video':'Видео'}
    await c.message.edit_text(f'✏️ Отправьте новое значение: <b>{prompts.get(field,field)}</b>',reply_markup=back(),parse_mode='HTML')

@router.callback_query(F.data.startswith('a:moviefields'))
async def moviefields(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    data=await state.get_data(); number=data.get('movie_number')
    if not number: await c.answer('Фильм не выбран.',show_alert=True);return
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Название',callback_data='a:moviefield:title'),InlineKeyboardButton(text='Описание',callback_data='a:moviefield:description')],[InlineKeyboardButton(text='Год',callback_data='a:moviefield:year'),InlineKeyboardButton(text='Жанр',callback_data='a:moviefield:genre')],[InlineKeyboardButton(text='Постер',callback_data='a:moviefield:poster'),InlineKeyboardButton(text='Видео',callback_data='a:moviefield:video')],[InlineKeyboardButton(text='◀️ Назад',callback_data='a:movies')]])
    await c.answer(); await c.message.edit_text(f'✏️ <b>Фильм {number}</b>\nВыберите поле:',reply_markup=kb,parse_mode='HTML')

@router.callback_query(F.data=='a:stats')
async def stats(c:CallbackQuery):
    if not await guard(c): return
    u=(await execute('SELECT COUNT(*) FROM users',one=True))[0]; m=(await execute('SELECT COUNT(*) FROM movies',one=True))[0]
    p=(await execute('SELECT COUNT(*) FROM payments',one=True))[0]; stars=(await execute('SELECT COALESCE(SUM(stars),0) FROM payments',one=True))[0]
    active=(await execute("SELECT COUNT(*) FROM subscriptions WHERE expires_at>datetime('now')",one=True))[0]
    refs=(await execute('SELECT COALESCE(SUM(referral_paid_count),0) FROM users',one=True))[0]
    await c.answer(); await c.message.edit_text(f'📊 <b>Статистика</b>\n\n👥 Пользователей: <b>{u}</b>\n🔐 Активных подписок: <b>{active}</b>\n🎬 Фильмов: <b>{m}</b>\n💳 Платежей: <b>{p}</b>\n⭐ Получено Stars: <b>{stars}</b>\n👥 Оплаченных рефералов: <b>{refs}</b>',reply_markup=back(),parse_mode='HTML')

@router.callback_query(F.data=='a:users')
async def users(c:CallbackQuery):
    if not await guard(c): return
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔎 Найти по Telegram ID',callback_data='a:userfind')],[InlineKeyboardButton(text='◀️ Админка',callback_data='a:home')]])
    await c.answer(); await c.message.edit_text('👤 <b>Пользователи</b>\n\nНайти пользователя можно по Telegram ID.',reply_markup=kb,parse_mode='HTML')

@router.callback_query(F.data=='a:userfind')
async def userfind(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.set_state(A.action); await state.update_data(action='userfind'); await c.answer(); await c.message.edit_text('🔎 Введите Telegram ID пользователя:',reply_markup=back())

@router.callback_query(F.data.startswith('a:user:'))
async def user_panel(c:CallbackQuery):
    if not await guard(c): return
    uid=int(c.data.split(':')[2]); row=await execute('SELECT id,username,first_name,searches,views,blocked,referral_paid_count,referral_level,referral_balance FROM users WHERE id=?',(uid,),one=True)
    if not row: await c.answer('Пользователь не найден.',show_alert=True); return
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    from services.subscription import expiry
    exp=await expiry(uid); sub=exp.strftime('%d.%m.%Y %H:%M UTC') if exp else 'не приобретена'
    text=f'👤 <b>Пользователь</b>\n\n🆔 <code>{row[0]}</code>\n👤 @{row[1] or "—"}\n🔎 Поисков: <b>{row[3]}</b>\n🎬 Просмотров: <b>{row[4]}</b>\n🚫 Заблокирован: <b>{"да" if row[5] else "нет"}</b>\n🔐 Подписка до: <b>{sub}</b>\n👥 Оплаченных рефералов: <b>{row[6]}</b>\n🏆 Уровень: <b>{row[7]}</b>\n💰 Реф. баланс: <b>{row[8]:.2f} ⭐</b>'
    toggle='✅ Разблокировать' if row[5] else '🚫 Заблокировать'
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='➕ Добавить подписку',callback_data=f'a:addsub:{uid}')],[InlineKeyboardButton(text='➖ Удалить подписку',callback_data=f'a:delsub:{uid}')],[InlineKeyboardButton(text=toggle,callback_data=f'a:block:{uid}:{0 if row[5] else 1}')],[InlineKeyboardButton(text='📩 Написать',callback_data=f'a:write:{uid}')],[InlineKeyboardButton(text='◀️ Пользователи',callback_data='a:users')]])
    await c.answer(); await c.message.edit_text(text,reply_markup=kb,parse_mode='HTML')

@router.callback_query(F.data.startswith('a:addsub:'))
async def addsub(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    uid=int(c.data.split(':')[2]); await state.set_state(A.action); await state.update_data(action='addsub',uid=uid); await c.answer()
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    await c.message.edit_text('💎 Выберите срок подписки:',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='7 дней',callback_data='a:subdays:7')],[InlineKeyboardButton(text='30 дней',callback_data='a:subdays:30')],[InlineKeyboardButton(text='90 дней',callback_data='a:subdays:90')],[InlineKeyboardButton(text='◀️ Назад',callback_data=f'a:user:{uid}')]]))

@router.callback_query(F.data.startswith('a:subdays:'))
async def subdays(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    data=await state.get_data(); uid=data.get('uid'); days=int(c.data.split(':')[2])
    exp=await add_days(uid,days); await state.clear(); await c.answer('Подписка выдана.')
    try: await c.bot.send_message(uid,f'🎉 Вам выдали подписку на <b>{days} дней</b>.\n📅 До: <b>{exp.strftime("%d.%m.%Y %H:%M UTC")}</b>',parse_mode='HTML')
    except Exception: pass
    await c.message.edit_text('✅ Подписка выдана.',reply_markup=back(),parse_mode='HTML')

@router.callback_query(F.data.startswith('a:delsub:'))
async def delsub(c:CallbackQuery):
    if not await guard(c): return
    uid=int(c.data.split(':')[2]); await remove_subscription(uid); await c.answer('Подписка удалена.',show_alert=True)
    try: await c.bot.send_message(uid,'ℹ️ Ваша подписка была снята администрацией.')
    except Exception: pass
    await c.message.edit_text('✅ Подписка удалена.',reply_markup=back(),parse_mode='HTML')

@router.callback_query(F.data.startswith('a:block:'))
async def block(c:CallbackQuery):
    if not await guard(c): return
    _,_,uid_s,val=c.data.split(':');uid=int(uid_s);blocked=int(val)
    await execute('UPDATE users SET blocked=? WHERE id=?',(blocked,uid)); await c.answer('Готово')
    try: await c.bot.send_message(uid,'🚫 Ваш аккаунт заблокирован.' if blocked else '✅ Ваш аккаунт разблокирован.')
    except Exception: pass
    await user_panel(c)

@router.callback_query(F.data.startswith('a:write:'))
async def write(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    uid=int(c.data.split(':')[2]); await state.set_state(A.action); await state.update_data(action='write',uid=uid); await c.answer(); await c.message.edit_text('📩 Отправьте сообщение пользователю:',reply_markup=back())

@router.callback_query(F.data=='a:channels')
async def channels(c:CallbackQuery):
    if not await guard(c): return
    rows=await execute('SELECT id,chat_id,title,username FROM channels ORDER BY id',fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text='➕ Добавить канал',callback_data='a:chadd')]]+[[InlineKeyboardButton(text=f'🗑 {t or u or cid}',callback_data=f'a:chdel:{i}')] for i,cid,t,u in rows]+[[InlineKeyboardButton(text='◀️ Админка',callback_data='a:home')]]
    await c.answer(); await c.message.edit_text('📢 <b>Обязательная подписка</b>\n\n'+('\n'.join(f'• {t or u or cid}' for _,cid,t,u in rows) if rows else 'Каналы не добавлены.'),reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode='HTML')

@router.callback_query(F.data=='a:chadd')
async def chadd(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    await state.set_state(A.action); await state.update_data(action='channel'); await c.answer(); await c.message.edit_text('📢 Отправьте @username канала. Бот должен быть администратором канала.',reply_markup=back())

@router.callback_query(F.data.startswith('a:chdel:'))
async def chdel(c:CallbackQuery):
    if not await guard(c):return
    await execute('DELETE FROM channels WHERE id=?',(int(c.data.split(':')[2]),)); await channels(c)

@router.callback_query(F.data=='a:images')
async def images(c:CallbackQuery):
    if not await guard(c): return
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    keys=['home','subscription','search','profile','promo','admin']
    have={r[0] for r in await execute('SELECT key FROM images',fetch=True)}
    kb=[[InlineKeyboardButton(text=f'🖼 {k} {"✅" if k in have else "—"}',callback_data=f'a:img:{k}')] for k in keys]+[[InlineKeyboardButton(text='◀️ Админка',callback_data='a:home')]]
    await c.answer(); await c.message.edit_text('🖼 <b>Изображения экранов</b>\n\nВыберите нужный экран и отправьте новую фотографию.',reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode='HTML')

@router.callback_query(F.data.startswith('a:img:'))
async def image_select(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    key=c.data.split(':')[2]; await state.set_state(A.action); await state.update_data(action='image',key=key); await c.answer(); await c.message.edit_text(f'🖼 Отправьте фотографию для экрана <b>{key}</b>.',reply_markup=back(),parse_mode='HTML')

@router.callback_query(F.data=='a:plans')
async def admin_plans(c:CallbackQuery):
    if not await guard(c):return
    rows=await execute('SELECT days,stars FROM plans ORDER BY days',fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text=f'✏️ {d} дней — {s} ⭐',callback_data=f'a:plan:{d}')] for d,s in rows]+[[InlineKeyboardButton(text='◀️ Админка',callback_data='a:home')]]
    await c.answer(); await c.message.edit_text('💎 <b>Тарифы</b>\n\nНажмите на тариф, чтобы изменить цену.',reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode='HTML')

@router.callback_query(F.data.startswith('a:plan:'))
async def plan_select(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    days=int(c.data.split(':')[2]); await state.set_state(A.action); await state.update_data(action='plan',days=days); await c.answer(); await c.message.edit_text(f'💎 Тариф: {days} дней\n\nВведите новую цену в Stars.',reply_markup=back())

@router.callback_query(F.data=='a:promos')
async def promos(c:CallbackQuery):
    if not await guard(c):return
    rows=await execute('SELECT code,days,discount,max_uses,uses FROM promo_codes ORDER BY code',fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text='➕ Создать',callback_data='a:promoadd')]]+[[InlineKeyboardButton(text=f'🗑 {code} — {d}д — {disc}% ({uses}/{lim})',callback_data=f'a:promodel:{code}')] for code,d,disc,lim,uses in rows]+[[InlineKeyboardButton(text='◀️ Админка',callback_data='a:home')]]
    text='🎟 <b>Промокоды</b>\n\n'+('\n'.join(f'• <code>{code}</code> — {d} дней — {disc}% — {uses}/{lim}' for code,d,disc,lim,uses in rows) if rows else 'Промокодов нет.')
    await c.answer(); await c.message.edit_text(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode='HTML')

@router.callback_query(F.data=='a:promoadd')
async def promoadd(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    await state.set_state(A.action); await state.update_data(action='promo_code'); await c.answer(); await c.message.edit_text('🎟 Введите код промокода:',reply_markup=back())

@router.callback_query(F.data.startswith('a:pd:'))
async def promo_discount(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    await state.update_data(discount=int(c.data.split(':')[2]),action='promo_days'); await c.answer(); await c.message.edit_text('⏳ Введите срок промокода в днях:',reply_markup=back())

@router.callback_query(F.data.startswith('a:promodel:'))
async def promodel(c:CallbackQuery):
    if not await guard(c):return
    code=c.data.split(':',2)[2]; await execute('DELETE FROM promo_codes WHERE code=?',(code,)); await c.answer('Промокод удалён.',show_alert=True); await promos(c)

@router.callback_query(F.data=='a:admins')
async def admins(c:CallbackQuery):
    if c.from_user.id!=OWNER_ID: await c.answer('Только главный администратор',show_alert=True); return
    rows=await execute('SELECT user_id FROM admins ORDER BY user_id',fetch=True)
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=[[InlineKeyboardButton(text='➕ Добавить администратора',callback_data='a:addadmin')]]+[[InlineKeyboardButton(text=f'🗑 {uid}',callback_data=f'a:deladmin:{uid}')] for (uid,) in rows]+[[InlineKeyboardButton(text='◀️ Админка',callback_data='a:home')]]
    await c.answer(); await c.message.edit_text('👑 <b>Администраторы</b>\n\nГлавный: <code>%s</code>\n\n%s'%(OWNER_ID,'\n'.join(f'• {r[0]}' for r in rows) or 'Нет дополнительных админов.'),reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode='HTML')

@router.callback_query(F.data=='a:addadmin')
async def addadmin(c:CallbackQuery,state:FSMContext):
    if c.from_user.id!=OWNER_ID:return
    await state.set_state(A.action); await state.update_data(action='addadmin'); await c.answer(); await c.message.edit_text('👑 Отправьте Telegram ID нового администратора.',reply_markup=back())

@router.callback_query(F.data.startswith('a:deladmin:'))
async def deladmin(c:CallbackQuery):
    if c.from_user.id!=OWNER_ID:return
    uid=int(c.data.split(':')[2]); await execute('DELETE FROM admins WHERE user_id=?',(uid,)); await c.answer('Администратор снят.',show_alert=True); await notify_role(c.bot,uid,False); await admins(c)

@router.callback_query(F.data=='a:broadcast')
async def broadcast(c:CallbackQuery,state:FSMContext):
    if not await guard(c):return
    await state.set_state(A.action); await state.update_data(action='broadcast'); await c.answer(); await c.message.edit_text('📢 <b>Рассылка</b>\n\nОтправьте сообщение. Поддерживаются текст, фото, видео, GIF, документы, аудио, голосовые и стикеры.',reply_markup=back(),parse_mode='HTML')

@router.message(A.action)
async def admin_input(m:Message,state:FSMContext):
    if not await is_admin(m.from_user.id):return
    data=await state.get_data(); action=data.get('action')
    if action=='version_version':
        version=(m.text or '').strip()
        if not version or len(version)>30:
            await m.answer('❌ Введите корректный номер версии, например 2.1.0.'); return
        await execute('UPDATE bot_version SET version=? WHERE id=1',(version,))
        await m.answer('✅ Номер версии обновлён.', reply_markup=menu(m.from_user.id==OWNER_ID))
        await state.clear(); return
    if action=='version_description':
        description=m.text or ''
        if len(description)>4000:
            await m.answer('❌ Описание слишком длинное. Максимум 4000 символов.'); return
        await execute('UPDATE bot_version SET description=? WHERE id=1',(description,))
        await m.answer('✅ Описание обновления сохранено.', reply_markup=menu(m.from_user.id==OWNER_ID))
        await state.clear(); return
    if action=='version_image':
        if not m.photo:
            await m.answer('❌ Отправьте фотографию.'); return
        await execute('UPDATE bot_version SET image_file_id=? WHERE id=1',(m.photo[-1].file_id,))
        await m.answer('✅ Изображение обновления сохранено.', reply_markup=menu(m.from_user.id==OWNER_ID))
        await state.clear(); return
    if action=='movie_video':
        if not m.video: await m.answer('❌ Отправьте именно видео.'); return
        movie=data.get('movie',{}); movie['video']=m.video.file_id
        await state.update_data(action='movie_number',movie=movie); await m.answer('2/6 Введите номер фильма.'); return
    if action=='movie_number':
        number=(m.text or '').strip(); movie=data.get('movie',{})
        if not number: await m.answer('❌ Номер не может быть пустым.'); return
        movie['number']=number; await state.update_data(action='movie_title',movie=movie); await m.answer('3/6 Введите название.'); return
    if action=='movie_title':
        movie=data.get('movie',{}); movie['title']=(m.text or '').strip(); await state.update_data(action='movie_desc',movie=movie); await m.answer('4/6 Введите описание.'); return
    if action=='movie_desc':
        movie=data.get('movie',{}); movie['description']=m.text or ''; await state.update_data(action='movie_meta',movie=movie); await m.answer('5/6 Отправьте год и жанр через `;`\nНапример: `2014;Фантастика, драма`'); return
    if action=='movie_meta':
        try: year,genre=[x.strip() for x in (m.text or '').split(';',1)]
        except Exception: await m.answer('❌ Формат: год;жанр'); return
        movie=data.get('movie',{}); movie['year']=year; movie['genre']=genre; await state.update_data(action='movie_poster',movie=movie); await m.answer('6/6 Отправьте постер фотографией.'); return
    if action=='movie_poster':
        if not m.photo: await m.answer('❌ Отправьте постер фотографией.'); return
        movie=data.get('movie',{}); movie['poster']=m.photo[-1].file_id
        await execute('INSERT OR REPLACE INTO movies(number,title,description,year,genre,poster_file_id,video_file_id) VALUES(?,?,?,?,?,?,?)',(movie['number'],movie['title'],movie.get('description',''),movie.get('year',''),movie.get('genre',''),movie['poster'],movie['video']))
        await m.answer('✅ Фильм добавлен.',reply_markup=menu(m.from_user.id==OWNER_ID)); await state.clear(); return
    if action=='movie_edit_number':
        number=(m.text or '').strip(); row=await execute('SELECT number FROM movies WHERE number=?',(number,),one=True)
        if not row: await m.answer('❌ Фильм не найден.'); return
        await state.update_data(action='movie_fields',movie_number=number)
        from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Название',callback_data='a:moviefield:title'),InlineKeyboardButton(text='Описание',callback_data='a:moviefield:description')],[InlineKeyboardButton(text='Год',callback_data='a:moviefield:year'),InlineKeyboardButton(text='Жанр',callback_data='a:moviefield:genre')],[InlineKeyboardButton(text='Постер',callback_data='a:moviefield:poster'),InlineKeyboardButton(text='Видео',callback_data='a:moviefield:video')],[InlineKeyboardButton(text='◀️ Назад',callback_data='a:movies')]])
        await m.answer('✏️ Выберите поле:',reply_markup=kb); return
    if action=='movie_edit_value':
        number=data['movie_number']; field=data['field']; value=None
        if field=='poster':
            if not m.photo: await m.answer('❌ Отправьте фото.'); return
            value=m.photo[-1].file_id
        elif field=='video':
            if not m.video: await m.answer('❌ Отправьте видео.'); return
            value=m.video.file_id
        else: value=m.text or ''
        column={'title':'title','description':'description','year':'year','genre':'genre','poster':'poster_file_id','video':'video_file_id'}[field]
        await execute(f'UPDATE movies SET {column}=? WHERE number=?',(value,number)); await state.clear(); await m.answer('✅ Фильм обновлён.',reply_markup=menu(m.from_user.id==OWNER_ID)); return
    if action=='movie_fields':
        return
    if action=='channel':
        ref=(m.text or '').strip()
        try:
            chat=await m.bot.get_chat(ref)
            await execute('INSERT OR REPLACE INTO channels(chat_id,title,username,invite_url) VALUES(?,?,?,?)',(str(chat.id),chat.title or ref,getattr(chat,'username',None),None))
            await m.answer('✅ Канал добавлен.',reply_markup=menu(m.from_user.id==OWNER_ID)); await state.clear()
        except Exception: await m.answer('❌ Не удалось получить канал. Проверьте @username и права бота.')
        return
    if action=='image':
        if not m.photo: await m.answer('❌ Отправьте фотографию.'); return
        await execute('INSERT INTO images(key,file_id) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET file_id=excluded.file_id',(data['key'],m.photo[-1].file_id))
        await m.answer('✅ Изображение сохранено.',reply_markup=menu(m.from_user.id==OWNER_ID)); await state.clear(); return
    if action=='plan':
        try:
            price=int((m.text or '').strip()); assert price>0
            await execute('UPDATE plans SET stars=? WHERE days=?',(price,data['days']))
            await m.answer('✅ Цена обновлена.',reply_markup=menu(m.from_user.id==OWNER_ID)); await state.clear()
        except Exception: await m.answer('❌ Введите положительное целое число Stars.')
        return
    if action=='addadmin':
        try:
            uid=int((m.text or '').strip()); assert uid!=OWNER_ID
            await execute('INSERT OR IGNORE INTO admins(user_id) VALUES(?)',(uid,))
            await m.answer('✅ Администратор добавлен.',reply_markup=menu(True)); await state.clear(); await notify_role(m.bot,uid,True)
        except Exception: await m.answer('❌ Нужен корректный Telegram ID.')
        return
    if action=='userfind':
        try: uid=int((m.text or '').strip())
        except Exception: await m.answer('❌ Нужен числовой Telegram ID.'); return
        await state.clear(); row=await execute('SELECT id FROM users WHERE id=?',(uid,),one=True)
        if not row: await m.answer('❌ Пользователь не найден.',reply_markup=back()); return
        from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
        await m.answer('✅ Пользователь найден.',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Открыть профиль',callback_data=f'a:user:{uid}')],[InlineKeyboardButton(text='◀️ Назад',callback_data='a:users')]])); return
    if action=='write':
        try: await m.bot.copy_message(data['uid'],m.chat.id,m.message_id); await m.answer('✅ Сообщение отправлено.',reply_markup=menu(m.from_user.id==OWNER_ID))
        except Exception: await m.answer('❌ Не удалось отправить сообщение.',reply_markup=menu(m.from_user.id==OWNER_ID))
        await state.clear(); return
    if action=='broadcast':
        users=await execute('SELECT id FROM users WHERE blocked=0',fetch=True); ok=bad=0
        for (uid,) in users:
            try: await m.bot.copy_message(uid,m.chat.id,m.message_id); ok+=1
            except Exception: bad+=1
        await m.answer(f'📢 <b>Рассылка завершена</b>\n\n✅ Отправлено: {ok}\n❌ Ошибок: {bad}',reply_markup=menu(m.from_user.id==OWNER_ID),parse_mode='HTML'); await state.clear(); return
    if action=='promo_code':
        code=(m.text or '').strip().upper()
        if not code or ';' in code: await m.answer('❌ Некорректный код.'); return
        await state.update_data(code=code,action='promo_discount'); await m.answer('🏷 Выберите скидку:',reply_markup=discounts()); return
    if action=='promo_days':
        try: days=int((m.text or '').strip()); assert days>0
        except Exception: await m.answer('❌ Введите положительное число дней.'); return
        await state.update_data(days=days,action='promo_limit'); await m.answer('🔢 Введите лимит активаций:')
        return
    if action=='promo_limit':
        try: limit=int((m.text or '').strip()); assert limit>0
        except Exception: await m.answer('❌ Введите положительное число.'); return
        await execute('INSERT OR REPLACE INTO promo_codes(code,days,discount,max_uses,uses,enabled) VALUES(?,?,?,?,0,1)',(data['code'],data['days'],data['discount'],limit))
        await m.answer(f'✅ Промокод <code>{data["code"]}</code> создан.\n⏳ {data["days"]} дней\n🏷 Скидка {data["discount"]}%\n🔢 Лимит {limit}',reply_markup=menu(m.from_user.id==OWNER_ID),parse_mode='HTML'); await state.clear(); return
