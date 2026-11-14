<script lang="ts">
  import { api, errorText, live, loadPresets, presets, send, socket } from "./api.svelte";

  let error = $state("");
  let newName = $state("");

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
      await api("POST", "/presets", { name: newName });
      newName = "";
      await loadPresets();
    });
</script>

<section class="space-y-4">
  <div class="flex flex-wrap items-center gap-3">
    <span class="text-5xl font-bold tabular-nums">
      {live.height_cm === null ? "--" : live.height_cm.toFixed(1)}<span class="text-xl"> cm</span>
    </span>
    <span class="rounded bg-gray-200 px-2 py-1 capitalize">{live.stance ?? "unknown"}</span>
    <span
      class="rounded px-2 py-1 text-white {live.connected && socket.open
        ? 'bg-green-600'
        : 'bg-red-600'}"
    >
      {live.connected && socket.open ? "Desk connected" : "Disconnected"}
    </span>
    {#if live.paused}
      <span class="rounded bg-amber-500 px-2 py-1 text-white">Paused</span>
    {/if}
  </div>

  <div class="grid grid-cols-2 gap-3">
    {#each [["up", "Up"], ["down", "Down"]] as const as [direction, label] (direction)}
      <button
        class="touch-none rounded-lg bg-blue-600 py-8 text-xl text-white select-none active:bg-blue-800"
        onpointerdown={() => {
          send({ type: "hold", direction });
        }}
        onpointerup={() => {
          send({ type: "release" });
        }}
        onpointerleave={() => {
          send({ type: "release" });
        }}
        onpointercancel={() => {
          send({ type: "release" });
        }}
        oncontextmenu={(event) => {
          event.preventDefault();
        }}
      >
        Hold to move {label}
      </button>
    {/each}
  </div>

  <div class="flex flex-wrap gap-2">
    {#each presets as preset (preset.id)}
      <button
        class="rounded border border-blue-600 px-3 py-2 text-blue-700 hover:bg-blue-50"
        onclick={() => goTo(preset.name)}>{preset.name} ({preset.height_cm} cm)</button
      >
    {/each}
    <button class="rounded bg-red-600 px-3 py-2 text-white" onclick={stop}>Stop</button>
  </div>

  <form
    class="flex flex-wrap gap-2"
    onsubmit={(event) => {
      event.preventDefault();
      void saveCurrent();
    }}
  >
    <input
      class="rounded border px-2 py-1"
      placeholder="Preset name"
      required
      bind:value={newName}
    />
    <button class="rounded border px-3 py-1 hover:bg-gray-100">Save current Height as Preset</button
    >
  </form>

  <button class="rounded border px-3 py-2 hover:bg-gray-100" onclick={togglePause}>
    {live.paused ? "Resume Automations" : "Pause Automations for today"}
  </button>

  {#if error}<p class="text-red-600">{error}</p>{/if}
</section>
