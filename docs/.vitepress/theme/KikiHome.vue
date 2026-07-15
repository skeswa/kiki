<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { withBase } from "vitepress";

type ThreadState = {
  command: string;
  note: string;
  payment: string;
  tests: string;
  bug: string;
  active: "payment" | "tests" | "bug";
};

const states: ThreadState[] = [
  {
    command: "kk new payment-refactor",
    note: "a thread: workspace + tmux session + agent",
    payment: "● working",
    tests: "queued",
    bug: "queued",
    active: "payment",
  },
  {
    command: "kk new bug-investigation",
    note: "parallel lines of inquiry, isolated on disk",
    payment: "● working",
    tests: "queued",
    bug: "● working",
    active: "bug",
  },
  {
    command: "kk new add-tests --follows payment-refactor",
    note: "follow edge recorded — related in history",
    payment: "● working",
    tests: "● working",
    bug: "● working",
    active: "tests",
  },
  {
    command: "# payment-refactor amends an ancestor",
    note: "kiki waits for add-tests to reach a safe boundary",
    payment: "✓ done",
    tests: "◐ reconciling",
    bug: "● working",
    active: "tests",
  },
];

const principles = [
  [
    "01",
    "be additive, not invasive",
    "Keep using jj, gh, and tmux as you always have. kiki reacts; it does not intercept or wrap.",
  ],
  [
    "02",
    "trust human prose",
    "The moment a human writes their own description, kiki steps off. Permanently.",
  ],
  [
    "03",
    "one stable contract; many UIs",
    "The gRPC service is the product surface. CLI and TUI are clients, not privileged exceptions.",
  ],
  [
    "04",
    "fail loud, not silent",
    "When the system cannot determine the right action, it stops and asks rather than guessing.",
  ],
  [
    "05",
    "no resource policing",
    "Concurrent agents, model spend, and laptop CPU remain your decisions, made with your tools.",
  ],
  [
    "06",
    "explicit egress",
    "Local transcripts never become PR copy. Sending text to a provider requires purpose-specific consent.",
  ],
];

const roadmap = [
  [
    "v1",
    "the acceptance slice",
    "Thread atom, recoverable lifecycle, linear live-follow cascade, batch-safe delivery, and projection repair.",
  ],
  [
    "v1.x",
    "workflow completion",
    "Stacked publishing, transcript catch-up, the overlay TUI, GitHub polling, and auto-archive.",
  ],
  [
    "v2",
    "the substrate",
    "Cross-thread messaging, the Codex adapter, native macOS UI, and direct GitHub APIs.",
  ],
  [
    "v3+",
    "further out",
    "jj-lib embedded in kkd, a web dashboard, and cross-repository coordination.",
  ],
];

const step = ref(0);
let timer: ReturnType<typeof setInterval> | undefined;

onMounted(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  timer = setInterval(() => {
    step.value = (step.value + 1) % states.length;
  }, 2800);
});

onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <main class="kiki-home">
    <section class="home-hero" aria-labelledby="hero-title">
      <p class="eyebrow">// a daemon-backed coordinator</p>
      <h1 id="hero-title">
        Multi-threaded coding<br />with AI agents,<br />
        <SlotCycle
          :phrases="[
            'without the stash.',
            'without the rebase.',
            'without losing context.',
            'in parallel.',
          ]"
        />
      </h1>
      <p class="hero-deck">
        One workflow for several pieces of code and several agents at once. kiki ties
        <a href="https://github.com/jj-vcs/jj">jujutsu (jj)</a>,
        <a href="https://github.com/tmux/tmux">tmux</a>, agent harnesses, and the GitHub CLI behind
        a single command: <strong>kk</strong>.
      </p>
      <div class="hero-actions">
        <a class="button primary" :href="withBase('/reference/')">read the reference →</a>
        <a class="button secondary" href="https://github.com/skeswa/kiki">github ↗</a>
        <code>$ kk new auth-refactor<i aria-hidden="true" /></code>
      </div>
    </section>

    <dl class="fact-strip" aria-label="Project facts">
      <div>
        <dt>vcs</dt>
        <dd>jujutsu (jj)</dd>
      </div>
      <div>
        <dt>harness</dt>
        <dd>Claude Code</dd>
      </div>
      <div>
        <dt>license</dt>
        <dd>MIT</dd>
      </div>
      <div>
        <dt>status</dt>
        <dd class="status">
          <SlotCycle
            :phrases="['pre-alpha · spec phase', 'implementation: not begun', 'feedback wanted']"
            :interval="3400"
          />
        </dd>
      </div>
    </dl>

    <section class="ledger-row problem-row" aria-labelledby="problem-title">
      <header><p id="problem-title" class="eyebrow">01 / the problem</p></header>
      <div class="row-copy">
        <p class="lead">
          The friction is in the seams. You stash, you switch branches, and three minutes later the
          original branch is a state you have to reconstruct — and the agent has lost the thread.
        </p>
        <p>
          Multiply that by three or four lines of inquiry in flight and the cost of opening another
          becomes prohibitive. But refactoring a function and migrating its callers is not a
          sequential task; it is a tree of work. The right tool lets those branches exist in
          parallel without worktrees colliding or people manually rebasing the world.
        </p>
        <p>kiki is an attempt to build that tool.</p>
      </div>
    </section>

    <section class="ledger-row thread-row" aria-labelledby="thread-title">
      <header>
        <p id="thread-title" class="eyebrow">02 / the thread</p>
        <p>
          A themed sequence of jj revisions with a live head, one workspace, one tmux session, and
          one agent. Isolated on disk, related in history.
        </p>
      </header>
      <div class="thread-demo">
        <p class="demo-command">
          <span>$</span> {{ states[step].command }}<i aria-hidden="true" />
        </p>
        <div class="trunk"><i /> <strong>main</strong> <span>trunk</span></div>
        <div class="trunk-line" />
        <div class="thread-cards">
          <div class="thread-stack">
            <article :class="{ active: states[step].active === 'payment' }">
              <div>
                <strong>payment-refactor</strong><span>{{ states[step].payment }}</span>
              </div>
              <small>agent A · jj workspace · tmux</small>
            </article>
            <div class="follow-line"><span>follows · reconcile + inform on evolve</span></div>
            <article
              class="test-card"
              :class="{
                active: states[step].active === 'tests',
                reconciling: states[step].tests.includes('◐'),
              }"
            >
              <div>
                <strong>add-tests</strong><span>{{ states[step].tests }}</span>
              </div>
              <small>agent B · jj workspace · tmux</small>
            </article>
          </div>
          <article :class="{ active: states[step].active === 'bug' }">
            <div>
              <strong>bug-investigation</strong><span>{{ states[step].bug }}</span>
            </div>
            <small>agent C · jj workspace · tmux</small>
          </article>
        </div>
        <p class="demo-note">// {{ states[step].note }}</p>
        <p class="thread-explainer">
          When an ancestor is amended, jj evolves descendants in repository state. kiki waits for a
          <strong>safe boundary</strong> before materializing that state in the thread’s files and
          telling the agent. Never mid-edit. Ambiguous topology stops for a human instead of
          guessing.
        </p>
      </div>
    </section>

    <section class="ledger-row" aria-labelledby="example-title">
      <header>
        <p id="example-title" class="eyebrow">03 / worked example</p>
        <p>Spawn, relate, inspect, switch, publish, close. Six verbs.</p>
      </header>
      <div class="terminal" aria-label="Example kiki terminal session">
        <span># opt a repository in</span>
        <code><i>$</i> kk init</code>
        <span># spawn a thread, then a child that follows it</span>
        <code><i>$</i> kk new auth-refactor</code>
        <code><i>$</i> kk new add-tests --follows auth-refactor</code>
        <code><i>$</i> kk ls</code>
        <b>&nbsp;&nbsp;running&nbsp;&nbsp;auth-refactor&nbsp;&nbsp;—&nbsp;&nbsp;claude-code</b>
        <b
          >&nbsp;&nbsp;running&nbsp;&nbsp;add-tests&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;auth-refactor&nbsp;&nbsp;claude-code</b
        >
        <code><i>$</i> kk switch auth-refactor</code>
        <code><i>$</i> kk close <span># workspace removed, revisions persist</span></code>
      </div>
    </section>

    <section class="ledger-row" aria-labelledby="principles-title">
      <header>
        <p id="principles-title" class="eyebrow">04 / principles, explicit</p>
        <p>Stated up front, because the reference book’s coherence depends on them.</p>
      </header>
      <div class="principle-grid">
        <article v-for="principle in principles" :key="principle[0]">
          <h2>
            <span>{{ principle[0] }}</span> {{ principle[1] }}
          </h2>
          <p>{{ principle[2] }}</p>
        </article>
      </div>
    </section>

    <section id="roadmap" class="ledger-row" aria-labelledby="roadmap-title">
      <header>
        <p id="roadmap-title" class="eyebrow">05 / roadmap</p>
        <p>The canonical scope ledger lives in the book’s Orientation chapter.</p>
      </header>
      <div class="roadmap-list">
        <article v-for="item in roadmap" :key="item[0]">
          <strong>{{ item[0] }}</strong
          ><b>{{ item[1] }}</b>
          <p>{{ item[2] }}</p>
        </article>
      </div>
    </section>

    <section class="closing-grid">
      <div>
        <p class="eyebrow">on the name</p>
        <p>
          <strong>kk</strong> sits on the home row immediately beside <strong>jj</strong> — a quiet
          acknowledgement that one tool works underneath the other. And a kiki is a gathering where
          everyone shows up as themselves and the room is richer for the multiplicity. 💅🏾
        </p>
      </div>
      <div>
        <p class="closing-lead">
          The spec is durable enough that pre-implementation feedback is genuinely actionable.
        </p>
        <div class="hero-actions">
          <a class="button primary" :href="withBase('/reference/')">read the book →</a>
          <a class="button secondary" href="https://github.com/skeswa/kiki/issues"
            >file an issue ↗</a
          >
        </div>
      </div>
    </section>

    <footer class="home-footer">
      <span>MIT © 2026 Sandile Keswa</span>
      <span>built on jj · tmux · agent harnesses · gh</span>
    </footer>
  </main>
</template>
