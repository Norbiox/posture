CREATE TABLE IF NOT EXISTS height_events (
  ts TEXT NOT NULL,
  height_cm REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS height_events_ts ON height_events (ts);

CREATE TABLE IF NOT EXISTS presets (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  height_cm REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS automations (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('schedule', 'timer')),
  enabled INTEGER NOT NULL DEFAULT 1,
  preset_id INTEGER NOT NULL REFERENCES presets (id) ON DELETE RESTRICT,
  time_of_day TEXT,
  stance TEXT,
  minutes INTEGER
);

CREATE TABLE IF NOT EXISTS holidays (
  date TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
