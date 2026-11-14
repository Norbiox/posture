<script lang="ts">
  import uPlot from "uplot";
  import "uplot/dist/uPlot.min.css";
  import { onMount } from "svelte";
  import { SvelteDate } from "svelte/reactivity";
  import { api, errorText, formatDuration as format } from "./api.svelte";

  interface DayStats {
    date: string;
    heights: (number | null)[];
    threshold_cm: number;
    sitting_s: number;
    standing_s: number;
  }
  interface DayTotals {
    date: string;
    sitting_s: number;
    standing_s: number;
  }

  let day = $state<DayStats | null>(null);
  let daily = $state<DayTotals[]>([]);
  let range = $state<[number, number] | null>(null);
  let span = $state(7);
  let error = $state("");
  let container: HTMLDivElement | undefined;
  let chart: uPlot | undefined;

  const MINUTES_PER_DAY = 1440;
  const stepped = uPlot.paths.stepped;

  // Same rule as the backend: a Height at the threshold counts as Standing.
  const totals = $derived.by(() => {
    if (!day) return { sitting: 0, standing: 0 };
    if (!range) return { sitting: day.sitting_s, standing: day.standing_s };
    let sitting = 0;
    let standing = 0;
    for (const height of day.heights.slice(range[0], range[1])) {
      if (height === null) continue;
      if (height >= day.threshold_cm) standing += 60;
      else sitting += 60;
    }
    return { sitting, standing };
  });

  const maxDaily = $derived(Math.max(1, ...daily.map((d) => d.sitting_s + d.standing_s)));

  async function loadDay(date?: string): Promise<void> {
    try {
      error = "";
      range = null;
      day = await api<DayStats>("GET", date ? `/stats/day?date=${date}` : "/stats/day");
    } catch (e) {
      error = errorText(e);
    }
  }

  async function loadDaily(): Promise<void> {
    try {
      daily = await api<DayTotals[]>("GET", `/stats/daily?days=${String(span)}`);
    } catch (e) {
      error = errorText(e);
    }
  }

  function shift(days: number): void {
    if (!day) return;
    const next = new SvelteDate(`${day.date}T00:00:00Z`);
    next.setUTCDate(next.getUTCDate() + days);
    void loadDay(next.toISOString().slice(0, 10));
  }

  function clock(hours: number): string {
    return `${String(Math.floor(hours)).padStart(2, "0")}:${hours % 1 === 0 ? "00" : "30"}`;
  }

  const token = (name: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim();
  const CHART_HEIGHT = 340;

  function draw(data: DayStats): void {
    if (!container) return;
    chart?.destroy();
    const ink = token("ink");
    const ink2 = token("ink-2");
    const rule = token("rule");
    const font = '12px "Barlow", sans-serif';
    const axis = { stroke: ink2, font, grid: { stroke: rule, width: 1 }, ticks: { stroke: rule } };
    const hours = data.heights.map((_, i) => i / 60);
    const ticks = Array.from({ length: 25 }, (_, i) => i);
    chart = new uPlot(
      {
        width: container.clientWidth,
        height: CHART_HEIGHT,
        legend: { show: false },
        cursor: { drag: { x: true, y: false, setScale: false } },
        scales: { x: { time: false, range: [0, 24] }, y: { range: [60, 130] } },
        axes: [
          {
            ...axis,
            splits: () => ticks,
            values: (u, splits) => {
              const step = u.width < 700 ? 6 : 2;
              return splits.map((h) => (h % step === 0 ? clock(h) : ""));
            },
          },
          { ...axis, label: "cm", labelFont: font, size: 44 },
        ],
        series: [
          {},
          { stroke: ink, width: 1.5, ...(stepped ? { paths: stepped({ align: 1 }) } : {}) },
          { stroke: ink2, width: 1, dash: [14, 4, 2, 4], points: { show: false } },
        ],
        hooks: {
          setSelect: [
            (u) => {
              if (u.select.width < 2) {
                range = null;
                return;
              }
              const from = Math.max(0, Math.floor(u.posToVal(u.select.left, "x") * 60));
              const to = Math.min(
                MINUTES_PER_DAY,
                Math.ceil(u.posToVal(u.select.left + u.select.width, "x") * 60),
              );
              range = [from, to];
            },
          ],
        },
      },
      [hours, data.heights, data.heights.map(() => data.threshold_cm)],
      container,
    );
  }

  function resetRange(): void {
    chart?.setSelect({ left: 0, top: 0, width: 0, height: 0 }, false);
    range = null;
  }

  $effect(() => {
    if (day) draw(day);
  });

  $effect(() => {
    void loadDaily();
  });

  onMount(() => {
    void loadDay();
    const onResize = () => {
      if (container) chart?.setSize({ width: container.clientWidth, height: CHART_HEIGHT });
    };
    const scheme = matchMedia("(prefers-color-scheme: dark)");
    const onScheme = () => {
      if (day) draw(day);
    };
    window.addEventListener("resize", onResize);
    scheme.addEventListener("change", onScheme);
    return () => {
      window.removeEventListener("resize", onResize);
      scheme.removeEventListener("change", onScheme);
      chart?.destroy();
    };
  });
</script>

<section class="flex flex-col gap-10">
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
      <button
        class="btn btn-sm btn-quiet w-9 px-0"
        onclick={() => {
          shift(-1);
        }}
        aria-label="Previous day"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"
          ><path d="M8 1 L3 6 L8 11" fill="none" stroke="currentColor" stroke-width="1.5" /></svg
        >
      </button>
      <span class="font-cond min-w-28 text-center text-xl font-semibold tabular-nums"
        >{day?.date ?? ""}</span
      >
      <button
        class="btn btn-sm btn-quiet w-9 px-0"
        onclick={() => {
          shift(1);
        }}
        aria-label="Next day"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"
          ><path d="M4 1 L9 6 L4 11" fill="none" stroke="currentColor" stroke-width="1.5" /></svg
        >
      </button>
      <button class="btn btn-sm btn-quiet" onclick={() => loadDay()}>Today</button>
      {#if range}
        <button class="btn btn-sm" onclick={resetRange}>Whole day</button>
      {/if}
      <dl class="ml-auto flex gap-6">
        <div>
          <dt class="text-sm text-ink-2">Sitting</dt>
          <dd class="font-cond text-xl font-semibold tabular-nums">{format(totals.sitting)}</dd>
        </div>
        <div>
          <dt class="text-sm text-ink-2">Standing</dt>
          <dd class="font-cond text-xl font-semibold tabular-nums">{format(totals.standing)}</dd>
        </div>
      </dl>
    </div>
    <div bind:this={container} class="w-full border-y border-ink py-3"></div>
    <p class="text-sm text-ink-2">
      {#if range}
        Selected {clock(range[0] / 60)}–{clock(range[1] / 60)}.
      {:else}
        Drag across the chart to total a time range.
      {/if}
      Chain line: Stance threshold.
    </p>
  </div>

  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-4">
      <h2>Daily totals</h2>
      <select class="input min-h-8 py-0 text-sm" bind:value={span} aria-label="Range">
        <option value={7}>7 days</option>
        <option value={30}>30 days</option>
      </select>
      <span class="flex items-center gap-3 text-sm text-ink-2">
        <span class="flex items-center gap-1.5"
          ><i class="inline-block size-3 border border-ink"></i> Sitting</span
        >
        <span class="flex items-center gap-1.5"
          ><i class="inline-block size-3 bg-ink"></i> Standing</span
        >
      </span>
    </div>
    <div class="flex h-36 items-end gap-1 border-b border-ink">
      {#each daily as d (d.date)}
        <div
          class="flex h-full min-w-0 flex-1 flex-col justify-end"
          title="{d.date}: sitting {format(d.sitting_s)}, standing {format(d.standing_s)}"
        >
          <div class="bg-ink" style="height: {(d.standing_s / maxDaily) * 100}%"></div>
          <div
            class="border-x border-t border-ink bg-paper-2"
            style="height: {(d.sitting_s / maxDaily) * 100}%"
          ></div>
        </div>
      {/each}
    </div>
    <div class="flex gap-1">
      {#each daily as d (d.date)}
        <span class="min-w-0 flex-1 truncate text-center text-[11px] text-ink-2 tabular-nums"
          >{d.date.slice(5)}</span
        >
      {/each}
    </div>
  </div>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</section>
