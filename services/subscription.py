from datetime import datetime, timedelta, timezone
from db import execute

def now():
    return datetime.now(timezone.utc)

async def expiry(user_id):
    row = await execute('SELECT expires_at FROM subscriptions WHERE user_id=?',(user_id,),one=True)
    if not row:
        return None
    try:
        dt = datetime.fromisoformat(row[0])
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

async def active(user_id):
    exp = await expiry(user_id)
    return bool(exp and exp > now())

async def add_days(user_id, days):
    current = await expiry(user_id)
    base = current if current and current > now() else now()
    exp = base + timedelta(days=days)
    await execute('INSERT INTO subscriptions(user_id,expires_at) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET expires_at=excluded.expires_at',(user_id,exp.isoformat()))
    return exp

async def remove(user_id):
    await execute('DELETE FROM subscriptions WHERE user_id=?',(user_id,))
