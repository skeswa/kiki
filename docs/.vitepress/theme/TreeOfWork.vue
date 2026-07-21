<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

/**
 * A looping, deterministic animation contrasting serial work (one lane,
 * context switches) with kiki's tree (parallel threads, follows, cascade,
 * close). One clock drives everything: `t` is seconds into a LOOP-second
 * cycle, and every element derives its state from thresholds on `t`. CSS
 * transitions do the easing; there is no per-element keyframe code.
 */
const LOOP = 16;

const t = ref(0);
const reduced = ref(false);
let timer: ReturnType<typeof setInterval> | undefined;

onMounted(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    reduced.value = true;
    t.value = 14; // freeze on the fully-grown scene; CSS suppresses all motion
    return;
  }
  const start = performance.now();
  timer = setInterval(() => {
    t.value = ((performance.now() - start) / 1000) % LOOP;
  }, 100);
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});

// --- top panel: one lane, three jobs, two context switches ----------------

const laneCommits = [
  { x: 70, at: 1.0, job: 0 },
  { x: 98, at: 2.0, job: 0 },
  { x: 126, at: 3.0, job: 0 },
  { x: 170, at: 5.8, job: 1 },
  { x: 198, at: 6.8, job: 1 },
  { x: 226, at: 7.8, job: 1 },
  { x: 270, at: 10.6, job: 2 },
  { x: 298, at: 11.6, job: 2 },
  { x: 326, at: 12.6, job: 2 },
];

const chips = [
  { label: "auth", x: 24, w: 56 },
  { label: "billing", x: 92, w: 76 },
  { label: "search", x: 180, w: 70 },
];

const activeJob = computed(() => (t.value < 4 ? 0 : t.value < 8.8 ? 1 : 2));
const switching = computed(
  () => (t.value >= 4 && t.value < 5.5) || (t.value >= 8.8 && t.value < 10.3),
);

const laneDotX = computed(() => {
  const done = laneCommits.filter((c) => c.at <= t.value);
  return done.length === 0 ? 44 : done[done.length - 1]!.x + 22;
});

const leftCaption = computed(() => {
  if (t.value < 4) return "auth: working · billing + search: waiting";
  if (t.value < 5.5) return "context switch: where was I?";
  if (t.value < 8.8) return "billing: working · search still waiting";
  if (t.value < 10.3) return "context switch: rebuild it all again";
  if (t.value < 14) return "search: working · auth going stale";
  return "one lane. everything else waits.";
});

// --- bottom panel: the tree -----------------------------------------------

// A branch is a short connector curve off the trunk plus a lane that grows
// as commits land: the agent dot rides the tip, commits pop up behind it.
const branches = [
  {
    id: "auth",
    at: 1.0,
    y: 58,
    connector: "M60,196 C60,120 84,58 128,58",
    start: 128,
    labelX: 96,
    commits: [
      { x: 158, at: 2.2 },
      { x: 194, at: 3.4 },
      { x: 230, at: 4.6 },
      { x: 266, at: 5.8 },
      { x: 302, at: 7.0 },
      { x: 338, at: 8.2 },
    ],
  },
  {
    id: "billing",
    at: 1.5,
    y: 112,
    connector: "M80,196 C80,150 104,112 148,112",
    start: 148,
    labelX: 116,
    commits: [
      { x: 178, at: 2.7 },
      { x: 214, at: 4.1 },
      { x: 250, at: 5.5 },
      { x: 286, at: 6.9 },
      { x: 322, at: 8.3 },
    ],
  },
  {
    id: "search",
    at: 2.0,
    y: 158,
    connector: "M100,196 C100,176 124,158 168,158",
    start: 168,
    labelX: 136,
    commits: [
      { x: 198, at: 3.2 },
      { x: 234, at: 4.8 },
      { x: 270, at: 7.8 },
      { x: 306, at: 9.0 },
    ],
  },
];

const child = {
  at: 7.6,
  y: 26,
  connector: "M266,58 C266,40 284,26 310,26",
  start: 310,
  commits: [
    { x: 330, at: 8.6 },
    { x: 362, at: 9.4 },
  ],
};

const LANE_END = 392;

