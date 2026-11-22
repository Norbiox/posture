<script lang="ts">
  import { onMount } from "svelte";
  import { api, errorText, loadPresets, presets, type SettingsData } from "./api.svelte";

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
    move_retries: 2,
  });
  let holidays = $state<Holiday[]>([]);
  let holidayDate = $state("");
  let holidayName = $state("");
  let presetName = $state("");
  let presetHeight = $state(100);
  let error = $state("");
  // Last server copy: each form saves only its own fields on top of it.
  let stored = $state<SettingsData | null>(null);
  let saved = $state<"" | "work" | "stance" | "moves">("");

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

  const saveSettings = (part: "work" | "stance" | "moves", fields: Partial<SettingsData>) =>
    guard(async () => {
      stored = await api<SettingsData>("PUT", "/settings", { ...stored, ...fields });
      settings = { ...settings, ...fields };
      saved = part;
      setTimeout(() => {
        saved = "";
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
      stored = await api<SettingsData>("GET", "/settings");
      settings = { ...stored };
      await loadHolidays();
    });
  });
</script>

<section class="grid gap-x-12 gap-y-10 lg:grid-cols-2">
  <div class="flex flex-col gap-y-10">
    <form
      class="flex flex-col gap-4 border-t border-ink pt-4"
      onsubmit={(event) => {
        event.preventDefault();
        const { work_start, work_end, workdays } = settings;
        void saveSettings("work", { work_start, work_end, workdays });
      }}
    >
      <h2>Work Hours</h2>
      <div class="flex flex-wrap gap-3">
        <label class="field">
          From
          <input type="time" class="input" required bind:value={settings.work_start} />
        </label>
        <label class="field">
          To
          <input type="time" class="input" required bind:value={settings.work_end} />
        </label>
      </div>
      <fieldset class="flex flex-col gap-1">
        <legend class="mb-1 text-[0.8125rem] text-ink-2">Workdays</legend>
        <div class="flex flex-wrap gap-px">
          {#each days as name, day (day)}
            <label
              class="flex h-9 min-w-12 cursor-pointer items-center justify-center border border-rule-strong px-2 has-checked:border-ink has-checked:bg-ink has-checked:text-paper has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ink"
            >
              <input
                type="checkbox"
                class="sr-only"
                checked={settings.workdays.includes(day)}
                onchange={() => {
                  toggleDay(day);
                }}
              />
              {name}
            </label>
          {/each}
        </div>
      </fieldset>
      <div class="flex items-center gap-3">
        <button class="btn btn-solid">Save Work Hours</button>
        {#if saved === "work"}<span class="text-sm" role="status">Saved.</span>{/if}
      </div>
    </form>

    <form
      class="flex flex-col gap-4 border-t border-ink pt-4"
      onsubmit={(event) => {
        event.preventDefault();
        void saveSettings("stance", { threshold_cm: settings.threshold_cm });
      }}
    >
      <h2>Stance</h2>
      <label class="field">
        Standing from Height, cm
        <input
          type="number"
          min="62"
          max="127"
          step="0.5"
          class="input w-32"
          required
          bind:value={settings.threshold_cm}
        />
      </label>
      <div class="flex items-center gap-3">
        <button class="btn btn-solid">Save Stance threshold</button>
        {#if saved === "stance"}<span class="text-sm" role="status">Saved.</span>{/if}
      </div>
    </form>

    <form
      class="flex flex-col gap-4 border-t border-ink pt-4"
      onsubmit={(event) => {
        event.preventDefault();
        void saveSettings("moves", { move_retries: settings.move_retries });
      }}
    >
      <h2>Moves</h2>
      <label class="field">
        Retries after an Interruption
        <input
          type="number"
          min="0"
          max="5"
          step="1"
          class="input w-32"
          required
          bind:value={settings.move_retries}
        />
      </label>
      <p class="text-sm text-ink-2">
        When something stops the Desk before it reaches a Preset or Height, Posture resumes the move
        this many times, then leaves the Desk where it stopped.
      </p>
      <div class="flex items-center gap-3">
        <button class="btn btn-solid">Save Moves</button>
        {#if saved === "moves"}<span class="text-sm" role="status">Saved.</span>{/if}
      </div>
    </form>
  </div>

  <div class="flex flex-col gap-4 border-t border-ink pt-4">
    <h2>Presets</h2>
    <table class="sheet-table">
      <thead><tr><th>Name</th><th>Height, cm</th><th></th></tr></thead>
      <tbody>
        {#each presets as preset (preset.id)}
          <tr>
            <td><input class="input w-full" bind:value={preset.name} aria-label="Name" /></td>
            <td>
              <input
                type="number"
                min="62"
                max="127"
                step="0.5"
                class="input w-24"
                bind:value={preset.height_cm}
                aria-label="Height in cm"
              />
            </td>
            <td class="text-right whitespace-nowrap">
              <button
                class="btn btn-sm btn-quiet"
                onclick={() => savePreset(preset.id, preset.name, preset.height_cm)}
              >
                Save
              </button>
              <button class="btn btn-sm btn-danger" onclick={() => removePreset(preset.id)}>
                Delete
              </button>
            </td>
          </tr>
        {:else}
          <tr><td colspan="3" class="py-4 text-ink-2">No Presets yet.</td></tr>
        {/each}
      </tbody>
    </table>
    <form
      class="flex flex-wrap items-end gap-2"
      onsubmit={(event) => {
        event.preventDefault();
        void addPreset();
      }}
    >
      <label class="field grow">
        Name
        <input class="input" placeholder="e.g. Standing" required bind:value={presetName} />
      </label>
      <label class="field">
        Height, cm
        <input
          type="number"
          min="62"
          max="127"
          step="0.5"
          class="input w-24"
          required
          bind:value={presetHeight}
        />
      </label>
      <button class="btn">Add Preset</button>
    </form>
  </div>

  <div class="flex flex-col gap-4 border-t border-ink pt-4 lg:col-span-2">
    <h2>Holidays</h2>
    <table class="sheet-table">
      <thead><tr><th>Date</th><th>Name</th><th></th></tr></thead>
      <tbody>
        {#each holidays as holiday (holiday.date + holiday.name)}
          <tr>
            <td class="font-cond w-32 text-base">{holiday.date}</td>
            <td>{holiday.name}</td>
            <td class="text-right">
              {#if holiday.automatic}
                <span class="text-sm text-ink-2">automatic</span>
              {:else}
                <button class="btn btn-sm btn-danger" onclick={() => removeHoliday(holiday.date)}>
                  Remove
                </button>
              {/if}
            </td>
          </tr>
        {:else}
          <tr><td colspan="3" class="py-4 text-ink-2">No Holidays.</td></tr>
        {/each}
      </tbody>
    </table>
    <form
      class="flex flex-wrap items-end gap-2"
      onsubmit={(event) => {
        event.preventDefault();
        void addHoliday();
      }}
    >
      <label class="field">
        Date
        <input type="date" class="input" required bind:value={holidayDate} />
      </label>
      <label class="field grow sm:max-w-xs">
        Name
        <input class="input" placeholder="e.g. Company day off" required bind:value={holidayName} />
      </label>
      <button class="btn">Add Holiday</button>
    </form>
  </div>
  {#if error}<p class="error lg:col-span-2" role="alert">{error}</p>{/if}
</section>
