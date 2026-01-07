import fs from 'node:fs';
import path from 'node:path';
import { db } from './db.js';
import { EventRecord } from './types.js';
import { hashEvent } from './hash.js';

function humanizeFromFilename(base: string): string | null {
  const stem = base.replace(/\.json$/i, '');
  const s = stem.toLowerCase();
  if (s.includes('global')) return 'Global Events';
  if (s.includes('dfw')) return 'DFW Events';
  // Convert underscores/hyphens to spaces and title case
  const words = stem.replace(/[_-]+/g, ' ').trim().split(/\s+/);
  if (words.length === 0) return null;
  const titled = words.map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  return titled || null;
}

export function loadEventsFromJson(jsonPath: string): EventRecord[] {
  const p = path.resolve(jsonPath);
  const stats = fs.statSync(p);
  const results: EventRecord[] = [];
  const loadFile = (file: string) => {
    const raw = fs.readFileSync(file, 'utf8');
    if (!raw.trim()) return;
    const data = JSON.parse(raw);
    if (Array.isArray(data)) {
      const base = path.basename(file).toLowerCase();
      const isGlobal = base.includes('global');
      const label = humanizeFromFilename(path.basename(file));
      for (const rec of data) {
        const r = rec as EventRecord;
        r.is_global = isGlobal;
        if (label) r.calendar_name = label;
        results.push(r);
      }
    }
  };
  if (stats.isDirectory()) {
    const files = fs.readdirSync(p).filter(f => f.toLowerCase().endsWith('.json'));
    for (const f of files) loadFile(path.join(p, f));
  } else {
    loadFile(p);
  }
  return results;
}

export function upsertCalendarsFromEvents(events: EventRecord[]) {
  const stmt = db.prepare(
    `INSERT INTO calendars (calendar_id, name, last_seen_at)
     VALUES (@calendar_id, @name, datetime('now'))
     ON CONFLICT(calendar_id) DO UPDATE SET
       last_seen_at = excluded.last_seen_at,
       name = COALESCE(calendars.name, excluded.name)`
  );
  const names = new Map<string, string | null>();
  for (const e of events) {
    if (!names.has(e.calendar_id)) names.set(e.calendar_id, e.calendar_name ?? null);
  }
  db.transaction(() => {
    for (const [calendar_id, name] of names.entries()) {
      stmt.run({ calendar_id, name });
    }
  })();
}

export function upsertEvents(events: EventRecord[]) {
  const stmt = db.prepare(
    `INSERT INTO events (calendar_id, event_id, title, starts_at, ends_at, url, location, updated_at, content_hash)
     VALUES (@calendar_id, @event_id, @title, @starts_at, @ends_at, @url, @location, @updated_at, @content_hash)
     ON CONFLICT(calendar_id, event_id) DO UPDATE SET
       title=excluded.title,
       starts_at=excluded.starts_at,
       ends_at=excluded.ends_at,
       url=excluded.url,
       location=excluded.location,
       updated_at=excluded.updated_at,
       content_hash=excluded.content_hash`
  );

  db.transaction(() => {
    for (const e of events) {
      const content_hash = hashEvent(e);
      stmt.run({ ...e, ends_at: e.ends_at ?? null, url: e.url ?? null, location: e.location ?? null, updated_at: e.updated_at ?? null, content_hash });
    }
  })();
}
