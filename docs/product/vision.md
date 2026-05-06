# Product vision

kiki (`kk`) is an agentic coding workflow coordinator. It gives a developer a first-class unit for a themed line of work: a jj-backed revision stack, an isolated workspace, a tmux session, and an agent session that can be paused, resumed, published, archived, and composed with related work.

The core product belief is that parallel agentic work should feel cheap enough to use routinely. Today, switching between agent-led lines of inquiry requires manual stashes, branches, rebases, terminal reconstruction, and context reconstruction. kiki makes that work ambient: threads can branch from other threads, follow live ancestor changes, and carry enough local transcript and status context that the human can orient quickly.

## Core principles

- kiki is an ambient coordinator, not a gatekeeper. Developers can still use `jj`, `tmux`, and `gh` directly.
- Threads are cooperative isolation, not a security boundary. v1 separates workspaces to prevent accidental interference; it does not sandbox same-UID processes.
- Human-authored prose is preserved. kiki may draft names, descriptions, and PR text, but it must not silently overwrite deliberate human edits.
- Local transcript data stays local. v1 transcript rows can feed local recall and reopen catch-up, but they must not feed externally published artifacts.
- Cascade safety matters more than eagerness. Descendant workspaces move at agent boundaries or quiescence, not mid-edit.
