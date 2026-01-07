export type EventRecord = {
  event_id: string;
  calendar_id: string;
  title: string;
  starts_at: string; // ISO
  ends_at?: string | null; // ISO
  url?: string | null;
  updated_at?: string | null; // ISO
  location?: string | null;
  is_global?: boolean; // derived from source file (e.g., global_events.json)
  calendar_name?: string; // friendly name derived from source
};

export type GuildSettings = {
  guild_id: string;
  channel_id: string | null;
};

export type NotificationType = 'new_event' | 'event_changed';
