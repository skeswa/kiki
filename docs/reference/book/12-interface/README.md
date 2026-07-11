# Interface

The TUI is v1.x polish, not acceptance slice (see [Orientation](../01-orientation.md)). The two documents here are the v1 contract if it ships:

1. [Specification](spec.md) — vocabulary, glyph language, wireframes, keymaps, toast triggers, mouse, degradation, and the `[ui]` configuration surface.
2. [Storyboard](storyboard.md) — a worked end-to-end scenario that walks one developer porting an iOS app to Android (with a docs repo and a marketing-site copyright bump along the way) through every branching, merging, and abandoning pattern the rest of the book commits to.

The specification is normative; the storyboard is illustrative. When they disagree, the specification wins, and the storyboard is the bug.

The storyboard introduces no new commands, flags, output strings, glyphs, or screen elements. Every beat in it grounds out in [Threads](../05-threads.md), [Cascade](../07-cascade.md), [Publishing](../09-publishing.md), [Commands](../11-commands.md), [spec.md](spec.md), or [Invariants](../04-invariants.md). If a beat in the storyboard appears to require behavior the rest of the book does not authorize, that is a finding to surface, not a license to extend the surface here.
