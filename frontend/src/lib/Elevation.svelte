<script lang="ts">
  import type { Preset } from "./api.svelte";

  interface Props {
    height: number | null;
    threshold: number | null;
    presets: Preset[];
    moving: boolean;
    online: boolean;
    onpreset: (name: string) => void;
  }
  let { height, threshold, presets, moving, online, onpreset }: Props = $props();

  // Drawn to scale: 2.6 px per cm in a 600 x 400 sheet, floor at y = 380.
  const W = 600;
  const H = 400;
  const FLOOR = 380;
  const PX = 2.6;
  const y = (cm: number) => FLOOR - cm * PX;
  const pctX = (x: number) => `${String((x / W) * 100)}%`;
  const pctY = (v: number) => `${String((v / H) * 100)}%`;

  const REST = y(72); // geometry is drawn at 72 cm and lifted with a transform
  const top = $derived(y(height ?? 72));
  const lift = $derived(`transform: translateY(${String(top - REST)}px)`);
  // IDÅSEN middle column stage travels half as far as the top stage.
  const halfLift = $derived(`transform: translateY(${String((top - REST) / 2)}px)`);
  const CX = 275; // column centre; desktop is 80 cm deep, A-frame foot 70 cm
  const D = PX; // px per cm, for readable geometry below
  const hatch = Array.from({ length: 57 }, (_, i) => 24 + i * 10);

  // Push labels of close Presets apart; a leader ties each label to its true level.
  const MIN_GAP = 32;
  const markers = $derived.by(() => {
    let last = -Infinity;
    return presets
      .toSorted((a, b) => b.height_cm - a.height_cm)
      .map((preset) => {
        const line = y(preset.height_cm);
        const label = Math.max(line, last + MIN_GAP);
        last = label;
        const current = height !== null && Math.abs(height - preset.height_cm) < 0.5;
        return { preset, line, label, current };
      });
  });
  let hovered = $state<Preset["id"] | null>(null); // Preset whose label is under the pointer

  const ink = $derived(moving ? "var(--color-pencil)" : "var(--color-ink)");
  const hidden = $derived(online ? undefined : "5 4");
</script>