type Lane = { at: number; start: number; commits: Array<{ x: number; at: number }> };

function tipX(lane: Lane): number {
  let tip = lane.start + 14;
  for (const c of lane.commits) if (t.value >= c.at) tip = c.x + 22;
  return tip;
}

function laneScale(lane: Lane): number {
  return (tipX(lane) - lane.start) / (LANE_END - lane.start);
}

const trunkCommits = [
  { x: 40, at: 0.3 },
  { x: 70, at: 0.5 },
  { x: 314, at: 9.8 },
];

const searchBlocked = computed(() => t.value >= 5.2 && t.value < 7.2);
const rippled = computed(() => t.value >= 9.9);
const glow = computed(() => t.value >= 9.9 && t.value < 11.2);
const authClosed = computed(() => t.value >= 12.9);

// Your attention, hopping between lanes while every agent keeps working.
// Each entry: [arrive-at-seconds, lane y].
const youStops: Array<[number, number]> = [
  [0.6, 58], // review auth
  [3.2, 112], // peek at billing
  [5.4, 158], // search flagged you: answer it
  [7.4, 58], // back to auth…
  [8.4, 26], // …and branch auth-ui off it
  [10.6, 112], // billing again
  [12.6, 58], // auth is done: close it
  [13.8, 158], // on to the next thing
];

const youY = computed(() => {
  let y = youStops[0]![1];
  for (const [at, stopY] of youStops) if (t.value >= at) y = stopY;
  return y;
});

const youVisible = computed(() => t.value >= 0.6);

const rightCaption = computed(() => {
  if (t.value < 5.2) return "three agents working · you hop where you're useful";
  if (t.value < 7.2) return "search needs you · the rest keep working";
  if (t.value < 9.6) return "you branch auth-ui off auth, live";
  if (t.value < 12.5) return "one rebase onto main · the cascade does the rest";
  if (t.value < 14.3) return "auth ships: kk close · auth-ui keeps going";
  return "same clock. the whole tree moved.";
});

const fading = computed(() => !reduced.value && t.value >= 15.2);

function dotState(branch: (typeof branches)[number]): string {
  if (branch.id === "search" && searchBlocked.value) return "blocked";
  if (branch.id === "auth") {
    if (authClosed.value) return "closed";
    if (t.value >= 12.5) return "done";
  }
  return t.value >= branch.at ? "working" : "off";
}
</script>

