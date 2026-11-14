<script lang="ts">
  import uPlot from "uplot";
  import "uplot/dist/uPlot.min.css";
  import { onMount } from "svelte";
  import { SvelteDate } from "svelte/reactivity";
  import { api, errorText } from "./api.svelte";

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

  function format(seconds: number): string {
    const minutes = Math.round(seconds / 60);
    return `${String(Math.floor(minutes / 60))} h ${String(minutes % 60)} min`;
  }

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

  function draw(data: DayStats): void {
    if (!container) return;
    chart?.destroy();
    const hours = data.heights.map((_, i) => i / 60);
    const ticks = Array.from({ length: 49 }, (_, i) => i / 2);
    chart = new uPlot(
      {
        width: container.clientWidth,
        height: 300,
        legend: { show: false },
        cursor: { drag: { x: true, y: false, setScale: false } },
        scales: { x: { time: false, range: [0, 24] }, y: { range: [60, 130] } },
        axes: [
          {
            splits: () => ticks,
            values: (_u, splits) => splits.map((h) => (h % 1 === 0 ? clock(h) : "")),
          },
          { label: "cm" },
        ],
        series: [
          {},
          { stroke: "#2563eb", width: 2, ...(stepped ? { paths: stepped({ align: 1 }) } : {}) },
          { stroke: "#dc2626", width: 1, dash: [6, 6], points: { show: false } },
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
      if (container) chart?.setSize({ width: container.clientWidth, height: 300 });
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart?.destroy();
    };
  });
</script>

<section class="space-y-6">
  <div class="space-y-2">
    <div class="flex items-center gap-2">
      <button
        class="rounded border px-3 py-1"
        onclick={() => {
          shift(-1);
        }}
        aria-label="Previous day">&larr;</button
      >
      <span class="font-bold tabular-nums">{day?.date ?? ""}</span>
      <button
        class="rounded border px-3 py-1"
        onclick={() => {
          shift(1);
        }}
        aria-label="Next day">&rarr;</button
      >
      <button class="rounded border px-3 py-1" onclick={() => loadDay()}>Today</button>
      {#if range}
        <button class="rounded border px-3 py-1" onclick={resetRange}>Whole day</button>
      {/if}
    </div>
    <div class="flex flex-wrap gap-4">
      <span>Sitting: <b>{format(totals.sitting)}</b></span>
      <span>Standing: <b>{format(totals.standing)}</b></span>
      {#if range}
        <span class="text-gray-500">selected {clock(range[0] / 60)}-{clock(range[1] / 60)}</span>
      {/if}
    </div>
    <div bind:this={container} class="w-full"></div>
    <p class="text-sm text-gray-500">
      Drag on the chart to total a time range. Dashed line: threshold.
    </p>
  </div>

  <div class="space-y-2">
    <div class="flex items-center gap-2">
      <h2 class="text-lg font-bold">Daily totals</h2>
      <select class="rounded border px-2 py-1" bind:value={span}>
        <option value={7}>7 days</option>
        <option value={30}>30 days</option>
      </select>
      <span class="flex items-center gap-1 text-sm"
        ><i class="inline-block size-3 bg-blue-300"></i> sitting
        <i class="inline-block size-3 bg-blue-700"></i> standing</span
      >
    </div>
    <div class="flex h-40 items-end gap-1">
      {#each daily as d (d.date)}
        <div
          class="flex h-full min-w-0 flex-1 flex-col justify-end"
          title="{d.date}: sitting {format(d.sitting_s)}, standing {format(d.standing_s)}"
        >
          <div class="bg-blue-700" style="height: {(d.standing_s / maxDaily) * 100}%"></div>
          <div class="bg-blue-300" style="height: {(d.sitting_s / maxDaily) * 100}%"></div>
          <span class="truncate text-center text-[10px]">{d.date.slice(5)}</span>
        </div>
      {/each}
    </div>
  </div>
  {#if error}<p class="text-red-600">{error}</p>{/if}
</section>
