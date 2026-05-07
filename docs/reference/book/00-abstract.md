# Abstract

Solving a problem has never been linear. You follow a lead, dive into it, surface with a better question, and change course. Agents introduce speed and vigor that help to uncover the shape of the work sooner, and that shape is usually a tree. Why, then, do our tools still mostly think in lines?

A dull knife makes for rougher chops, and might ultimately change what you cook. The current tools of the trade affect you similarly when the work asks you to switch context quickly: they make agility expensive. You pause the actual engineering to remember what you were doing, reconstruct context for a new agent, describe revisions, name work in progress, and keep bookkeeping from going stale. The problem has not become more interesting. It has become more expensive to think about.

kiki is designed to help an engineer do their best work and pursue their loftiest ideas by removing the obstructive friction that makes ambitious work feel impractical. That friction encourages a quaint fiction: that engineering should proceed as one tidy line of work, one terminal, one agent, one branch of thought at a time. kiki gives the real tree of work a shape the tools can understand.

Its unit is a **thread**: a line of work with its own jj workspace, tmux session, agent session, bookmark, transcript, and place in the revision graph. A thread can follow another thread. When the parent changes, kiki rebases the child at a safe boundary and tells the agent what changed before it continues.

The goal is not to hide `jj`, `tmux`, `gh`, or the agent harness. They remain the tools underneath. kiki is the layer that lets several lines of work stay alive at once without asking the human to keep the whole state of the tree in their head.

This reference defines the contract for that layer: the vocabulary, the invariants, and the mechanisms that keep the model honest.
