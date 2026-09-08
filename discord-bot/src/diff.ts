import { db } from './db.js';
import { EventRecord, NotificationType } from './types.js';
import { hashEvent } from './hash.js';

const TZ = process.env.TZ || 'America/Chicago';

// starts_at is written by the scrapers as local wall-clock time with a
// trailing 'Z' (not a real UTC instant), so read the date digits directly
// instead of running it through a timezone conversion, which would
// re-shift an already-local time by the UTC offset.
function eventDateStr(startsAt: string): string {
  return startsAt.slice(0, 10);
}

function todayLocalDateStr(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: TZ });
}

function isPastEvent(startsAt: string): boolean {
  return eventDateStr(startsAt) < todayLocalDateStr();
}

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
    if (isPastEvent(e.starts_at)) continue; // don't notify about events that already happened

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

        // Check if only the URL changed
        const otherFieldsMatch =
          prev.title === e.title &&
          prev.starts_at === e.starts_at &&
          (prev.ends_at ?? null) === (e.ends_at ?? null) &&
          (prev.location ?? null) === (e.location ?? null);

        if (otherFieldsMatch) {
          // Only URL changed
          if (!prev.url && e.url) {
            // Link was added
            results.push({ calendar_id: e.calendar_id, event_id: e.event_id, type: 'link_added', payload: e, previous });
          } else if (prev.url && e.url && prev.url !== e.url) {
            // Link was changed
            results.push({ calendar_id: e.calendar_id, event_id: e.event_id, type: 'link_changed', payload: e, previous });
          } else {
            // Other changes
            results.push({ calendar_id: e.calendar_id, event_id: e.event_id, type: 'event_changed', payload: e, previous });
          }
        } else {
          // Multiple fields changed
          results.push({ calendar_id: e.calendar_id, event_id: e.event_id, type: 'event_changed', payload: e, previous });
        }
      }
    }
  }

  return results;
}
