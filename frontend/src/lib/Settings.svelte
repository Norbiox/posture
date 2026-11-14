<script lang="ts">
  import { onMount } from "svelte";
  import { api, errorText, loadPresets, presets } from "./api.svelte";

  interface SettingsData {
    work_start: string;
    work_end: string;
    workdays: number[];
    threshold_cm: number;
  }
  interface Holiday {
    date: string;
    name: string;
    automatic: boolean;
  }

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  let settings = $state<SettingsData>({
    work_start: "07:00",
    work_end: "17:00",
    workdays: [],
    threshold_cm: 90,
  });
  let holidays = $state<Holiday[]>([]);
  let holidayDate = $state("");
  let holidayName = $state("");
  let presetName = $state("");
  let presetHeight = $state(100);
  let error = $state("");
  let saved = $state(false);

  async function guard(action: () => Promise<void>): Promise<void> {
    error = "";
    try {
      await action();
    } catch (e) {
      error = errorText(e);
    }
  }

  const loadHolidays = async () => {
    holidays = await api<Holiday[]>("GET", "/holidays");
  };

  const saveSettings = () =>
    guard(async () => {
      settings = await api<SettingsData>("PUT", "/settings", settings);
      saved = true;
      setTimeout(() => {
        saved = false;
      }, 2000);
    });

  const addHoliday = () =>
    guard(async () => {
      await api("POST", "/holidays", { date: holidayDate, name: holidayName });
      holidayName = "";
      await loadHolidays();
    });

  const removeHoliday = (date: string) =>
    guard(async () => {
      await api("DELETE", `/holidays/${date}`);
      await loadHolidays();
    });

  const addPreset = () =>
    guard(async () => {
      await api("POST", "/presets", { name: presetName, height_cm: presetHeight });
      presetName = "";
      await loadPresets();
    });

  const savePreset = (id: number, name: string, height: number) =>
    guard(async () => {
      await api("PUT", `/presets/${String(id)}`, { name, height_cm: height });
      await loadPresets();
    });

  const removePreset = (id: number) =>
    guard(async () => {
      await api("DELETE", `/presets/${String(id)}`);
      await loadPresets();
    });

  function toggleDay(day: number): void {
    settings.workdays = settings.workdays.includes(day)
      ? settings.workdays.filter((d) => d !== day)
      : [...settings.workdays, day];
  }

  onMount(() => {
    void guard(async () => {
      settings = await api<SettingsData>("GET", "/settings");
      await loadHolidays();
    });
  });
</script>

<section class="space-y-8">
  <form
    class="space-y-3"
    onsubmit={(event) => {
      event.preventDefault();
      void saveSettings();
    }}
  >
    <h2 class="text-lg font-bold">Work Hours</h2>
    <div class="flex flex-wrap gap-3">
      <label class="flex flex-col text-sm">
        From
        <input
          type="time"
          class="rounded border px-2 py-1"
          required
          bind:value={settings.work_start}
        />
      </label>
      <label class="flex flex-col text-sm">
        To
        <input
          type="time"
          class="rounded border px-2 py-1"
          required
          bind:value={settings.work_end}
        />
      </label>
    </div>
    <div class="flex flex-wrap gap-3">
      {#each days as name, day (day)}
        <label class="flex items-center gap-1">
          <input
            type="checkbox"
            checked={settings.workdays.includes(day)}
            onchange={() => {
              toggleDay(day);
            }}
          />
          {name}
        </label>
      {/each}
    </div>
    <label class="flex flex-col text-sm">
      Standing from Height (cm)
      <input
        type="number"
        min="62"
        max="127"
        step="0.5"
        class="w-32 rounded border px-2 py-1"
        required
        bind:value={settings.threshold_cm}
      />
    </label>
    <button class="rounded bg-blue-600 px-3 py-1 text-white">Save</button>
    {#if saved}<span class="text-green-700">Saved</span>{/if}
  </form>

  <div class="space-y-2">
    <h2 class="text-lg font-bold">Holidays</h2>
    <ul class="space-y-1">
      {#each holidays as holiday (holiday.date + holiday.name)}
        <li class="flex items-center gap-2">
          <span class="tabular-nums">{holiday.date}</span>
          <span class="grow">{holiday.name}</span>
          {#if holiday.automatic}
            <span class="text-sm text-gray-500">automatic</span>
          {:else}
            <button
              class="rounded border px-2 py-1 text-red-700"
              onclick={() => removeHoliday(holiday.date)}>Remove</button
            >
          {/if}
        </li>
      {/each}
    </ul>
    <form
      class="flex flex-wrap gap-2"
      onsubmit={(event) => {
        event.preventDefault();
        void addHoliday();
      }}
    >
      <input type="date" class="rounded border px-2 py-1" required bind:value={holidayDate} />
      <input
        class="rounded border px-2 py-1"
        placeholder="Name"
        required
        bind:value={holidayName}
      />
      <button class="rounded border px-3 py-1">Add Holiday</button>
    </form>
  </div>

  <div class="space-y-2">
    <h2 class="text-lg font-bold">Presets</h2>
    {#each presets as preset (preset.id)}
      <div class="flex flex-wrap gap-2">
        <input class="rounded border px-2 py-1" bind:value={preset.name} aria-label="Name" />
        <input
          type="number"
          min="62"
          max="127"
          step="0.5"
          class="w-24 rounded border px-2 py-1"
          bind:value={preset.height_cm}
          aria-label="Height in cm"
        />
        <button
          class="rounded border px-2 py-1"
          onclick={() => savePreset(preset.id, preset.name, preset.height_cm)}>Save</button
        >
        <button
          class="rounded border px-2 py-1 text-red-700"
          onclick={() => removePreset(preset.id)}>Delete</button
        >
      </div>
    {/each}
    <form
      class="flex flex-wrap gap-2"
      onsubmit={(event) => {
        event.preventDefault();
        void addPreset();
      }}
    >
      <input class="rounded border px-2 py-1" placeholder="Name" required bind:value={presetName} />
      <input
        type="number"
        min="62"
        max="127"
        step="0.5"
        class="w-24 rounded border px-2 py-1"
        required
        bind:value={presetHeight}
      />
      <button class="rounded border px-3 py-1">Add Preset</button>
    </form>
  </div>
  {#if error}<p class="text-red-600">{error}</p>{/if}
</section>
