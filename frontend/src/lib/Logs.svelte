<script lang="ts">
  import { logs } from "./api.svelte";

  const severity: Record<string, number> = { INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50 };
  let minimum = $state("INFO");
  const visible = $derived(
    logs.filter((line) => (severity[line.level] ?? 0) >= (severity[minimum] ?? 0)),
  );
</script>

<section class="space-y-2">
  <label class="flex items-center gap-2">
    Level
    <select class="rounded border px-2 py-1" bind:value={minimum}>
      <option>INFO</option>
      <option>WARNING</option>
      <option>ERROR</option>
    </select>
  </label>
  <div class="h-[60vh] overflow-auto rounded bg-gray-900 p-2 font-mono text-xs text-gray-100">
    {#each visible as line, i (i)}
      <div
        class={line.level === "ERROR" || line.level === "CRITICAL"
          ? "text-red-400"
          : line.level === "WARNING"
            ? "text-amber-300"
            : ""}
      >
        {line.ts}
        {line.level}
        {line.message}
      </div>
    {/each}
  </div>
</section>
