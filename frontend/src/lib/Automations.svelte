<script lang="ts">
  import { onMount } from "svelte";
  import { api, errorText, presets, type Stance } from "./api.svelte";

  interface Automation {
    id: number;
    kind: "schedule" | "timer";
    enabled: boolean;
    preset_id: number;
    time_of_day: string | null;
    stance: Stance | null;
    minutes: number | null;
  }

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
    automations = await api<Automation[]>("GET", "/automations");
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

<section class="space-y-4">
  <ul class="space-y-2">
    {#each automations as a (a.id)}
      <li class="flex flex-wrap items-center gap-2 rounded border p-2">
        <input
          type="checkbox"
          checked={a.enabled}
          onchange={() => toggle(a)}
          aria-label="Enabled"
        />
        <span class="grow">
          {#if a.kind === "schedule"}
            Schedule: at {a.time_of_day} move to {presetName(a.preset_id)}
          {:else}
            Timer: after {a.minutes} min {a.stance} move to {presetName(a.preset_id)}
          {/if}
        </span>
        <button
          class="rounded border px-2 py-1"
          onclick={() => {
            edit(a);
          }}>Edit</button
        >
        <button class="rounded border px-2 py-1 text-red-700" onclick={() => remove(a)}
          >Delete</button
        >
      </li>
    {:else}
      <li class="text-gray-500">No Automations yet.</li>
    {/each}
  </ul>

  <form
    class="flex flex-wrap items-end gap-2 rounded border p-3"
    onsubmit={(event) => {
      event.preventDefault();
      void save();
    }}
  >
    <label class="flex flex-col text-sm">
      Type
      <select class="rounded border px-2 py-1" bind:value={kind}>
        <option value="schedule">Schedule</option>
        <option value="timer">Timer</option>
      </select>
    </label>
    {#if kind === "schedule"}
      <label class="flex flex-col text-sm">
        Time
        <input type="time" class="rounded border px-2 py-1" required bind:value={timeOfDay} />
      </label>
    {:else}
      <label class="flex flex-col text-sm">
        Stance
        <select class="rounded border px-2 py-1" bind:value={stance}>
          <option value="sitting">Sitting</option>
          <option value="standing">Standing</option>
        </select>
      </label>
      <label class="flex flex-col text-sm">
        Minutes
        <input
          type="number"
          min="1"
          max="1440"
          class="w-24 rounded border px-2 py-1"
          required
          bind:value={minutes}
        />
      </label>
    {/if}
    <label class="flex flex-col text-sm">
      Move to Preset
      <select class="rounded border px-2 py-1" required bind:value={presetId}>
        <option value={0} disabled>Choose...</option>
        {#each presets as preset (preset.id)}
          <option value={preset.id}>{preset.name}</option>
        {/each}
      </select>
    </label>
    <button class="rounded bg-blue-600 px-3 py-1 text-white">
      {editing === null ? "Add" : "Save"}
    </button>
    {#if editing !== null}
      <button
        type="button"
        class="rounded border px-3 py-1"
        onclick={() => {
          editing = null;
        }}>Cancel</button
      >
    {/if}
  </form>
  {#if error}<p class="text-red-600">{error}</p>{/if}
</section>
