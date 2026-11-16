# Interface

Kiki's threads are viewed through a Herdr client attached to kiki's dedicated Herdr server. Herdr draws panes, tabs, and its native sidebar; kiki publishes a label and tokens into that sidebar and draws only the overlay, approval cards, and an optional Stack pane. Which of these surfaces belong to the acceptance slice and which are v1.x polish is recorded once, in [Orientation](../01-orientation.md). The two documents here are the v1 contract for each surface when it ships:

1. [Specification](spec.md) — the vocabulary, the split between native Herdr UI and custom kiki UI, glyphs, wireframes, keymaps, toasts and notifications, mouse behavior, fallbacks, and the configuration the surfaces read.
2. [Storyboard](storyboard.md) — one developer's end-to-end story (porting an iOS app to Android, with a docs repo and a marketing-site fix along the way) that exercises every branching, merging, and abandoning pattern the rest of the book commits to.

The specification is the rulebook; the storyboard is the movie. When they disagree, the specification wins, and the storyboard has the bug.

The storyboard invents nothing: no new commands, flags, output strings, glyphs, or screen elements. Every beat in it traces back to [Threads](../03-threads.md), [Cascade](../05-cascade.md), [Publishing](../07-publishing.md), [Commands](../09-commands.md), [spec.md](spec.md), [Terminal runtime](../13-architecture/terminal-runtime.md), or [Invariants](../02-invariants.md). If a beat seems to need behavior the rest of the book does not authorize, that is a bug to report — not permission to extend the interface.
