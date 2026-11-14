<script lang="ts">
  import { onMount } from "svelte";
  import {
    api,
    errorText,
    formatDuration,
    live,
    loadPresets,
    presets,
    send,
    socket,
    type Automation,
    type SettingsData,
  } from "./api.svelte";
  import Elevation from "./Elevation.svelte";

  interface Holiday {
    date: string;
  }
  interface DayTotals {
    sitting_s: number;
    standing_s: number;
  }

  let error = $state("");
  let newName = $state("");
  let automations = $state<Automation[]>([]);
  let settings = $state<SettingsData | null>(null);
  let holidays = $state<Holiday[]>([]);
  let today = $state<DayTotals | null>(null);
  let now = $state(new Date());

  const online = $derived(live.connected && socket.open);
  const presetById = (id: number) => presets.find((p) => p.id === id);
  const hhmm = (d: Date) =>
    `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  // ponytail: browser-local date; matches POSTURE_TZ when the browser runs in the same zone.
  const isoDate = (d: Date) =>
    `${String(d.getFullYear())}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  const workToday = $derived.by(() => {
    if (!settings) return false;
    const weekday = (now.getDay() + 6) % 7;
    return settings.workdays.includes(weekday) && !holidays.some((h) => h.date === isoDate(now));
  });

  // ponytail: "Next" is derived client-side from Schedules and Work Hours; add a backend
  // endpoint if Timer due times or retries need to show exact times.
  const upcoming = $derived.by(() => {
    const s = settings;
    if (!s || !workToday) return [];
    const clock = hhmm(now);
    const enabled = automations.filter((a) => a.enabled);
    const schedules = enabled
      .filter((a) => a.kind === "schedule" && a.time_of_day !== null)
      .filter((a) => (a.time_of_day ?? "") > clock && (a.time_of_day ?? "") < s.work_end)
      .sort((a, b) => (a.time_of_day ?? "").localeCompare(b.time_of_day ?? ""))
      .map((a) => ({
        key: `s${String(a.id)}`,
        time: a.time_of_day ?? "",
        what: "Schedule",
        preset: presetById(a.preset_id),
      }));
    const end =
      s.work_end > clock
        ? [{ key: "end", time: s.work_end, what: "Work Hours end", preset: undefined }]
        : [];
    return [...schedules, ...end];
  });

  const timers = $derived(
    workToday ? automations.filter((a) => a.enabled && a.kind === "timer") : [],
  );

  async function run(action: () => Promise<unknown>): Promise<void> {
    error = "";
    try {
      await action();
    } catch (e) {
      error = errorText(e);
    }
  }

  const goTo = (name: string) => run(() => api("POST", "/move", { preset: name }));
  const stop = () => run(() => api("POST", "/stop"));
  const togglePause = () => run(() => api(live.paused ? "DELETE" : "POST", "/pause"));
  const saveCurrent = () =>
    run(async () => {
      const existing = presets.find((p) => p.name === newName);
      const height = live.height_cm;
      if (existing && height !== null) {
        const question = `Do you want to update Preset ${existing.name} from ${existing.height_cm.toFixed(1)} to ${height.toFixed(1)}?`;
        // ponytail: native confirm(); swap for a styled dialog if DESIGN.md asks for one.
        if (!confirm(question)) return;
        // Send the Height shown in the question, not whatever the Desk reads a moment later.
        await api("PUT", `/presets/${String(existing.id)}`, { name: newName, height_cm: height });
      } else {
        await api("POST", "/presets", { name: newName });
      }
      newName = "";
      await loadPresets();
    });

  async function refreshTotals(): Promise<void> {
    today = await api<DayTotals>("GET", "/stats/day").catch(() => today);
  }

  onMount(() => {
    void run(async () => {
      [automations, settings, holidays] = await Promise.all([
        api<Automation[]>("GET", "/automations"),
        api<SettingsData>("GET", "/settings"),
        api<Holiday[]>("GET", "/holidays"),
      ]);
    });
    void refreshTotals();
    const timer = setInterval(() => {
      now = new Date();
      void refreshTotals();
    }, 60_000);
    return () => {
      clearInterval(timer);
    };
  });

  function hold(direction: "up" | "down") {
    return {
      onpointerdown: () => {
        send({ type: "hold", direction });
      },
      onpointerup: release,
      onpointerleave: release,
      onpointercancel: release,
      oncontextmenu: (event: Event) => {
        event.preventDefault();
      },
    };
  }
  function release() {
    send({ type: "release" });
  }
</script>

