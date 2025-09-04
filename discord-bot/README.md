# FAB Events Discord Bot

This bot posts notifications about new events and when global events gain webpages.

- Command service: handles slash commands (`/notify ...`).
- Worker service: runs weekly, reads `../data/events.json`, diffs against DB, and posts to subscribed channels.

## Links
- Live site: https://fabevents.chaco.dev

Quick start
- Copy `.env.example` to `.env` and fill values.
- Put your events JSON at repo root: `data/events.json`.
- From repo root: `docker compose -f discord-bot/docker-compose.yml up -d --build`.

Environment
- `DISCORD_TOKEN`: Bot token.
- `APP_ID`: Discord application ID.
- `GUILD_ID`: Optional. If set (or `GUILD_IDS` comma-separated), commands register per-guild for instant availability.
- `DATA_JSON_PATH`: Path in container to events JSON directory or file (default `/app/data`).
- `SCHEDULE_CRON`: Default `0 9 * * 3` (Wednesday 09:00). TZ via `TZ` (default `America/Chicago`).

Data
- Place JSON files in repo root `data/` (e.g., `global_events.json`, `dfw_events.json`).
- Calendars are auto-discovered from the JSON and stored in SQLite.
- Any file with "global" in its name is treated as the Global calendar for special "webpage added" notifications.

Instant commands while testing
- Add `GUILD_ID=<your_test_guild_id>` in `discord-bot/.env` or `.env.local`.
- Rebuild/restart `bot-cmd` to register per‑guild commands immediately.

DB
- SQLite at `discord-bot/var/bot.db`.