<template>
  <figure class="tow" :class="{ fading, reduced }" role="img"
    aria-label="Animation contrasting two ways of working. Without kiki: one lane where auth, billing, and search take turns, separated by costly context switches, with your attention pinned to the lane. With kiki: a revision tree where three threads and a child thread grow in parallel while a marker labeled you hops between them — answering the thread that needs a human, branching a child thread, and closing a finished thread — and after one rebase onto the moving main, kiki's cascade carries every following thread forward.">
    <div class="tow-stack" aria-hidden="true">
      <div class="tow-panel">
        <div class="tow-head">
          <span class="tow-tag">without kiki</span>
          <span class="tow-title">one lane at a time</span>
        </div>
        <svg viewBox="0 0 440 230">
          <g v-for="(chip, i) in chips" :key="chip.label" class="chip"
            :class="{ active: activeJob === i && !switching, waiting: activeJob < i || (switching && activeJob === i) }">
            <rect :x="chip.x" y="18" :width="chip.w" height="24" rx="3" />
            <text :x="chip.x + chip.w / 2" y="34">{{ chip.label }}</text>
          </g>
          <text class="switch-flash" :class="{ on: switching }" x="220" y="96">⌛ context switch…</text>
          <line class="track" x1="24" y1="140" x2="416" y2="140" />
          <circle v-for="c in laneCommits" :key="c.x" class="commit lane-commit"
            :class="{ on: t >= c.at, stale: t >= 10.3 && c.job === 0 }" :cx="c.x" cy="140" r="4.5" />
          <g class="agent" :class="{ paused: switching }" :style="{ transform: `translateX(${laneDotX}px)` }">
            <circle cx="0" cy="140" r="5.5" />
            <g class="you pinned">
              <rect x="-18" y="100" width="36" height="18" rx="3" />
              <text x="0" y="113">you</text>
              <path d="M-4,120 L0,126 L4,120 Z" />
            </g>
          </g>
        </svg>
        <div class="tow-caption">{{ leftCaption }}</div>
      </div>

      <div class="tow-panel">
        <div class="tow-head">
          <span class="tow-tag green">with kiki</span>
          <span class="tow-title">the whole tree, live</span>
        </div>
        <svg viewBox="0 0 440 230">
          <line class="track trunk-line" x1="24" y1="196" x2="292" y2="196" :class="{ on: t >= 0.1 }" />
          <line class="track trunk-line seg2" x1="292" y1="196" x2="416" y2="196" :class="{ on: t >= 9.7 }" />
          <text class="lane-label trunk-label" x="24" y="216" :class="{ on: t >= 0.4 }">main</text>
          <circle v-for="c in trunkCommits" :key="c.x" class="commit trunk-commit" :class="{ on: t >= c.at }"
            :cx="c.x" cy="196" r="4.5" />

          <g v-for="(b, i) in branches" :key="b.id" class="branch" :class="{ rippled }"
            :style="{ transitionDelay: rippled ? `${i * 0.12}s` : '0s' }">
            <path class="wire" :class="{ on: t >= b.at, glow, closed: b.id === 'auth' && authClosed }"
              :d="b.connector" pathLength="100" />
            <line class="lane" :class="{ on: t >= b.at, glow, closed: b.id === 'auth' && authClosed }" :x1="b.start"
              :y1="b.y" :x2="LANE_END" :y2="b.y" vector-effect="non-scaling-stroke"
              :style="{ transform: `scaleX(${laneScale(b)})`, transformOrigin: `${b.start}px ${b.y}px` }" />
            <text class="lane-label" :x="b.labelX" :y="b.y - 10"
              :class="{ on: t >= b.at + 0.5, closed: b.id === 'auth' && authClosed }">{{ b.id }}</text>
            <circle v-for="c in b.commits" :key="c.x" class="commit"
              :class="{ on: t >= c.at, closed: b.id === 'auth' && authClosed }" :cx="c.x" :cy="b.y" r="4.5" />
            <g class="agent" :data-state="dotState(b)" :style="{ transform: `translateX(${tipX(b)}px)` }">
              <circle cx="0" :cy="b.y" r="5.5" />
              <circle class="halo" cx="0" :cy="b.y" r="10" />
            </g>
            <g class="needs-you" v-if="b.id === 'search'" :class="{ on: searchBlocked }"
              :style="{ transform: `translateX(${tipX(b)}px)` }">
              <rect x="-96" :y="b.y - 34" width="76" height="20" rx="3" />
              <text x="-58" :y="b.y - 20">needs you</text>
            </g>

            <template v-if="b.id === 'auth'">
              <path class="wire child-wire" :class="{ on: t >= child.at, glow }" :d="child.connector"
                pathLength="100" />
              <line class="lane" :class="{ on: t >= child.at, glow }" :x1="child.start" :y1="child.y" :x2="LANE_END"
                :y2="child.y" vector-effect="non-scaling-stroke"
                :style="{ transform: `scaleX(${laneScale(child)})`, transformOrigin: `${child.start}px ${child.y}px` }" />
              <text class="lane-label" x="304" y="16" :class="{ on: t >= child.at + 0.5 }">auth-ui</text>
              <circle v-for="c in child.commits" :key="c.x" class="commit" :class="{ on: t >= c.at }" :cx="c.x"
                :cy="child.y" r="4.5" />
              <g class="agent" :data-state="t >= child.at ? 'working' : 'off'"
                :style="{ transform: `translateX(${tipX(child)}px)` }">
                <circle cx="0" :cy="child.y" r="5.5" />
                <circle class="halo" cx="0" :cy="child.y" r="10" />
              </g>
              <g class="closed-chip" :class="{ on: authClosed }">
                <rect x="322" y="68" width="72" height="18" rx="3" />
                <text x="358" y="81">✓ closed</text>
              </g>
            </template>
          </g>

          <g class="you roaming" :class="{ on: youVisible }" :style="{ transform: `translateY(${youY}px)` }">
            <path d="M403,0 L396,4 L403,8 Z" transform="translate(0,-4)" />
            <rect x="404" y="-9" width="32" height="18" rx="3" />
            <text x="420" y="4">you</text>
          </g>
        </svg>
        <div class="tow-caption green">{{ rightCaption }}</div>
      </div>
    </div>
  </figure>
