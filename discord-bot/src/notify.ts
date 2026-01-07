import { REST } from '@discordjs/rest';
import { Routes } from 'discord-api-types/v10';
import { db } from './db.js';
import { DiffResult } from './diff.js';
import { EventRecord } from './types.js';

const TOKEN = process.env.DISCORD_TOKEN || '';
const CHANNEL_IDS = (process.env.DISCORD_CHANNEL_IDS || process.env.DISCORD_CHANNEL_ID || '')
  .split(',')
  .map(id => id.trim())
  .filter(Boolean);
const SITE_URL = process.env.SITE_URL || 'https://fabevents.chaco.dev';
const TZ = process.env.TZ || 'America/Chicago';
const rest = TOKEN ? new REST({ version: '10' }).setToken(TOKEN) : null;

function formatWhen(value: string) {
  return new Date(value).toLocaleString('en-US', { timeZone: TZ });
}

function formatEventTitle(e: { title: string; url?: string | null }) {
  return e.url ? `[${e.title}](${e.url})` : e.title;
}

function formatEventLine(e: { title: string; starts_at: string; url?: string | null; is_global?: boolean }) {
  const title = formatEventTitle(e);
  if (e.is_global) {
    return `- ${title}`;
  }
  const when = formatWhen(e.starts_at);
  return `- ${title} @ ${when}`;
}

function formatChange(prev: EventRecord, next: EventRecord) {
  const changes: string[] = [];
  if (prev.starts_at !== next.starts_at) {
    changes.push(`date/time: ${formatWhen(prev.starts_at)} -> ${formatWhen(next.starts_at)}`);
  }
  if ((prev.ends_at ?? '') !== (next.ends_at ?? '')) {
    const prevEnd = prev.ends_at ? formatWhen(prev.ends_at) : 'none';
    const nextEnd = next.ends_at ? formatWhen(next.ends_at) : 'none';
    changes.push(`end: ${prevEnd} -> ${nextEnd}`);
  }
  if ((prev.location ?? '') !== (next.location ?? '')) {
    changes.push(`location: ${prev.location ?? 'none'} -> ${next.location ?? 'none'}`);
  }
  if ((prev.url ?? '') !== (next.url ?? '')) {
    const prevUrl = prev.url ?? 'none';
    const nextUrl = next.url ?? 'none';
    changes.push(`url: ${prevUrl} -> ${nextUrl}`);
  }
  if ((prev.title ?? '') !== (next.title ?? '')) {
    changes.push(`title: ${prev.title} -> ${next.title}`);
  }
  return changes.join(' | ');
}

export async function sendNotifications(diffs: DiffResult) {
  if (!rest) {
    console.warn('DISCORD_TOKEN not set; skipping notifications');
    return;
  }
  const channelIds = CHANNEL_IDS.length
    ? CHANNEL_IDS
    : (db.prepare('SELECT channel_id FROM guild_settings WHERE channel_id IS NOT NULL').all() as { channel_id: string }[])
        .map(row => row.channel_id);

  if (channelIds.length === 0) {
    console.warn('No channel IDs configured; skipping notifications');
    return;
  }

  const lines: string[] = [];
  for (const d of diffs) {
    if (d.type === 'new_event') {
      lines.push(formatEventLine({
        title: d.payload.title,
        starts_at: d.payload.starts_at,
        url: d.payload.url ?? undefined,
        is_global: d.payload.is_global ?? false
      }));
      continue;
    }
    if (d.type === 'event_changed' && d.previous) {
      const changeText = formatChange(d.previous, d.payload);
      const title = formatEventTitle(d.payload);
      if (d.payload.is_global) {
        lines.push(`- UPDATE: ${title}\n  -> ${changeText}`);
      } else {
        lines.push(`- UPDATE: ${title} @ ${formatWhen(d.payload.starts_at)}\n  -> ${changeText}`);
      }
    }
  }

  if (lines.length === 0) return;
  const header = 'Updates from FAB Events:';
  const footer = `\n\nBrowse and subscribe: ${SITE_URL}`;
  const maxLen = 2000;

  const chunks: string[] = [];
  let current = header;
  for (const line of lines) {
    if ((current + '\n' + line).length + footer.length > maxLen) {
      chunks.push(current);
      current = header + '\n' + line;
    } else {
      current += '\n' + line;
    }
  }
  if (current.trim()) chunks.push(current);

  for (const channelId of channelIds) {
    for (const chunk of chunks) {
      const content = chunk + footer;
      try {
        await rest.post(Routes.channelMessages(channelId), { body: { content } });
      } catch (err) {
        console.error('Failed to send message', { channel_id: channelId, err });
      }
    }
  }
}
