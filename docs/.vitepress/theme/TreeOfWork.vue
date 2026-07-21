<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

/**
 * A play-once, deterministic animation contrasting serial work (one lane,
 * context switches) with kiki's tree (parallel threads, follows, cascade,
 * close-and-fold). One clock drives everything: `t` is seconds into a
 * DURATION-second run, and every element derives its state from thresholds
 * on `t`. CSS transitions do the easing; there is no per-element keyframe
 * code. A replay button resets the clock; the reset fades only the drawn
 * content, never the frame around it.
 */
const DURATION = 16;

const t = ref(0);
const done = ref(false);
const resetting = ref(false);
const reduced = ref(false);
let timer: ReturnType<typeof setInterval> | undefined;
let resetTimers: number[] = [];

// The clock runs below real time so the tree's growth is easy to follow.
const SPEED = 0.8;

function startClock() {
  const start = performance.now();
  timer = setInterval(() => {
    const elapsed = ((performance.now() - start) / 1000) * SPEED;
    if (elapsed >= DURATION) {
      t.value = DURATION;
      done.value = true;
      if (timer) clearInterval(timer);
      timer = undefined;
      return;
    }
    t.value = elapsed;
  }, 100);
}

onMounted(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    reduced.value = true;
    t.value = DURATION; // show the finished scene; CSS suppresses all motion
    return;
  }
  startClock();
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  // Cancel any in-flight reset so a replay can't restart the clock (and
  // leak its interval) after the component is gone.
  for (const id of resetTimers) window.clearTimeout(id);
  resetTimers = [];
});

function replay() {
  if (resetting.value || timer) return;
  done.value = false;
  resetting.value = true;
  // Fade the drawing out, snap every element back to its t=0 state while
  // hidden (transitions are suppressed under .resetting), then fade back
  // in and restart the clock.
  resetTimers = [
    window.setTimeout(() => {
      t.value = 0;
      resetTimers.push(
        window.setTimeout(() => {
          resetting.value = false;
          startClock();
        }, 80),
      );
    }, 340),
  ];
}

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

// Each thread keeps one color across both panels: kiki green for auth,
// sky for billing, lavender for search, and a lighter green for auth's
// child so the lineage reads at a glance. `x` left-aligns the label
// under that job's first commit, and `at` is that commit's time — the
// label appears with the dot it names.
const jobs = [
  { label: "auth", x: 66, at: 1.0, color: "#48d597" },
  { label: "billing", x: 166, at: 5.8, color: "#64b6e0" },
  { label: "search", x: 266, at: 10.6, color: "#b48ee6" },
];

const activeJob = computed(() => (t.value < 4 ? 0 : t.value < 8.8 ? 1 : 2));
const switching = computed(
  () => (t.value >= 4 && t.value < 5.5) || (t.value >= 8.8 && t.value < 10.3),
);

// The agent sits where the next commit will land, so commits pop under
// it and the dot-to-dot rhythm stays even.
const laneDotX = computed(() => {
  let last: number | undefined;
  for (const c of laneCommits) {
    if (c.at <= t.value) last = c.x;
    else return c.x;
  }
  return last! + 28;
});

const leftCaption = computed(() => {
  if (t.value < 4) return "auth: working · billing + search: waiting";
  if (t.value < 5.5) return "context switch: where was I?";
  if (t.value < 8.8) return "billing: working · search still waiting";
  if (t.value < 10.3) return "context switch: rebuild it all again";
  if (t.value < 14) return "search: working · auth going stale";
  return "each job had to wait for the one before it";
});

// --- bottom panel: the tree -----------------------------------------------

