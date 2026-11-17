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
    note: "a thread: workspace + terminal group + agent",
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
    note: "follow edge recorded between the threads",
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
    "keep using your tools",
    "Keep using jj, gh, and Herdr as you always have. kiki reacts; it does not intercept or wrap.",
  ],
  [
    "02",
    "trust human prose",
    "The moment a human writes their own description, kiki steps off. Permanently.",
  ],
  [
    "03",
    "one stable contract; many UIs",
    "The CLI and TUI use the same gRPC service and follow the same access rules.",
  ],
  [
    "04",
    "report uncertain state",
    "When kiki cannot determine the next action, it stops and asks for a human decision.",
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
    "Create and recover threads, coordinate updates along linear revision chains, deliver context safely, and repair mismatches.",
  ],
  [
    "v1.x",
    "workflow completion",
    "Stacked publishing, transcript catch-up, the overlay TUI, GitHub polling, and auto-archive.",
  ],
  [
    "v2",
    "more integrations",
    "Cross-thread messaging, further harness adapters, native macOS UI, and direct GitHub APIs.",
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
            'in separate workspaces.',
            'with linked threads.',
            'with tracked dependencies.',
            'in parallel.',
          ]"
        />
      </h1>
      <p class="hero-deck">
        One workflow for several pieces of code and several agents at once. kiki ties
        <a href="https://github.com/jj-vcs/jj">jujutsu (jj)</a>,
        <a href="https://github.com/herdrdev/herdr">Herdr</a>, agent harnesses, and the GitHub CLI
        behind a single command: <strong>kk</strong>.
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
        <dd>
          <SlotCycle :phrases="['Claude Code', 'Codex']" :interval="3000" />
        </dd>
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
          Several agents can work at once, but you still have to track their workspaces, terminals,
          and revision chains. Switching tasks means finding where each agent left off.
        </p>
        <p>
          A refactor may have separate tasks for tests and callers. When the shared code changes,
          those tasks need updated files and an explanation of what moved. Kiki tracks the
          dependencies and coordinates those updates.
        </p>
        <p>The design is written. Implementation has not started.</p>
      </div>
    </section>

    <section class="ledger-row thread-row" aria-labelledby="thread-title">
      <header>
        <p id="thread-title" class="eyebrow">02 / the thread</p>
        <p>
          A named line of work with a live jj head, a workspace, a terminal group, and an agent.
          Each thread edits its own files and can follow related threads.
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
              <small>agent A · jj workspace · terminal</small>
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
              <small>agent B · jj workspace · terminal</small>
            </article>
          </div>
          <article :class="{ active: states[step].active === 'bug' }">
            <div>
              <strong>bug-investigation</strong><span>{{ states[step].bug }}</span>
            </div>
            <small>agent C · jj workspace · terminal</small>
          </article>
        </div>
        <p class="demo-note">// {{ states[step].note }}</p>
        <p class="thread-explainer">
          When an ancestor is amended, jj evolves descendants in repository state. kiki waits for a
          <strong>safe boundary</strong> before materializing that state in the thread’s files and
          telling the agent. It does not change files mid-edit. If the revision relationships are
          ambiguous, kiki stops for a human decision.
        </p>
      </div>
    </section>

    <section class="ledger-row" aria-labelledby="example-title">
      <header>
        <p id="example-title" class="eyebrow">03 / worked example</p>
        <p>Create two related threads, inspect them, switch to one, and close it.</p>
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
          >&nbsp;&nbsp;running&nbsp;&nbsp;add-tests&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;auth-refactor&nbsp;&nbsp;codex</b
        >
        <code><i>$</i> kk switch auth-refactor</code>
        <code><i>$</i> kk close <span># workspace removed, revisions persist</span></code>
      </div>
    </section>

    <section class="ledger-row" aria-labelledby="principles-title">
      <header>
        <p id="principles-title" class="eyebrow">04 / principles, explicit</p>
        <p>These rules guide the implementation.</p>
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
        <p>The Orientation chapter defines what ships in each release.</p>
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
          <strong>kk</strong> sits beside <strong>jj</strong> on the keyboard’s home row. The names
          reflect how the tools work together. A kiki is a gathering, which fits a project about
          several agents and a person working together. 💅🏾
        </p>
      </div>
      <div>
        <p class="closing-lead">
          Implementation has not started. Feedback can still change the design.
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
      <span>built on jj · Herdr · agent harnesses · gh</span>
    </footer>
  </main>
</template>
