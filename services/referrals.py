from db import execute
from services.subscription import add_days

LEVELS = ((25, 3, 15), (10, 2, 10), (1, 1, 5))

def level_for_count(count: int) -> int:
    if count >= 25: return 3
    if count >= 10: return 2
    if count >= 1: return 1
    return 0

def percent_for_level(level: int) -> int:
    return {1: 5, 2: 10, 3: 15}.get(level, 0)

async def apply_referral_reward(payment_id: int, buyer_id: int, paid_stars: int):
    # Referral progression counts only the referred user's FIRST successful payment.
    old_payment = await execute('SELECT 1 FROM payments WHERE user_id=? AND id<>? LIMIT 1', (buyer_id, payment_id), one=True)
    if old_payment:
        return None

    row = await execute('SELECT referrer_id FROM users WHERE id=?', (buyer_id,), one=True)
    if not row or not row[0]:
        return None
    referrer_id = row[0]
    if referrer_id == buyer_id:
        return None
    if not await execute('SELECT 1 FROM users WHERE id=?', (referrer_id,), one=True):
        return None

    await execute('UPDATE users SET referral_paid_count=referral_paid_count+1 WHERE id=?', (referrer_id,))
    row = await execute('SELECT referral_paid_count,referral_bonus_claimed FROM users WHERE id=?', (referrer_id,), one=True)
    count, claimed = row
    level = level_for_count(count)
    pct = percent_for_level(level)
    await execute('UPDATE users SET referral_level=? WHERE id=?', (level, referrer_id))

    reward = paid_stars * pct / 100 if pct else 0
    if pct:
        await execute('UPDATE users SET referral_balance=referral_balance+? WHERE id=?', (reward, referrer_id))
        try:
            await execute(
                'INSERT INTO referral_rewards(referrer_id,referred_id,payment_id,paid_stars,percent,reward) VALUES(?,?,?,?,?,?)',
                (referrer_id,buyer_id,payment_id,paid_stars,pct,reward)
            )
        except Exception:
            pass

    bonus = False
    if count >= 10 and not claimed:
        await add_days(referrer_id, 3)
        await execute('UPDATE users SET referral_bonus_claimed=1 WHERE id=?', (referrer_id,))
        bonus = True
    return referrer_id, pct, reward, bonus, level