</template>

<style scoped>
.tow {
  margin: 28px 0;
  border: 1px solid var(--kiki-line, rgba(200, 214, 205, 0.14));
  border-radius: 6px;
  background: rgba(9, 16, 14, 0.6);
  overflow: hidden;
  transition: opacity 0.7s ease;
}

.tow.fading {
  opacity: 0;
}

.tow-panel {
  padding: 20px 22px 16px;
  min-width: 0;
}

.tow-panel + .tow-panel {
  border-top: 1px solid var(--kiki-line, rgba(200, 214, 205, 0.14));
}

.tow-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.tow-tag {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(200, 214, 205, 0.45);
}

.tow-tag.green {
  color: var(--kiki-green, #48d597);
}

.tow-title {
  font-size: 12px;
  color: rgba(200, 214, 205, 0.78);
}

.tow svg {
  display: block;
  width: 100%;
  max-width: 620px;
  height: auto;
  margin: 0 auto;
}

.tow-caption {
  min-height: 18px;
  margin-top: 6px;
  font-size: 11px;
  text-align: center;
  color: rgba(200, 214, 205, 0.5);
}

.tow-caption.green {
  color: rgba(72, 213, 151, 0.75);
}

/* --- shared drawing vocabulary --- */

.track {
  stroke: rgba(200, 214, 205, 0.16);
  stroke-width: 1.5;
}

.trunk-line {
  stroke-dasharray: 400;
  stroke-dashoffset: 400;
  transition: stroke-dashoffset 0.9s ease;
}

.trunk-line.on {
  stroke-dashoffset: 0;
}

.wire {
  fill: none;
  stroke: rgba(200, 214, 205, 0.28);
  stroke-width: 1.5;
  stroke-dasharray: 100;
  stroke-dashoffset: 100;
  transition:
    stroke-dashoffset 0.8s ease,
    stroke 0.5s ease;
}

.wire.on {
  stroke-dashoffset: 0;
}

.wire.glow {
  stroke: rgba(72, 213, 151, 0.7);
}

.lane {
  stroke: rgba(200, 214, 205, 0.28);
  stroke-width: 1.5;
  opacity: 0;
  transition:
    transform 0.6s ease,
    opacity 0.4s ease,
    stroke 0.5s ease;
}

.lane.on {
  opacity: 1;
}

.lane.glow {
  stroke: rgba(72, 213, 151, 0.7);
}

.commit {
  fill: var(--kiki-green, #48d597);
  opacity: 0;
  transform: scale(0.2);
  transform-box: fill-box;
  transform-origin: center;
  transition:
    opacity 0.3s ease,
    transform 0.35s cubic-bezier(0.2, 1.6, 0.4, 1),
    fill 0.6s ease;
}

.commit.on {
  opacity: 0.85;
  transform: scale(1);
}

.trunk-commit {
  fill: none;
  stroke: rgba(200, 214, 205, 0.6);
  stroke-width: 1.5;
}

.lane-commit.stale {
  fill: rgba(200, 214, 205, 0.3);
}

.lane-label {
  font-family: inherit;
  font-size: 11px;
  fill: rgba(200, 214, 205, 0.55);
  opacity: 0;
  transition: opacity 0.5s ease;
}

.lane-label.on {
  opacity: 1;
}

.trunk-label {
  fill: rgba(200, 214, 205, 0.4);
}

/* --- top panel --- */

.chip rect {
  fill: rgba(200, 214, 205, 0.06);
  stroke: rgba(200, 214, 205, 0.18);
  transition:
    fill 0.4s ease,
    stroke 0.4s ease;
}

.chip text {
  font-size: 11px;
  fill: rgba(200, 214, 205, 0.45);
  text-anchor: middle;
  transition: fill 0.4s ease;
}

.chip.active rect {
  fill: rgba(72, 213, 151, 0.1);
  stroke: rgba(72, 213, 151, 0.5);
}

.chip.active text {
  fill: var(--kiki-green, #48d597);
}

.chip.waiting text {
  fill: rgba(200, 214, 205, 0.3);
}

.switch-flash {
  font-size: 11px;
  fill: #e8b268;
  text-anchor: middle;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.switch-flash.on {
  opacity: 1;
}

/* --- agents --- */

.agent {
  transition: transform 0.6s ease;
}

.agent circle {
  fill: var(--kiki-green, #48d597);
  transition: fill 0.4s ease;
}

.agent .halo {
  fill: none;
  stroke: rgba(72, 213, 151, 0.5);
  stroke-width: 1.5;
  opacity: 0;
}

.agent[data-state="off"] circle {
  fill: transparent;
}

.agent[data-state="working"] > circle:first-child {
  animation: tow-pulse 1.6s ease-in-out infinite;
}

.agent[data-state="blocked"] circle {
  fill: #e8b268;
}

.agent[data-state="blocked"] .halo {
  stroke: rgba(232, 178, 104, 0.6);
  opacity: 1;
  animation: tow-ring 1.2s ease-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}

.agent[data-state="done"] circle {
  fill: rgba(72, 213, 151, 0.55);
}

.agent[data-state="closed"] circle {
  fill: transparent;
  stroke: rgba(200, 214, 205, 0.35);
  stroke-width: 1.5;
}

.agent.paused > circle {
  fill: rgba(200, 214, 205, 0.35);
}

@keyframes tow-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}

@keyframes tow-ring {
  0% {
    transform: scale(0.6);
    opacity: 0.9;
  }
  100% {
    transform: scale(1.4);
    opacity: 0;
  }
}

/* --- needs-you badge --- */

.needs-you {
  opacity: 0;
  transition:
    opacity 0.3s ease,
    transform 0.6s ease;
}

.needs-you.on {
  opacity: 1;
}

.needs-you rect {
  fill: rgba(232, 178, 104, 0.12);
  stroke: rgba(232, 178, 104, 0.55);
}

.needs-you text {
  font-size: 10px;
  fill: #e8b268;
  text-anchor: middle;
}

/* --- your attention --- */

.you rect {
  fill: rgba(220, 232, 226, 0.08);
  stroke: rgba(220, 232, 226, 0.65);
  stroke-width: 1;
}

.you text {
  font-size: 10px;
  fill: rgba(230, 240, 235, 0.9);
  text-anchor: middle;
  letter-spacing: 0.06em;
}

.you path {
  fill: rgba(220, 232, 226, 0.65);
}

.you.roaming {
  opacity: 0;
  transition:
    transform 0.55s cubic-bezier(0.4, 1.3, 0.4, 1),
    opacity 0.4s ease;
}

.you.roaming.on {
  opacity: 1;
}

/* --- a thread closing --- */

.wire.closed,
.lane.closed {
  stroke: rgba(200, 214, 205, 0.12);
}

.commit.closed {
  fill: rgba(200, 214, 205, 0.25);
  opacity: 0.5;
}

.lane-label.closed {
  opacity: 0.35;
}

.closed-chip {
  opacity: 0;
  transition: opacity 0.4s ease;
}

.closed-chip.on {
  opacity: 1;
}

.closed-chip rect {
  fill: rgba(72, 213, 151, 0.08);
  stroke: rgba(72, 213, 151, 0.4);
}

.closed-chip text {
  font-size: 10px;
  fill: rgba(72, 213, 151, 0.85);
  text-anchor: middle;
}

/* --- cascade ripple --- */

.branch {
  transition: transform 0.7s cubic-bezier(0.3, 1.2, 0.4, 1);
}

.branch.rippled {
  transform: translateX(14px);
}

/* --- reduced motion: the grown scene appears, nothing moves --- */

/* The clock freezes after mount, which would otherwise fire every CSS
   transition once (wires drawing, lanes stretching, the "you" marker
   flying to its final stop). Suppress all motion so the final scene
   simply appears. */
.tow.reduced :deep(*) {
  transition: none !important;
  animation: none !important;
}
</style>
