import aiosqlite
from config import DB_PATH

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY,
 username TEXT,
 first_name TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 searches INTEGER NOT NULL DEFAULT 0,
 views INTEGER NOT NULL DEFAULT 0,
 blocked INTEGER NOT NULL DEFAULT 0,
 referrer_id INTEGER,
 referral_paid_count INTEGER NOT NULL DEFAULT 0,
 referral_level INTEGER NOT NULL DEFAULT 0,
 referral_balance REAL NOT NULL DEFAULT 0,
 referral_bonus_claimed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS channels(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 chat_id TEXT UNIQUE NOT NULL,
 title TEXT,
 username TEXT,
 invite_url TEXT
);
CREATE TABLE IF NOT EXISTS images(key TEXT PRIMARY KEY, file_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bot_version(
 id INTEGER PRIMARY KEY CHECK(id=1),
 version TEXT NOT NULL DEFAULT '1.0.0',
 description TEXT NOT NULL DEFAULT '',
 image_file_id TEXT
);
CREATE TABLE IF NOT EXISTS plans(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 days INTEGER UNIQUE NOT NULL,
 stars INTEGER NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS movies(
 number TEXT PRIMARY KEY,
 title TEXT NOT NULL,
 description TEXT DEFAULT '',
 year TEXT DEFAULT '',
 genre TEXT DEFAULT '',
 poster_file_id TEXT,
 video_file_id TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS promo_codes(
 code TEXT PRIMARY KEY,
 days INTEGER NOT NULL,
 discount INTEGER NOT NULL DEFAULT 0,
 max_uses INTEGER NOT NULL,
 uses INTEGER NOT NULL DEFAULT 0,
 enabled INTEGER NOT NULL DEFAULT 1,
 expires_at TEXT
);
CREATE TABLE IF NOT EXISTS promo_used(
 code TEXT NOT NULL,
 user_id INTEGER NOT NULL,
 used_at TEXT DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(code,user_id)
);
CREATE TABLE IF NOT EXISTS subscriptions(user_id INTEGER PRIMARY KEY, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 plan_days INTEGER NOT NULL,
 stars INTEGER NOT NULL,
 original_stars INTEGER,
 charge_id TEXT UNIQUE,
 promo_code TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS referral_rewards(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 referrer_id INTEGER NOT NULL,
 referred_id INTEGER NOT NULL,
 payment_id INTEGER,
 paid_stars INTEGER NOT NULL,
 percent INTEGER NOT NULL,
 reward REAL NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(referrer_id,referred_id,payment_id)
);
'''

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        migrations = [
            ('users','blocked','INTEGER NOT NULL DEFAULT 0'),
            ('users','referrer_id','INTEGER'),
            ('users','referral_paid_count','INTEGER NOT NULL DEFAULT 0'),
            ('users','referral_level','INTEGER NOT NULL DEFAULT 0'),
            ('users','referral_balance','REAL NOT NULL DEFAULT 0'),
            ('users','referral_bonus_claimed','INTEGER NOT NULL DEFAULT 0'),
            ('promo_codes','discount','INTEGER NOT NULL DEFAULT 0'),
            ('promo_codes','expires_at','TEXT'),
            ('payments','promo_code','TEXT'),
            ('payments','original_stars','INTEGER'),
        ]
        for table, col, typ in migrations:
            try:
                await db.execute(f'ALTER TABLE {table} ADD COLUMN {col} {typ}')
            except Exception:
                pass
        for days, stars in ((7,129),(30,349),(90,649)):
            await db.execute('INSERT OR IGNORE INTO plans(days,stars) VALUES(?,?)',(days,stars))
        await db.execute("INSERT OR IGNORE INTO bot_version(id,version,description) VALUES(1,'1.0.0','')")
        await db.commit()

async def execute(sql, params=(), *, fetch=False, one=False):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(sql, params)
        result = None
        if fetch:
            result = await cur.fetchall()
        elif one:
            result = await cur.fetchone()
        await db.commit()
        return result

async def add_user(user, referrer_id=None):
    existing = await execute('SELECT referrer_id FROM users WHERE id=?',(user.id,),one=True)
    if existing is None:
        if referrer_id == user.id:
            referrer_id = None
        await execute(
            'INSERT INTO users(id,username,first_name,referrer_id) VALUES(?,?,?,?)',
            (user.id,user.username or '',user.first_name or '',referrer_id)
        )
    else:
        await execute('UPDATE users SET username=?,first_name=? WHERE id=?',(user.username or '',user.first_name or '',user.id))

async def is_admin(user_id):
    if user_id == __import__('config').OWNER_ID:
        return True
    return bool(await execute('SELECT 1 FROM admins WHERE user_id=?',(user_id,),one=True))

async def is_blocked(user_id):
    row = await execute('SELECT blocked FROM users WHERE id=?',(user_id,),one=True)
    return bool(row and row[0])
