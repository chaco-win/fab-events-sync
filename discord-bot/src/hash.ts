import crypto from 'node:crypto';
import { EventRecord } from './types.js';

export function hashEvent(e: EventRecord): string {
  const canonical = JSON.stringify({
    title: e.title,
    starts_at: e.starts_at,
    ends_at: e.ends_at ?? null,
    url: e.url ?? null,
    location: e.location ?? null,
  });
  return crypto.createHash('sha256').update(canonical).digest('hex');
}
