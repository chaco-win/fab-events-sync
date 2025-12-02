import './env.js';
import cron from 'node-cron';
import { migrate } from './db.js';
import { loadEventsFromJson, upsertCalendarsFromEvents, upsertEvents } from './ingest.js';
import { computeDiff } from './diff.js';
import { sendNotifications } from './notify.js';

migrate();

// Default to directory so multiple calendar files are discovered (matches README/.env.example).
const DATA_JSON_PATH = process.env.DATA_JSON_PATH || '/app/data';
const CRON = process.env.SCHEDULE_CRON || '0 9 * * 3'; // Wed 09:00
const TZ = process.env.TZ || 'America/Chicago';

async function runOnce() {
  try {
    const events = loadEventsFromJson(DATA_JSON_PATH);
    upsertCalendarsFromEvents(events);
    const diffs = computeDiff(events);
    upsertEvents(events); // persist latest
    await sendNotifications(diffs);
    console.log(`Worker run complete: events=${events.length}, diffs=${diffs.length}`);
  } catch (err) {
    console.error('Worker run failed', err);
  }
}

if (process.env.RUN_ONCE === '1') {
  runOnce();
} else {
  console.log(`Scheduling worker with cron '${CRON}' TZ '${TZ}'`);
  cron.schedule(CRON, runOnce, { timezone: TZ });
}