<div class="grid gap-x-10 gap-y-8 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
  <section aria-label="Desk" class="flex flex-col gap-5">
    <Elevation
      height={live.height_cm}
      threshold={settings?.threshold_cm ?? null}
      {presets}
      moving={live.moving}
      {online}
      onpreset={goTo}
    />

    <div class="grid grid-cols-[1fr_1fr_auto] gap-2 border-t border-ink pt-4">
      {#each [["up", "Up"], ["down", "Down"]] as const as [direction, label] (direction)}
        <button
          class="btn h-14 touch-none text-base active:bg-ink active:text-paper"
          disabled={!online}
          {...hold(direction)}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
            <path
              d={direction === "up" ? "M7 2 L13 11 H1 Z" : "M7 12 L13 3 H1 Z"}
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linejoin="miter"
            />
          </svg>
          <span>Hold<span class="hidden sm:inline">&nbsp;to move</span>&nbsp;{label}</span>
        </button>
      {/each}
      <button
        class="btn h-14 border-pencil px-6 text-base font-semibold {live.moving
          ? 'bg-pencil text-paper hover:bg-pencil'
          : 'text-pencil hover:bg-pencil-wash'}"
        onclick={stop}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
          <rect x="1" y="1" width="10" height="10" fill="currentColor" />
        </svg>
        Stop
      </button>
    </div>

    <form
      class="flex flex-wrap items-end gap-2"
      onsubmit={(event) => {
        event.preventDefault();
        void saveCurrent();
      }}
    >
      <label class="field grow">
        New Preset at current Height
        <input class="input" placeholder="Name, e.g. Standing" required bind:value={newName} />
      </label>
      <button class="btn h-9" disabled={live.height_cm === null}>Save Preset</button>
    </form>

    {#if error}<p class="error" role="alert">{error}</p>{/if}
  </section>

  <aside class="flex flex-col gap-8 lg:border-l lg:border-rule lg:pl-10">
    <section aria-labelledby="next-heading" class="flex flex-col gap-3">
      <div class="flex items-center justify-between gap-3">
        <h2 id="next-heading">Next</h2>
        <button class="btn btn-sm {live.paused ? 'btn-solid' : 'btn-quiet'}" onclick={togglePause}>
          {live.paused ? "Resume Automations" : "Pause for today"}
        </button>
      </div>
      {#if !settings}
        <p class="text-ink-2">Loading…</p>
      {:else if !workToday}
        <p class="border-y border-rule py-3 text-ink-2">No Work Hours today. Automations rest.</p>
      {:else if upcoming.length === 0}
        <p class="border-y border-rule py-3 text-ink-2">Work Hours are over for today.</p>
      {:else}
        <table class="sheet-table {live.paused ? 'text-ink-2' : ''}">
          <thead>
            <tr><th>Time</th><th>Automation</th><th class="text-right">Preset</th></tr>
          </thead>
          <tbody>
            {#each upcoming as row, i (row.key)}
              <tr class={i === 0 && !live.paused && timers.length === 0 ? "font-semibold" : ""}>
                <td class="font-cond text-base whitespace-nowrap">{row.time}</td>
                <td class={live.paused && row.preset ? "line-through" : ""}>{row.what}</td>
                <td class="text-right whitespace-nowrap">
                  {#if row.preset}
                    {row.preset.name}
                    <span class="font-cond text-ink-2">{row.preset.height_cm.toFixed(1)}</span>
                  {:else}
                    <span class="text-ink-2">–</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
        {#each timers as t (t.id)}
          {@const preset = presetById(t.preset_id)}
          <p class="text-sm {live.paused ? 'text-ink-2 line-through' : ''}">
            Timer: after {t.minutes} min {t.stance} → {preset?.name ?? "?"}
            <span class="text-ink-2 tabular-nums">{preset?.height_cm.toFixed(1) ?? ""}</span>
          </p>
        {/each}
        {#if live.paused}
          <p class="text-sm text-ink-2">Paused until tomorrow. The Desk stays where it is.</p>
        {/if}
      {/if}
    </section>

    <section aria-labelledby="today-heading" class="flex flex-col gap-3">
      <h2 id="today-heading">Today</h2>
      {#if today}
        {@const total = Math.max(1, today.sitting_s + today.standing_s)}
        <dl class="grid grid-cols-2 border-t border-ink">
          <div class="border-r border-rule py-3 pr-4">
            <dt class="text-sm text-ink-2">Sitting</dt>
            <dd class="font-cond text-2xl font-semibold tabular-nums">
              {formatDuration(today.sitting_s)}
            </dd>
          </div>
          <div class="py-3 pl-4">
            <dt class="text-sm text-ink-2">Standing</dt>
            <dd class="font-cond text-2xl font-semibold tabular-nums">
              {formatDuration(today.standing_s)}
            </dd>
          </div>
        </dl>
        <div class="flex h-2 border border-ink" aria-hidden="true">
          <div
            class="bg-ink"
            style="width: {(today.standing_s / total) * 100}%"
            title="Standing"
          ></div>
        </div>
        <p class="text-sm text-ink-2">
          Standing {Math.round((today.standing_s / total) * 100)}% of tracked time.
        </p>
      {:else}
        <p class="text-ink-2">No data yet.</p>
      {/if}
    </section>
  </aside>
</div>
