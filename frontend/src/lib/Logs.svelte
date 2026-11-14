<script lang="ts">
  import { logs } from "./api.svelte";

  const severity: Record<string, number> = { INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50 };
  let minimum = $state("INFO");
  const visible = $derived(
    logs.filter((line) => (severity[line.level] ?? 0) >= (severity[minimum] ?? 0)),
  );
</script>

<section class="flex flex-col gap-3">
  <label class="field w-40">
    Minimum level
    <select class="input" bind:value={minimum}>
      <option>INFO</option>
      <option>WARNING</option>
      <option>ERROR</option>
    </select>
  </label>
  <div class="h-[65vh] overflow-auto border-y border-ink font-mono text-[12.5px] leading-relaxed">
    {#each visible as line, i (i)}
      <div
        class="grid grid-cols-[auto_5.5rem_1fr] gap-x-4 border-b border-rule px-1 py-0.5 {line.level ===
          'ERROR' || line.level === 'CRITICAL'
          ? 'bg-paper-2 font-semibold'
          : line.level === 'WARNING'
            ? 'font-semibold'
            : ''}"
      >
        <span class="whitespace-nowrap text-ink-2">{line.ts}</span>
        <span>{line.level}</span>
        <span class="break-words">{line.message}</span>
      </div>
    {:else}
      <p class="py-4 font-sans text-ink-2">No log lines at this level.</p>
    {/each}
  </div>
</section>
