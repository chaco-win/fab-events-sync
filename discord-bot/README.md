# FAB Events Discord Bot

This bot posts notifications about new events and event changes for both local and global calendars.

- Worker service: runs on a schedule, reads `../data/*.json`, diffs against DB, and posts to a single channel.

## Links
- Live site: https://fabevents.chaco.dev

Quick start
- Copy `.env.example` to `.env` and fill values.
- Put your events JSON at repo root: `data/events.json`.
- From repo root: `docker compose -f discord-bot/docker-compose.yml up -d --build`.

Environment
- `DISCORD_TOKEN`: Bot token.
- `DISCORD_CHANNEL_ID`: Single channel ID to post notifications into.
- `DISCORD_CHANNEL_IDS`: Comma-separated list of channel IDs (overrides `DISCORD_CHANNEL_ID` when set).
- `DATA_JSON_PATH`: Path in container to events JSON directory or file (default `/app/data`).
- `SCHEDULE_CRON`: Default `0 9 * * 3` (Wednesday 09:00). TZ via `TZ` (default `America/Chicago`).

Data
- Place JSON files in repo root `data/` (e.g., `global_events.json`, `dfw_events.json`).
- Calendars are auto-discovered from the JSON and stored in SQLite for change detection.

DB
- SQLite at `discord-bot/var/bot.db`.
