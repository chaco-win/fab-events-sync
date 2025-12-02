import Database from 'better-sqlite3';

// Default to /data so it works with a named volume, unless overridden by env.
const DB_PATH = process.env.DB_PATH || '/data/bot.db';

export const db = new Database(DB_PATH);

export function migrate() {
  db.exec(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS guild_settings (
      guild_id TEXT PRIMARY KEY,
      channel_id TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS guild_calendar_subscriptions (
      guild_id TEXT NOT NULL,
      calendar_id TEXT NOT NULL,
      PRIMARY KEY (guild_id, calendar_id)
    );

    CREATE TABLE IF NOT EXISTS calendars (
      calendar_id TEXT PRIMARY KEY,
      name TEXT,
      last_seen_at TEXT
    );

    CREATE TABLE IF NOT EXISTS events (
      calendar_id TEXT NOT NULL,
      event_id TEXT NOT NULL,
      title TEXT NOT NULL,
      starts_at TEXT NOT NULL,
      ends_at TEXT,
      url TEXT,
      location TEXT,
      updated_at TEXT,
      content_hash TEXT,
      PRIMARY KEY (calendar_id, event_id)
    );

    CREATE TABLE IF NOT EXISTS notifications_log (
      guild_id TEXT NOT NULL,
      calendar_id TEXT NOT NULL,
      event_id TEXT NOT NULL,
      type TEXT NOT NULL,
      posted_at TEXT DEFAULT (datetime('now')),
      PRIMARY KEY (guild_id, calendar_id, event_id, type)
    );
  `);
}
