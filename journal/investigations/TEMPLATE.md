# State the question or finding in plain language

Date: YYYY-MM-DD, with timezone when it matters  
Type: Investigation / Outcome  
Topic: Name the topic  
Related plan or decision: Link, if any

## Summary

Give the question and main finding in a few sentences. “We do not yet know”
is a valid conclusion. Separate measurements from explanations or guesses.

## Context

Explain what prompted the work and enough background for a new reader.

## Findings

Describe what the evidence establishes, its scope, and remaining uncertainty.
Pin the source revision, executable version, and environment where relevant;
distinguish source inspection from executed tests.

## Conclusion and follow-up

State what follows and what remains to do. A recommendation is not a decided
choice; link to a separate decision record when one exists. If this changes
an earlier conclusion, link both records.

## Evidence and reproduction

Link the commands, scripts, results, and measurements needed to assess or
repeat the work. Keep compact results under `journal/evidence/<topic>/<run>/`.
Describe side effects and cleanup for executable probes. Leave credentials,
private environment files, and verbose temporary output out of the journal.
