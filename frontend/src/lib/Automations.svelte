<script lang="ts">
  import { onMount } from "svelte";
  import { api, errorText, presets, type Automation, type Stance } from "./api.svelte";

  let automations = $state<Automation[]>([]);
  let error = $state("");
  let editing = $state<number | null>(null);
  let kind = $state<Automation["kind"]>("schedule");
  let presetId = $state(0);
  let timeOfDay = $state("10:00");
  let stance = $state<Stance>("sitting");
  let minutes = $state(60);

  const presetName = (id: number) => presets.find((p) => p.id === id)?.name ?? "?";

  async function load(): Promise<void> {
    const sortKey = (a: Automation) =>
      a.kind === "schedule" ? `0${a.time_of_day ?? ""}` : `1${String(a.minutes).padStart(4, "0")}`;
    automations = (await api<Automation[]>("GET", "/automations")).sort((a, b) =>
      sortKey(a).localeCompare(sortKey(b)),
    );
  }

  function body(enabled: boolean) {
    return kind === "schedule"
      ? { kind, enabled, preset_id: presetId, time_of_day: timeOfDay }
      : { kind, enabled, preset_id: presetId, stance, minutes };
  }

  async function guard(action: () => Promise<void>): Promise<void> {
    error = "";
    try {
      await action();
      await load();
    } catch (e) {
      error = errorText(e);
    }
  }

  const save = () =>
    guard(async () => {
      if (editing === null) {
        await api("POST", "/automations", body(true));
      } else {
        const current = automations.find((a) => a.id === editing);
        await api("PUT", `/automations/${String(editing)}`, body(current?.enabled ?? true));
        editing = null;
      }
    });

  const toggle = (a: Automation) =>
    guard(async () => {
      const { id, ...rest } = a;
      await api("PUT", `/automations/${String(id)}`, { ...rest, enabled: !a.enabled });
    });

  const remove = (a: Automation) => guard(() => api("DELETE", `/automations/${String(a.id)}`));

  function edit(a: Automation): void {
    editing = a.id;
    kind = a.kind;
    presetId = a.preset_id;
    timeOfDay = a.time_of_day ?? "10:00";
    stance = a.stance ?? "sitting";
    minutes = a.minutes ?? 60;
  }

  onMount(() => {
    void guard(() => Promise.resolve());
  });
</script>

<section class="flex flex-col gap-8">
  <table class="sheet-table">
    <thead>
      <tr>
        <th class="w-10"><span class="sr-only">Enabled</span></th>
        <th>Rule</th>
        <th>Preset</th>
        <th><span class="sr-only">Actions</span></th>
      </tr>
    </thead>
    <tbody>
      {#each automations as a (a.id)}
        <tr class="{a.enabled ? '' : 'text-ink-2'} {editing === a.id ? 'bg-paper-2' : ''}">
          <td>
            <input
              type="checkbox"
              class="size-4 cursor-pointer align-middle"
              checked={a.enabled}
              onchange={() => toggle(a)}
              aria-label="Enabled"
            />
          </td>
          <td>
            {#if a.kind === "schedule"}
              <span class="font-cond mr-2 text-base font-semibold">{a.time_of_day}</span>
              Schedule
            {:else}
              <span class="font-cond mr-2 text-base font-semibold">+{a.minutes} min</span>
              Timer, after {a.minutes} min {a.stance}
            {/if}
          </td>
          <td>{presetName(a.preset_id)}</td>
          <td class="text-right whitespace-nowrap">
            <button
              class="btn btn-sm btn-quiet"
              onclick={() => {
                edit(a);
              }}
            >
              Edit
            </button>
            <button class="btn btn-sm btn-danger" onclick={() => remove(a)}>Delete</button>
          </td>
        </tr>
      {:else}
        <tr>
          <td colspan="4" class="py-4 text-ink-2">No Automations yet. Add the first below.</td>
        </tr>
      {/each}
    </tbody>
  </table>

  <form
    class="flex flex-col gap-4 border-t border-ink pt-4"
    onsubmit={(event) => {
      event.preventDefault();
      void save();
    }}
  >
    <h2>{editing === null ? "New Automation" : "Edit Automation"}</h2>
    <div class="flex flex-wrap items-end gap-3">
      <label class="field">
        Type
        <select class="input" bind:value={kind}>
          <option value="schedule">Schedule</option>
          <option value="timer">Timer</option>
        </select>
      </label>
      {#if kind === "schedule"}
        <label class="field">
          Time
          <input type="time" class="input" required bind:value={timeOfDay} />
        </label>
      {:else}
        <label class="field">
          Stance
          <select class="input" bind:value={stance}>
            <option value="sitting">Sitting</option>
            <option value="standing">Standing</option>
          </select>
        </label>
        <label class="field">
          Minutes
          <input
            type="number"
            min="1"
            max="1440"
            class="input w-24"
            required
            bind:value={minutes}
          />
        </label>
      {/if}
      <label class="field">
        Move to Preset
        <select class="input" required bind:value={presetId}>
          <option value={0} disabled>Choose…</option>
          {#each presets as preset (preset.id)}
            <option value={preset.id}>{preset.name}</option>
          {/each}
        </select>
      </label>
      <button class="btn btn-solid">
        {editing === null ? "Add Automation" : "Save"}
      </button>
      {#if editing !== null}
        <button
          type="button"
          class="btn btn-quiet"
          onclick={() => {
            editing = null;
          }}
        >
          Cancel
        </button>
      {/if}
    </div>
  </form>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</section>
