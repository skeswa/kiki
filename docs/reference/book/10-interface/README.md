# Interface

This chapter covers what a person sees and touches when using kiki.

Kiki's [threads](../appendix-a-glossary.md#thread) are viewed through a [Herdr](../appendix-a-glossary.md#herdr) client attached to kiki's [dedicated Herdr server](../appendix-a-glossary.md#dedicated-herdr-server). Herdr is the [terminal multiplexer](../appendix-a-glossary.md#ext-terminal-multiplexer) kiki uses: the program that hosts the terminals. The drawing work is split in two:

- Herdr draws [panes](../appendix-a-glossary.md#ext-pane), [tabs](../appendix-a-glossary.md#ext-tab), and its native sidebar.
- Kiki publishes a label and tokens into that sidebar (see [Herdr sidebar projection](../appendix-a-glossary.md#herdr-sidebar-projection)). Kiki draws only the [overlay](../appendix-a-glossary.md#overlay-tui), approval cards, and an optional Stack pane (the [`ui` role pane](../appendix-a-glossary.md#ui-role-pane)).

Some of these surfaces belong to the [acceptance slice](../appendix-a-glossary.md#acceptance-slice) and some are [v1.x polish](../appendix-a-glossary.md#v1-x-polish). Which is which is recorded once, in [Orientation](../01-orientation.md).

The two documents here are the v1 contract for each surface when it ships:

1. [Specification](spec.md) — the rules for every surface. It covers:
   - the vocabulary;
   - the split between native Herdr UI and custom kiki UI;
   - glyphs (the small symbols on screen) and wireframes (sketches of each screen);
   - keymaps (which key does what);
   - [toasts](../appendix-a-glossary.md#toast) (short pop-up messages) and notifications;
   - mouse behavior;
   - fallbacks;
   - the configuration the surfaces read.
2. [Storyboard](storyboard.md) — one developer's end-to-end story. The developer ports an iOS app to Android, with a docs repo and a marketing-site fix along the way. The story exercises every branching, merging, and abandoning pattern the rest of the book commits to.

The specification is the rulebook; the storyboard is the movie. When they disagree, the specification wins, and the storyboard has the bug.

The storyboard invents nothing: no new commands, flags, output strings, glyphs, or screen elements. Every beat in it (every step of the story) traces back to one of these:

- [Threads](../03-threads.md)
- [Cascade](../05-cascade.md)
- [Publishing](../07-publishing.md)
- [Commands](../09-commands.md)
- [spec.md](spec.md)
- [Terminal runtime](../13-architecture/terminal-runtime.md)
- [Invariants](../02-invariants.md)

If a beat seems to need behavior the rest of the book does not authorize, that is a bug to report. It is not permission to extend the interface.
