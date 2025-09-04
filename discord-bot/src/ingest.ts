import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { db } from './db.js';
import { EventRecord } from './types.js';

function hashEvent(e: EventRecord): string {
  const canonical = JSON.stringify({
    title: e.title,
    starts_at: e.starts_at,
    ends_at: e.ends_at ?? null,
    url: e.url ?? null,
    location: e.location ?? null,
  });
  return crypto.createHash('sha256').update(canonical).digest('hex');
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
      for (const rec of data) {
        const r = rec as EventRecord;
        r.is_global = isGlobal;
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
     ON CONFLICT(calendar_id) DO UPDATE SET last_seen_at = excluded.last_seen_at`
  );
  const uniq = new Set(events.map(e => e.calendar_id));
  db.transaction(() => {
    for (const calendar_id of uniq) {
      stmt.run({ calendar_id, name: null });
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
