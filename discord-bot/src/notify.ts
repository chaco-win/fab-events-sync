import { REST } from '@discordjs/rest';
import { Routes } from 'discord-api-types/v10';
import { DiffResult } from './diff.js';
import { EventRecord } from './types.js';

const TOKEN = process.env.DISCORD_TOKEN || '';
const CHANNEL_ID = process.env.DISCORD_CHANNEL_ID || '';
const SITE_URL = process.env.SITE_URL || 'https://fabevents.chaco.dev';
const TZ = process.env.TZ || 'America/Chicago';
const rest = TOKEN ? new REST({ version: '10' }).setToken(TOKEN) : null;

function formatWhen(value: string) {
  return new Date(value).toLocaleString('en-US', { timeZone: TZ });
}

function formatEventLine(e: { title: string; starts_at: string; url?: string | null; calendarName?: string | null }) {
  const when = formatWhen(e.starts_at);
  const link = e.url ? ` - ${e.url}` : '';
  const cal = e.calendarName ? ` [${e.calendarName}]` : '';
  return `- ${e.title}${cal} @ ${when}${link}`;
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
  if (!CHANNEL_ID) {
    console.warn('DISCORD_CHANNEL_ID not set; skipping notifications');
    return;
  }

  const lines: string[] = [];
  for (const d of diffs) {
    if (d.type === 'new_event') {
      lines.push(formatEventLine({
        title: d.payload.title,
        starts_at: d.payload.starts_at,
        url: d.payload.url ?? undefined,
        calendarName: d.payload.calendar_name ?? null
      }));
      continue;
    }
    if (d.type === 'event_changed' && d.previous) {
      const changeText = formatChange(d.previous, d.payload);
      const cal = d.payload.calendar_name ? ` [${d.payload.calendar_name}]` : '';
      lines.push(`- UPDATE: ${d.payload.title}${cal} @ ${formatWhen(d.payload.starts_at)}\n  -> ${changeText}`);
    }
  }

  if (lines.length === 0) return;
  const header = 'Updates from FAB Events:';
  const footer = `\n\nBrowse and subscribe: ${SITE_URL}`;
  const content = [header, ...lines].join('\n') + footer;
  try {
    await rest.post(Routes.channelMessages(CHANNEL_ID), { body: { content } });
  } catch (err) {
    console.error('Failed to send message', { channel_id: CHANNEL_ID, err });
  }
}