// A branch is a short connector curve off the trunk plus a lane that grows
// as commits land: the agent dot rides the tip, commits pop up behind it.
const branches = [
  {
    id: "auth",
    at: 1.0,
    color: "#48d597",
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
    color: "#64b6e0",
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
    color: "#b48ee6",
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
  color: "#8ee6bd",
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

// The agent rides one slot ahead: it sits where the next commit will
// land, the commit pops beneath it, and it slides on to the next slot.
function tipX(lane: Lane): number {
  let last: number | undefined;
  for (const c of lane.commits) {
    if (t.value >= c.at) last = c.x;
    else return c.x;
  }
  return last === undefined ? lane.commits[0]!.x : last + 36;
}

function laneScale(lane: Lane): number {
  return (tipX(lane) - lane.start) / (LANE_END - lane.start);
}

// The base commits sit exactly where the branch connectors leave the
// trunk, so every curve springs from a visible revision. They ripple
// with the branches (a rebase moves the branch points along main), so
// they render inside a shifting group while the later commits stay put.
const baseTrunkCommits = [
  { x: 60, at: 0.3 },
  { x: 80, at: 0.5 },
  { x: 100, at: 0.7 },
];

const trunkCommits: Array<{ x: number; at: number; merge?: boolean }> = [
  { x: 314, at: 9.8 },
  { x: 340, at: 13.2, merge: true },
];

const searchBlocked = computed(() => t.value >= 5.2 && t.value < 7.2);
const rippled = computed(() => t.value >= 9.9);
const rippled2 = computed(() => t.value >= 13.0);
const glow = computed(() => t.value >= 9.9 && t.value < 11.2);
const authClosed = computed(() => t.value >= 12.9);
// Matches the merge trunk commit's `at` so the ring fires as the dot pops.
const mergeLanded = computed(() => t.value >= 13.2);
const authFolded = computed(() => t.value >= 13.9);

// Your attention, hopping between lanes while every agent keeps working.
// Each entry: [arrive-at-seconds, lane key]. The pointer rides just off
// the tip of whichever lane it is attending, so it grows rightward with
// the branch instead of parking at the panel's edge.
const laneById = {
  auth: branches[0]!,
  billing: branches[1]!,
  search: branches[2]!,
  authui: child,
} as const;

const youStops: Array<[number, keyof typeof laneById]> = [
  [1.9, "auth"], // review auth once its lane exists
  [3.2, "billing"], // peek at billing
  [5.4, "search"], // search flagged you: answer it
  [7.4, "auth"], // back to auth…
  [8.4, "authui"], // …and branch auth-ui off it
  [10.6, "billing"], // billing again
  [12.6, "auth"], // auth is done: close it
  [13.8, "search"], // on to the next thing
];

const youLane = computed(() => {
  let key = youStops[0]![1];
  for (const [at, k] of youStops) if (t.value >= at) key = k;
  return key;
});

// Branch groups slide right on each ripple; the pointer, which lives
// outside those groups, adds the same offset to stay glued to the tips.
const rippleOffset = computed(() => (rippled2.value ? 40 : rippled.value ? 14 : 0));

const youX = computed(() =>
  Math.min(tipX(laneById[youLane.value]) + rippleOffset.value, 384),
);
const youY = computed(() => laneById[youLane.value].y);
const youVisible = computed(() => t.value >= 1.9);

const rightCaption = computed(() => {
  if (t.value < 5.2) return "three agents working · you hop where you're useful";
  if (t.value < 7.2) return "search needs you · the rest keep working";
  if (t.value < 9.6) return "you branch auth-ui off auth, live";
  if (t.value < 12.5) return "one rebase onto main · the cascade does the rest";
  if (t.value < 14.6) return "kk close: auth folds into main · auth-ui reroots there";
  return "every thread moved in the same sixteen seconds";
});

// Agents come alive only after their connector finishes drawing, so no
// lane or dot floats in space before its curve reaches it.
const WIRE_DRAW = 0.75;

function dotState(branch: (typeof branches)[number]): string {
  if (branch.id === "search" && searchBlocked.value) return "blocked";
  if (branch.id === "auth" && t.value >= 12.5) return "done";
  return t.value >= branch.at + WIRE_DRAW ? "working" : "off";
}
</script>

<template>
  <div class="tow" :class="{ reduced, resetting }">
    <figure class="tow-fig" role="img"
      aria-label="Animation, played once, contrasting two ways of working. Without kiki: one lane where auth, billing, and search take turns, separated by costly context switches, with your attention pinned to the lane. With kiki: a revision tree where three threads and a child thread grow in parallel while a marker labeled you rides the tip of whichever thread it attends — answering the thread that needs a human, branching a child thread, and closing a finished thread. After one rebase onto the moving main, kiki's cascade carries every following thread forward, and closing the finished auth thread folds its work into main while its child thread auth-ui reroots onto main and keeps going.">
      <div class="tow-stack" aria-hidden="true">
        <div class="tow-panel">
          <div class="tow-head">
            <span class="tow-tag">without kiki</span>
          </div>
          <svg viewBox="0 0 440 84">
            <line class="track" x1="24" y1="56" x2="416" y2="56" />
            <circle v-for="c in laneCommits" :key="c.x" class="commit lane-commit"
              :class="{ on: t >= c.at, stale: t >= 10.3 && c.job === 0 }" :cx="c.x" cy="56" r="4.5"
              :style="{ '--th': jobs[c.job]!.color }" />
            <text v-for="(job, i) in jobs" :key="job.label" class="job-label" :style="{ '--th': job.color }"
              :class="{ on: t >= job.at, active: activeJob === i && !switching }" :x="job.x"
              y="78">{{ job.label }}</text>
            <g class="agent" :class="{ paused: switching }"
              :style="{ transform: `translateX(${laneDotX}px)`, '--th': jobs[activeJob]!.color }">
              <circle cx="0" cy="56" r="5.5" />
              <g class="you pinned">
                <rect x="-18" y="16" width="36" height="18" />
                <text x="0" y="29">you</text>
                <path d="M-4,36 L0,42 L4,36 Z" />
              </g>
            </g>
          </svg>
          <div class="tow-caption">{{ leftCaption }}</div>
        </div>

        <div class="tow-panel">
          <div class="tow-head">
            <span class="tow-tag green">with kiki</span>
          </div>
          <svg viewBox="0 0 440 230">
            <line class="track trunk-line" x1="24" y1="196" x2="292" y2="196" :class="{ on: t >= 0.1 }" />
            <line class="track trunk-line seg2" x1="292" y1="196" x2="416" y2="196" :class="{ on: t >= 9.7 }" />
            <text class="lane-label trunk-label" x="24" y="216" :class="{ on: t >= 0.4 }">main</text>
            <!-- Each base dot shifts on the same stagger as its branch, so the
                 pair stays glued mid-transition, not just at rest. -->
            <g v-for="(c, i) in baseTrunkCommits" :key="c.x" class="branch" :class="{ rippled, rippled2 }"
              :style="{ transitionDelay: rippled ? `${i * 0.12}s` : '0s' }">
              <circle class="commit trunk-commit" :class="{ on: t >= c.at }" :cx="c.x" cy="196" r="4.5" />
            </g>
            <circle v-for="c in trunkCommits" :key="c.x" class="commit trunk-commit"
              :class="{ on: t >= c.at, merge: c.merge }" :cx="c.x" cy="196" r="4.5" />
            <circle class="merge-pulse" :class="{ on: mergeLanded }" cx="340" cy="196" r="9" />
            <text class="merged-label" :class="{ on: authFolded }" x="340" y="216">auth ✓</text>

            <g v-for="(b, i) in branches" :key="b.id" class="branch" :class="{ rippled, rippled2 }"
              :style="{ transitionDelay: rippled ? `${i * 0.12}s` : '0s', '--th': b.color }">
              <path class="wire" :class="{ on: t >= b.at, glow }" :d="b.connector" pathLength="100" />
              <g class="row" :class="{ folding: b.id === 'auth' && authClosed }">
                <line class="lane" :class="{ on: t >= b.at + WIRE_DRAW, glow }" :x1="b.start" :y1="b.y"
                  :x2="LANE_END" :y2="b.y" vector-effect="non-scaling-stroke"
                  :style="{ transform: `scaleX(${laneScale(b)})`, transformOrigin: `${b.start}px ${b.y}px` }" />
                <text class="lane-label" :x="b.labelX" :y="b.y - 10" :class="{ on: t >= b.at + 0.9 }">{{ b.id }}</text>
                <circle v-for="c in b.commits" :key="c.x" class="commit" :class="{ on: t >= c.at }" :cx="c.x"
                  :cy="b.y" r="4.5" />
                <g class="agent" :data-state="dotState(b)" :style="{ transform: `translateX(${tipX(b)}px)` }">
                  <circle cx="0" :cy="b.y" r="5.5" />
                  <circle class="halo" cx="0" :cy="b.y" r="10" />
                </g>
              </g>
              <g class="needs-you" v-if="b.id === 'search'" :class="{ on: searchBlocked }"
                :style="{ transform: `translateX(${tipX(b)}px)` }">
                <rect x="-96" :y="b.y - 34" width="76" height="20" />
                <text x="-58" :y="b.y - 20">needs you</text>
              </g>

              <template v-if="b.id === 'auth'">
                <path class="wire child-wire" :class="{ on: t >= child.at, glow, gone: authClosed }"
                  :style="{ '--th': child.color }" :d="child.connector" pathLength="100" />
                <g class="authui" :class="{ dropped: authClosed }" :style="{ '--th': child.color }">
                  <line class="lane" :class="{ on: t >= child.at + WIRE_DRAW, glow }" :x1="child.start" :y1="child.y"
                    :x2="LANE_END" :y2="child.y" vector-effect="non-scaling-stroke"
                    :style="{ transform: `scaleX(${laneScale(child)})`, transformOrigin: `${child.start}px ${child.y}px` }" />
                  <text class="lane-label" x="304" y="16" :class="{ on: t >= child.at + 0.9 }">auth-ui</text>
                  <circle v-for="c in child.commits" :key="c.x" class="commit" :class="{ on: t >= c.at }" :cx="c.x"
                    :cy="child.y" r="4.5" />
                  <g class="agent" :data-state="t >= child.at + WIRE_DRAW ? 'working' : 'off'"
                    :style="{ transform: `translateX(${tipX(child)}px)` }">
                    <circle cx="0" :cy="child.y" r="5.5" />
                    <circle class="halo" cx="0" :cy="child.y" r="10" />
                  </g>
                </g>
              </template>
            </g>

            <g class="you roaming" :class="{ on: youVisible }"
              :style="{ transform: `translate(${youX}px, ${youY}px)` }">
              <path d="M12,0 L19,-4.5 L19,4.5 Z" />
              <rect x="21" y="-9" width="32" height="18" />
              <text x="37" y="4">you</text>
            </g>
          </svg>
          <div class="tow-caption green">{{ rightCaption }}</div>
        </div>
      </div>
    </figure>
    <button v-if="!reduced" class="tow-replay" :class="{ on: done }" type="button"
      aria-label="Replay the animation" @click="replay">
      ↻ replay
    </button>
  </div>
</template>

<style scoped>
.tow {
  position: relative;
  margin: 28px 0;
  border: 1px solid var(--kiki-line, rgba(200, 214, 205, 0.14));
  border-radius: 0;
  background: linear-gradient(180deg, rgba(13, 21, 18, 0.75), rgba(8, 14, 12, 0.65));
  overflow: hidden;
}

.tow-fig {
  margin: 0;
}

/* Graph-paper dot grid: the instrument the tree is drawn on. */
.tow-panel {
  padding: 16px 20px 12px;
  min-width: 0;
  background-image: radial-gradient(rgba(200, 214, 205, 0.05) 1px, transparent 1px);
  background-size: 18px 18px;
  background-position: 2px 6px;
}

.tow-panel + .tow-panel {
  border-top: 1px solid var(--kiki-line, rgba(200, 214, 205, 0.14));
}

.tow-head {
  display: flex;
  align-items: center;
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

/* Square status marker: hollow for the lane you left behind, filled for
   the tree kiki keeps live. */
.tow-tag::before {
  content: "";
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 7px;
  border: 1px solid currentColor;
  vertical-align: 1px;
  opacity: 0.8;
}

.tow-tag.green {
  color: var(--kiki-green, #48d597);
}

.tow-tag.green::before {
  background: currentColor;
}

.tow svg {
  display: block;
  width: 100%;
  max-width: 580px;
  height: auto;
  margin: 0 auto;
  transition: opacity 0.3s ease;
}

.tow-caption {
  min-height: 18px;
  margin-top: 6px;
  font-size: 11px;
  text-align: center;
  color: rgba(200, 214, 205, 0.5);
  transition: opacity 0.3s ease;
}

.tow-caption.green {
  color: rgba(72, 213, 151, 0.75);
}

/* --- replay: appears once the run finishes --- */

.tow-replay {
  position: absolute;
  top: 12px;
  right: 14px;
  font-family: inherit;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--kiki-green, #48d597);
  background: transparent;
  border: 1px solid rgba(72, 213, 151, 0.35);
  border-radius: 0;
  padding: 4px 10px;
  cursor: pointer;
  opacity: 0;
  /* visibility keeps the hidden button out of the keyboard tab order;
     the delay lets the opacity fade finish before it disappears. */
  visibility: hidden;
  transition:
    opacity 0.4s ease,
    visibility 0s linear 0.4s,
    border-color 0.2s ease;
}

.tow-replay.on {
  opacity: 1;
  visibility: visible;
  transition:
    opacity 0.4s ease,
    visibility 0s,
    border-color 0.2s ease,
    background 0.2s ease;
}

.tow-replay:hover {
  border-color: rgba(72, 213, 151, 0.7);
  background: rgba(72, 213, 151, 0.08);
}

.tow-replay:active {
  transform: translateY(1px);
}

.tow-replay:focus-visible {
  outline: 1px solid rgba(72, 213, 151, 0.8);
  outline-offset: 2px;
}

/* Resetting fades the drawn content only — never the frame, heads, or
   button — and suppresses inner transitions so every element snaps back
   to its t=0 state while hidden. */
.tow.resetting svg,
.tow.resetting .tow-caption {
  opacity: 0;
}

.tow.resetting :deep(svg *) {
  transition: none !important;
  animation: none !important;
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
  stroke: color-mix(in srgb, var(--th, #93a7a0) 30%, transparent);
  stroke-width: 1.5;
  stroke-dasharray: 100;
  stroke-dashoffset: 100;
  transition:
    stroke-dashoffset 0.8s ease,
    stroke 0.5s ease,
    opacity 0.5s ease;
}

.wire.on {
  stroke-dashoffset: 0;
}

.wire.glow {
  stroke: rgba(72, 213, 151, 0.7);
}

.wire.gone {
  opacity: 0;
}

.lane {
  stroke: rgba(200, 214, 205, 0.28);
  stroke: color-mix(in srgb, var(--th, #93a7a0) 38%, transparent);
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
  fill: var(--th, var(--kiki-green, #48d597));
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

.trunk-commit.merge {
  fill: var(--kiki-green, #48d597);
  stroke: none;
}

/* One-shot ring when the fold lands on main. */
.merge-pulse {
  fill: none;
  stroke: rgba(72, 213, 151, 0.8);
  stroke-width: 1.5;
  opacity: 0;
  transform-box: fill-box;
  transform-origin: center;
}

.merge-pulse.on {
  animation: tow-merge 1.1s ease-out 1 both;
}

@keyframes tow-merge {
  0% {
    transform: scale(0.4);
    opacity: 0.9;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

.lane-commit.stale {
  fill: rgba(200, 214, 205, 0.3);
}

.lane-label {
  font-family: inherit;
  font-size: 11px;
  fill: var(--th, rgba(200, 214, 205, 0.55));
  opacity: 0;
  transition: opacity 0.5s ease;
}

.lane-label.on {
  opacity: 0.85;
}

.trunk-label {
  fill: rgba(200, 214, 205, 0.4);
}

/* --- top panel: job labels sit under their cluster of commits --- */

.job-label {
  font-size: 11px;
  fill: rgba(200, 214, 205, 0.35);
  text-anchor: start;
  opacity: 0;
  transition:
    fill 0.4s ease,
    opacity 0.4s ease;
}

.job-label.on {
  opacity: 1;
}

.job-label.active {
  fill: var(--th, var(--kiki-green, #48d597));
}

/* --- agents --- */

.agent {
  transition: transform 0.6s ease;
}

.agent circle {
  fill: var(--th, var(--kiki-green, #48d597));
  transition: fill 0.4s ease;
}

.agent .halo {
  fill: none;
  stroke: var(--th, rgba(72, 213, 151, 0.5));
  stroke-width: 1.5;
  opacity: 0;
}

.agent[data-state="off"] circle {
  fill: transparent;
}

.agent[data-state="working"] > circle:first-child {
  animation: tow-pulse 1.6s ease-in-out infinite;
  filter: drop-shadow(0 0 4px rgba(72, 213, 151, 0.55));
  filter: drop-shadow(0 0 4px color-mix(in srgb, var(--th, #48d597) 60%, transparent));
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
  opacity: 0.55;
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

.you {
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.45));
}

.you rect {
  fill: rgba(24, 34, 30, 0.92);
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

/* --- closing a thread: the fold into main --- */

/* The finished row funnels into the merge commit: its dots converge on
   the merge point while sinking onto the trunk, so the work visibly
   becomes the new revision on main. The origin is the merge commit's
   position minus the branch group's final ripple offset. */
.row {
  transform-origin: 300px 58px;
  transition:
    transform 0.9s ease,
    opacity 0.9s ease;
}

.row.folding {
  transform: translateY(138px) scaleX(0.08);
  opacity: 0;
}

/* The child thread slides into the freed row and inherits the folded
   thread's trunk connector: the row transforms from auth into auth-ui. */
.authui {
  transition: transform 0.9s ease 0.25s;
}

.authui.dropped {
  transform: translate(-182px, 32px);
}

/* Once the fold lands, the merged work is named on the trunk itself,
   right under its merge commit. */
.merged-label {
  font-size: 10px;
  fill: rgba(72, 213, 151, 0.75);
  text-anchor: middle;
  opacity: 0;
  transition: opacity 0.5s ease;
}

.merged-label.on {
  opacity: 1;
}

/* --- cascade ripples: everything moves along --- */

.branch {
  transition: transform 0.7s cubic-bezier(0.3, 1.2, 0.4, 1);
}

.branch.rippled {
  transform: translateX(14px);
}

/* The close pushes everything along again, further than the cascade. */
.branch.rippled2 {
  transform: translateX(40px);
}

/* --- reduced motion: the finished scene appears, nothing moves --- */

/* The clock freezes after mount, which would otherwise fire every CSS
   transition once (wires drawing, lanes stretching, the "you" marker
   flying to its final stop). Suppress all motion so the final scene
   simply appears. */
.tow.reduced :deep(*) {
  transition: none !important;
  animation: none !important;
}
</style>
