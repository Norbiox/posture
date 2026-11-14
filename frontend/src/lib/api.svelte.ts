export type Stance = "sitting" | "standing";

export interface Live {
  height_cm: number | null;
  stance: Stance | null;
  moving: boolean;
  connected: boolean;
  paused: boolean;
}

export interface Preset {
  id: number;
  name: string;
  height_cm: number;
}

export interface Automation {
  id: number;
  kind: "schedule" | "timer";
  enabled: boolean;
  preset_id: number;
  time_of_day: string | null;
  stance: Stance | null;
  minutes: number | null;
}

export interface SettingsData {
  work_start: string;
  work_end: string;
  workdays: number[];
  threshold_cm: number;
}

export interface LogLine {
  ts: string;
  level: string;
  message: string;
}

type ServerMessage =
  | ({ type: "state" } & Live)
  | ({ type: "height" } & Pick<Live, "height_cm" | "stance" | "moving">)
  | ({ type: "log" } & LogLine);

const MAX_LOG_LINES = 500;

export const live = $state<Live>({
  height_cm: null,
  stance: null,
  moving: false,
  connected: false,
  paused: false,
});
export const presets = $state<Preset[]>([]);
export const logs = $state<LogLine[]>([]);
export const socket = $state({ open: false });

export async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method };
  if (body !== undefined) {
    init.headers = { "content-type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = error?.detail;
    throw new Error(
      typeof detail === "string" ? detail : `Request failed (${String(response.status)})`,
    );
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export async function loadPresets(): Promise<void> {
  presets.splice(0, presets.length, ...(await api<Preset[]>("GET", "/presets")));
}

let ws: WebSocket | undefined;

export function send(
  message: { type: "hold"; direction: "up" | "down" } | { type: "release" },
): void {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

function onMessage(event: MessageEvent<string>): void {
  const message = JSON.parse(event.data) as ServerMessage;
  if (message.type === "log") {
    logs.push({ ts: message.ts, level: message.level, message: message.message });
    if (logs.length > MAX_LOG_LINES) {
      logs.shift();
    }
  } else {
    live.height_cm = message.height_cm;
    live.stance = message.stance;
    live.moving = message.moving;
    if (message.type === "state") {
      live.connected = message.connected;
      live.paused = message.paused;
    }
  }
}

export function connect(): void {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${scheme}://${location.host}/ws`);
  ws.onopen = () => {
    socket.open = true;
  };
  ws.onmessage = onMessage;
  ws.onclose = () => {
    socket.open = false;
    live.connected = false;
    setTimeout(connect, 3000);
  };
}

export async function loadLogs(): Promise<void> {
  const lines = await api<LogLine[]>("GET", "/logs?lines=200");
  logs.splice(0, logs.length, ...lines);
}

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  return `${String(Math.floor(minutes / 60))} h ${String(minutes % 60)} min`;
}
