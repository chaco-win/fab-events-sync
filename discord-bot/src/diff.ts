import { db } from './db.js';
import { EventRecord, NotificationType } from './types.js';
import { hashEvent } from './hash.js';

export type DiffResult = {
  calendar_id: string;
  event_id: string;
  type: NotificationType;
  payload: EventRecord;
  previous?: EventRecord;
}[];

export function computeDiff(events: EventRecord[]): DiffResult {
  const results: DiffResult = [];
  const selectPrev = db.prepare(
    'SELECT title, starts_at, ends_at, url, location, content_hash FROM events WHERE calendar_id = ? AND event_id = ?'
  );

  for (const e of events) {
    const prev = selectPrev.get(e.calendar_id, e.event_id) as {
      title: string;
      starts_at: string;
      ends_at?: string | null;
      url?: string | null;
      location?: string | null;
      content_hash: string;
    } | undefined;
    if (!prev) {
      results.push({ calendar_id: e.calendar_id, event_id: e.event_id, type: 'new_event', payload: e });
    } else {
      const nextHash = hashEvent(e);
      if (prev.content_hash !== nextHash) {
        const previous: EventRecord = {
          calendar_id: e.calendar_id,
          event_id: e.event_id,
          title: prev.title,
          starts_at: prev.starts_at,
          ends_at: prev.ends_at ?? null,
          url: prev.url ?? null,
          location: prev.location ?? null,
        };
        results.push({ calendar_id: e.calendar_id, event_id: e.event_id, type: 'event_changed', payload: e, previous });
      }
    }
  }

  return results;
}
