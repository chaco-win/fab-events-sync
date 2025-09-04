import { db } from './db.js';
import { EventRecord, NotificationType } from './types.js';

export type DiffResult = {
  calendar_id: string;
  event_id: string;
  type: NotificationType;
  payload: EventRecord;
}[];

export function computeDiff(events: EventRecord[]): DiffResult {
  const results: DiffResult = [];
  const selectPrev = db.prepare('SELECT url FROM events WHERE calendar_id = ? AND event_id = ?');

  for (const e of events) {
    const prev = selectPrev.get(e.calendar_id, e.event_id) as { url?: string } | undefined;
    if (!prev) {
      results.push({ calendar_id: e.calendar_id, event_id: e.event_id, type: 'new_event', payload: e });
    } else if (e.is_global) {
      const prevUrl = prev.url ?? '';
      const newUrl = e.url ?? '';
      if (!prevUrl && newUrl) {
        results.push({ calendar_id: e.calendar_id, event_id: e.event_id, type: 'url_added', payload: e });
      }
    }
  }

  return results;
}
