<script lang="ts">
  import { onMount } from "svelte";
  import { connect, live, loadLogs, loadPresets, socket } from "./lib/api.svelte";
  import Automations from "./lib/Automations.svelte";
  import Control from "./lib/Control.svelte";
  import Logs from "./lib/Logs.svelte";
  import Settings from "./lib/Settings.svelte";
  import Stats from "./lib/Stats.svelte";

  const tabs = ["Control", "Stats", "Automations", "Settings", "Logs"] as const;
  let tab = $state<(typeof tabs)[number]>("Control");
  const online = $derived(live.connected && socket.open);

  onMount(() => {
    connect();
    void loadPresets();
    void loadLogs();
  });
</script>

<div class="mx-auto flex min-h-dvh max-w-6xl flex-col px-4 sm:px-6">
  <header
    class="flex flex-wrap items-end gap-x-8 gap-y-2 border-b border-ink pt-4 sm:flex-nowrap sm:pt-5"
  >
    <h1 class="font-cond pb-2 text-2xl leading-none font-semibold tracking-[0.02em]">Posture</h1>
    <div
      class="-mb-px flex grow gap-5 overflow-x-auto [scrollbar-width:none]"
      role="tablist"
      aria-label="Sections"
    >
      {#each tabs as name (name)}
        <button
          role="tab"
          aria-selected={tab === name}
          class="shrink-0 cursor-pointer border-b-2 pb-2 text-[0.9375rem] font-medium transition-colors {tab ===
          name
            ? 'border-ink text-ink'
            : 'border-transparent text-ink-2 hover:text-ink'}"
          onclick={() => (tab = name)}>{name}</button
        >
      {/each}
    </div>
    <p
      class="order-first flex w-full items-center gap-4 pb-2 text-sm sm:order-none sm:w-auto sm:shrink-0"
      aria-live="polite"
    >
      <span class="flex items-center gap-2 {online ? 'text-ink' : 'text-ink-2'}">
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <circle
            cx="5"
            cy="5"
            r="4"
            fill={online ? "currentColor" : "none"}
            stroke="currentColor"
            stroke-width="1"
            stroke-dasharray={online ? "none" : "2 1.5"}
          />
        </svg>
        {online ? "Desk connected" : "Disconnected"}
      </span>
      {#if live.paused}
        <span class="border border-ink px-1.5 leading-5 font-medium">Paused today</span>
      {/if}
    </p>
  </header>

  <main class="grow py-6 sm:py-8">
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
  </main>
</div>