<div class="relative w-full select-none" style="aspect-ratio: {W} / {H}">
  <svg
    viewBox="0 0 {W} {H}"
    class="absolute inset-0 h-full w-full overflow-visible"
    role="img"
    aria-label="Side view of the Desk at {height === null
      ? 'unknown Height'
      : `${height.toFixed(1)} cm`}"
  >
    <!-- Ground -->
    <line x1="16" x2={W - 8} y1={FLOOR} y2={FLOOR} stroke="var(--color-ink)" stroke-width="1.5" />
    {#each hatch as x (x)}
      <line x1={x} x2={x - 9} y1={FLOOR + 1} y2={FLOOR + 10} stroke="var(--color-rule)" />
    {/each}

    <!-- Preset levels -->
    {#each markers as m (m.preset.id)}
      <!-- Leader: true level at the Desk, bent to the label when labels were pushed apart. -->
      <polyline
        points="372,{m.line} 386,{m.line} 398,{m.label} {W - 8},{m.label}"
        fill="none"
        stroke={hovered === m.preset.id
          ? "var(--color-ink)"
          : m.current
            ? "var(--color-ink-2)"
            : "var(--color-rule)"}
      />
    {/each}

    <!-- Stance threshold: chain line, drafting convention for a datum -->
    {#if threshold !== null}
      <line
        x1="16"
        x2={W - 8}
        y1={y(threshold)}
        y2={y(threshold)}
        stroke="var(--color-ink-2)"
        stroke-dasharray="14 4 2 4"
      />
    {/if}

    <!-- IKEA IDÅSEN, side view: floor beam with pads, two struts, three round column
         stages standing on the beam, under-top bracket, front paddle, desktop -->
    <clipPath id="above-base"><rect x="0" y="0" width={W} height={y(47)} /></clipPath>
    <g fill="var(--color-paper-2)" stroke="var(--color-ink)" stroke-dasharray={hidden}>
      <path
        d="M{CX - 4 * D} {y(35)} V{y(29)} L{CX - 29 * D} {y(4)} H{CX - 35 * D} Z M{CX + 4 * D} {y(
          35,
        )} V{y(29)} L{CX + 29 * D} {y(4)} H{CX + 35 * D} Z"
      />
      <rect x={CX - 36 * D} y={y(4)} width={72 * D} height={2.5 * D} />
      <rect x={CX - 36 * D} y={y(1.5)} width={6 * D} height={1.5 * D} />
      <rect x={CX + 30 * D} y={y(1.5)} width={6 * D} height={1.5 * D} />
      <g clip-path="url(#above-base)">
        <rect class="slide" x={CX - 3 * D} y={y(67)} width={6 * D} height={40 * D} style={lift} />
        <rect
          class="slide"
          x={CX - 3.5 * D}
          y={y(61)}
          width={7 * D}
          height={45 * D}
          style={halfLift}
        />
      </g>
      <rect x={CX - 4 * D} y={y(48)} width={8 * D} height={44 * D} />
      <g class="slide" style={lift}>
        <rect x={CX - 21.5 * D} y={y(69)} width={43 * D} height={2 * D} />
        <rect x={CX - 36 * D} y={y(69)} width={5 * D} height={2.5 * D} />
        <rect x={CX - 40 * D} y={REST} width={80 * D} height={3 * D} stroke={ink} />
      </g>
    </g>

    <!-- Dimension line, floor to desktop -->
    <g stroke={ink} stroke-width="1" class="transition-[stroke]">
      <g class="slide" style={lift}>
        <line x1="142" x2="167" y1={REST} y2={REST} stroke-dasharray={hidden} />
        <line x1="147" x2="157" y1={REST + 5} y2={REST - 5} stroke-width="2" />
      </g>
      <line
        class="slide"
        x1="152"
        x2="152"
        y1={REST}
        y2={FLOOR}
        style="transform-box: view-box; transform-origin: 152px {FLOOR}px; transform: scaleY({(FLOOR -
          top) /
          (FLOOR - REST)})"
      />
      <line x1="147" x2="157" y1={FLOOR + 5} y2={FLOOR - 5} stroke-width="2" />
    </g>
  </svg>

  <!-- Text lives in HTML so it stays readable at phone width. -->
  <div
    class="slide pointer-events-none absolute right-[77%] flex -translate-y-1/2 flex-col items-end leading-none"
    style="top: {pctY((top + FLOOR) / 2)}"
  >
    <span
      class="font-cond text-[clamp(2.25rem,7vw,4.25rem)] font-semibold tracking-[-0.01em] tabular-nums transition-colors"
      style="color: {ink}"
      aria-live="polite"
    >
      {height === null ? "--.-" : height.toFixed(1)}
    </span>
    <span class="mt-1 text-xs text-ink-2 sm:text-sm">
      {#if !online}last known, cm{:else if moving}cm, moving{:else}cm{/if}
    </span>
  </div>

  {#if threshold !== null}
    <span
      class="pointer-events-none absolute -translate-y-full pb-1 text-xs leading-tight whitespace-nowrap text-ink-2 sm:text-sm"
      style="left: {pctX(16)}; top: {pctY(y(threshold))}"
    >
      Standing from {threshold.toFixed(1)}
    </span>
  {/if}

  {#each markers as m (m.preset.id)}
    <button
      class="absolute -translate-y-full cursor-pointer pb-1 text-left text-xs leading-tight whitespace-nowrap sm:text-sm {m.current
        ? 'font-semibold text-ink'
        : 'text-ink-2 hover:text-ink'}"
      style="left: {pctX(410)}; top: {pctY(m.label)}"
      onclick={() => {
        onpreset(m.preset.name);
      }}
      onmouseenter={() => (hovered = m.preset.id)}
      onmouseleave={() => (hovered = null)}
      aria-label="Move to Preset {m.preset.name}, {m.preset.height_cm} cm"
    >
      <span class="font-cond font-semibold tabular-nums">+{m.preset.height_cm.toFixed(1)}</span>
      <span>{m.preset.name}</span>
    </button>
  {/each}
</div>

<style>
  .slide {
    transition:
      transform 280ms linear,
      top 280ms linear;
  }
  @media (prefers-reduced-motion: reduce) {
    .slide {
      transition: none;
    }
  }
</style>
