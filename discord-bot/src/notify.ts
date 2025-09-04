import { REST } from '@discordjs/rest';
import { Routes } from 'discord-api-types/v10';
import { db } from './db.js';
import { DiffResult } from './diff.js';

const TOKEN = process.env.DISCORD_TOKEN || '';
const rest = TOKEN ? new REST({ version: '10' }).setToken(TOKEN) : null;

function formatEventLine(e: { title: string; starts_at: string; url?: string | null; calendarName?: string | null }) {
  const when = new Date(e.starts_at).toLocaleString('en-US', { timeZone: process.env.TZ || 'America/Chicago' });
  const link = e.url ? ` — ${e.url}` : '';
  const cal = e.calendarName ? ` [${e.calendarName}]` : '';
  return `• ${e.title}${cal} — ${when}${link}`;
}

export async function sendNotifications(diffs: DiffResult) {
  if (!rest) {
    console.warn('DISCORD_TOKEN not set; skipping notifications');
    return;
  }

  const guildRows = db.prepare('SELECT guild_id, channel_id FROM guild_settings WHERE channel_id IS NOT NULL').all() as { guild_id: string; channel_id: string }[];
  const calNameStmt = db.prepare('SELECT name FROM calendars WHERE calendar_id = ?');
  const subCheck = db.prepare('SELECT 1 FROM guild_calendar_subscriptions WHERE guild_id = ? AND calendar_id = ?');
  const logInsert = db.prepare(`INSERT OR IGNORE INTO notifications_log(guild_id, calendar_id, event_id, type) VALUES (?,?,?,?)`);

  for (const { guild_id, channel_id } of guildRows) {
    const lines: string[] = [];
    for (const d of diffs) {
      const subscribed = subCheck.get(guild_id, d.calendar_id);
      if (!subscribed) continue;
      logInsert.run(guild_id, d.calendar_id, d.event_id, d.type);
      const nameRow = calNameStmt.get(d.calendar_id) as { name?: string } | undefined;
      lines.push(formatEventLine({ title: d.payload.title, starts_at: d.payload.starts_at, url: d.payload.url ?? undefined, calendarName: nameRow?.name ?? null }));
    }
    if (lines.length === 0) continue;
    const content = lines.join('\n');
    try {
      await rest.post(Routes.channelMessages(channel_id), { body: { content } });
    } catch (err) {
      console.error('Failed to send message', { guild_id, channel_id, err });
    }
  }
}
