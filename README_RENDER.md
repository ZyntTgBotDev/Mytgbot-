# ZYNT FILMS — Render deployment

This version is prepared for Render Background Worker + Persistent Disk.

## Why Background Worker
The bot uses Telegram long polling (`start_polling()`), so it does not need an HTTP URL.
Render Background Workers are intended for continuously running processes.

## Important
The persistent disk is used for `zynt_films.db`.
Without persistent storage, Render's default filesystem is ephemeral and local DB changes can disappear after a restart/deploy.

## Deploy from GitHub
1. Create a GitHub repository.
2. Upload all files from this folder to the repository.
3. In Render: New -> Blueprint.
4. Select the repository.
5. Render will read `render.yaml`.
6. Enter `BOT_TOKEN` when Render asks for the secret.
7. Deploy.

The owner is already:
OWNER_ID=1784758404

## Manual Render settings
If you do not use Blueprint:
- Service type: Background Worker
- Runtime: Python
- Build: `pip install -r requirements.txt`
- Start: `python bot.py`
- Environment:
  - `BOT_TOKEN` = your NEW bot token
  - `OWNER_ID` = `1784758404`
  - `DATA_DIR` = `/var/data`
- Persistent Disk:
  - Mount path `/var/data`
  - Size 10 GB

## Token
Do NOT commit `.env` to GitHub.
The token previously exposed in chat should be revoked and replaced through @BotFather.
Put the new token only in Render Environment Variables.

## Telegram Stars
Digital goods/subscriptions are charged in Telegram Stars (`XTR`).
The bot validates the selected plan during pre-checkout and grants access only after `successful_payment`.

## Channel subscription checks
The bot must be able to inspect membership in required channels. Add the bot as an administrator of required channels before enabling them.

## GitHub auto deploy
With autoDeploy enabled, pushes to the connected branch trigger a new deployment.
