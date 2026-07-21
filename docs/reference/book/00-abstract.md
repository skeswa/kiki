# Abstract

Solving a problem has never been a straight line. You chase a lead, dig in, surface with a better question, and change course. Coding agents speed this up and make the shape of the work visible sooner — and that shape is usually a tree. So why do our tools still think in straight lines?

A dull knife makes rougher cuts, and eventually changes what you cook. Dull tools do the same to engineering. Today, switching between lines of work is expensive: you stop the actual work to remember where things were, rebuild context for an agent, name half-finished changes, and clean up stale bookkeeping. The problem has not become more interesting. It has become more expensive to think about.

None of this is hypothetical. Push agents hard enough and you end up building the workflow by hand: a jj workspace for each line of work, a tmux session for each workspace, an agent alive in each session, a bookmark naming each chain of changes. It works. It also leaks — you forget which workspace holds what, you cannot see which agent is stuck, standing up the next line of work is a ritual, keeping ten of them current against a moving trunk is a chore, and `jj log` becomes a scroll through every chain to find your own. The workflow is worth keeping. The bookkeeping is not.

kiki exists to remove that friction — the friction that quietly teaches engineers to work one tidy line at a time: one terminal, one agent, one branch of thought. kiki gives the real tree of work a shape the tools can understand.

Its unit is a **thread**: one line of work with its own jj workspace, tmux session, agent session, and place in the revision graph. A thread's live tip is whatever revision its workspace is on — jj calls that `@`. Its bookmark is a saved checkpoint, like a bookmark left between pages: useful for finding your place later, distinct from the page you are on now. A thread can follow another thread. When the parent changes, jj may rewrite the child's history in the repository immediately; kiki waits for a safe moment — the child's agent between actions — before changing the child's files and telling its agent what happened. When the parent grows a new commit that jj cannot know the child should build on, kiki rebases the child's own straight chain of commits at that same safe moment.

The goal is not to hide `jj`, `tmux`, `gh`, or the agent harness. They stay the tools underneath. kiki is the layer that keeps several lines of work alive at once, so the human does not have to hold the whole tree in their head.

This book defines the contract for that layer: the vocabulary, the rules, and the machinery that keep it honest.
