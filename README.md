# Shizuka — Telegram Media Collection Bot

Production-oriented asynchronous Pyrofork/MongoDB bot for gated media collections, token economy, sponsor rewards, referrals, check-ins, cleanup, and an administrator control surface. It stores Telegram `file_id`s only; no media is persisted locally.

## Features

- Inline menu, categories, chronological collection browsing, safe view de-duplication, save vault, permanent unlock vault, token ledger, and ordered albums split into Telegram-safe groups of ten.
- Atomic balance debit for purchases, unique unlock/save/referral records, configurable UTC daily browsing limit, daily streak rewards, and referral crediting.
- Provider-neutral shortener records, per-user/provider cooldowns, expiry, minimum verification timing, tolerance, suspicious-activity audit records, and administrator-only recovery from restriction.
- MongoDB indexes, asynchronous Motor/aiohttp/Pyrofork operations, rate-limited media delivery, cleanup worker, maintenance mode, and error-safe callbacks.
- `/admin` access is restricted by `ADMIN_IDS`; dashboard exposes collection/category/shortener/economy/user/reward/settings/system/statistics/broadcast areas. Privileged commands are logged through the token ledger.

## Required environment

Copy `.env.example` to `.env` and set. Create the required Telegram application credentials at https://my.telegram.org/apps:

| Variable | Purpose |
|---|---|
| `BOT_TOKEN` | Token from BotFather |
| `API_ID` / `API_HASH` | Telegram application credentials from https://my.telegram.org/apps; required by Pyrofork even for bot authorization |
| `MONGO_URI` | MongoDB Atlas/self-hosted URI |
| `DATABASE_NAME` | Mongo database name |
| `ADMIN_IDS` | Comma-separated Telegram numeric IDs |
| `BOT_USERNAME` | Bot username without `@` |
| `STORAGE_CHANNEL_ID` | Private permanent media channel ID; bot must be an admin with post permission |
| `DEFAULT_*`, `CLEANUP_*`, `SHORTENER_TIMEOUT` | Bootstrap defaults; runtime settings live in MongoDB |

Never commit `.env` or API keys. Shortener API keys are stored in MongoDB and only passed server-side to their configured API.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit every required value
python -m bot.main
```

The bot verifies MongoDB at startup and creates its indexes once. It runs as long polling with Pyrofork, appropriate for low-cost worker hosting. It also binds `0.0.0.0:$PORT` (default `8080`) with `/` and `/healthz` so Koyeb health checks do not terminate the worker.

## First-time administrator workflow

1. Add your numeric ID to `ADMIN_IDS`, restart, then open `/admin`.
2. Create a category with `/newcategory Name | Optional description`.
3. Add the bot as an administrator with permission to post in the private storage channel, set `STORAGE_CHANNEL_ID`, then use **Storage Status/Test** in `/admin` to verify it. Start an upload with `/newcollection Title | category_id | price | optional description`; every cover and uploaded media message is copied into the storage channel before the collection is published.
4. Open **Shorteners** and configure records with `name`, `api_url`, `api_key`, `domain`, `enabled`, `reward_tokens`, `cooldown_hours`, `alias_enabled`, and `alias_prefix`. Keys are masked in UI. For Arolinks, use the API endpoint `https://arolinks.com/api` (not the member/developer documentation page).
5. Adjust economy values via `/set daily_free_limit 10`, `/set referral_reward 5`, `/set checkin_base_reward 2`, `/set checkin_streak_bonus 1`, `/set cleanup_enabled true`, `/set cleanup_after_minutes 10`, or `/set maintenance_mode true`.

Admins can temporarily test optional Pyrofork button styling with `/buttonstyles`; this does not alter any production keyboard.

Admin user tools: `/ban ID reason`, `/unban ID`, `/tokens ID +/-amount`. Each balance adjustment receives an immutable transaction log. Reply to broadcast media/text with `/broadcast` in an extended deployment handler.

## Deploy Render

Push this repository, create a **Background Worker**, select Docker, and configure all variables from `.env.example` in Render’s Environment page. `render.yaml` defines the worker command. Do not use a web service: the bot is a long-running polling worker.

## Deploy Koyeb

Create an App from the Git repository, select Docker build, use `python -m bot.main` as the worker command, configure the same environment variables as secrets, and set the instance to always on. No volume is needed.

## Operations and troubleshooting

- Ensure BotFather privacy settings permit the intended admin uploads; the bot only accepts private-chat interactions.
- MongoDB network access must allow the host. DNS failures generally indicate an incomplete Atlas connection string or IP allow list.
- Shortener responses must be JSON with one of `shortenedUrl`, `shortened_url`, or `url`; provider credentials are not hardcoded.
- Media is copied permanently into the configured private Storage Channel on upload and delivered from its stored messages in the original order. Deleted/invalid storage messages are skipped without crashing the worker.
- The cleanup worker only deletes delivered collection messages, never navigation/menu messages.
