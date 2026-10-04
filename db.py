import aiosqlite
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY,
 username TEXT,
 first_name TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 searches INTEGER NOT NULL DEFAULT 0,
 views INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS channels(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 chat_id TEXT UNIQUE NOT NULL,
 title TEXT,
 username TEXT,
 invite_url TEXT
);
CREATE TABLE IF NOT EXISTS images(
 key TEXT PRIMARY KEY,
 file_id TEXT NOT NULL
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
 max_uses INTEGER NOT NULL,
 uses INTEGER NOT NULL DEFAULT 0,
 enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS promo_used(
 code TEXT NOT NULL,
 user_id INTEGER NOT NULL,
 used_at TEXT DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(code,user_id)
);
CREATE TABLE IF NOT EXISTS subscriptions(
 user_id INTEGER PRIMARY KEY,
 expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 plan_days INTEGER NOT NULL,
 stars INTEGER NOT NULL,
 charge_id TEXT UNIQUE,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        for days, stars in ((7,129),(30,349),(90,649)):
            await db.execute(
                "INSERT OR IGNORE INTO plans(days,stars) VALUES(?,?)",
                (days, stars)
            )
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

async def add_user(user):
    await execute(
        """INSERT INTO users(id,username,first_name) VALUES(?,?,?)
           ON CONFLICT(id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name""",
        (user.id, user.username or "", user.first_name or "")
    )

async def is_admin(user_id):
    if user_id == __import__("config").OWNER_ID:
        return True
    return bool(await execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,), one=True))
