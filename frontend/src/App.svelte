<script lang="ts">
  import { onMount } from "svelte";
  import { connect, loadLogs, loadPresets } from "./lib/api.svelte";
  import Automations from "./lib/Automations.svelte";
  import Control from "./lib/Control.svelte";
  import Logs from "./lib/Logs.svelte";
  import Settings from "./lib/Settings.svelte";
  import Stats from "./lib/Stats.svelte";

  const tabs = ["Control", "Stats", "Automations", "Settings", "Logs"] as const;
  let tab = $state<(typeof tabs)[number]>("Control");

  onMount(() => {
    connect();
    void loadPresets();
    void loadLogs();
  });
</script>

<div class="mx-auto max-w-3xl p-4">
  <h1 class="mb-3 text-2xl font-bold">Posture</h1>
  <nav class="mb-4 flex flex-wrap gap-1 border-b border-gray-300">
    {#each tabs as name (name)}
      <button
        class="rounded-t px-3 py-2 {tab === name ? 'bg-blue-600 text-white' : 'hover:bg-gray-100'}"
        onclick={() => (tab = name)}>{name}</button
      >
    {/each}
  </nav>
  {#if tab === "Control"}
    <Control />
  {:else if tab === "Stats"}
    <Stats />
  {:else if tab === "Automations"}
    <Automations />
  {:else if tab === "Settings"}
    <Settings />
  {:else}
    <Logs />
  {/if}
</div>
