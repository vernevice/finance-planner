# 0004 — Raw exports and snapshots are gitignored by default

**Date:** 2026-08-04
**Status:** Accepted — confirmed by the household 2026-08-04
**Touches invariants:** §2.3 (the ledger is append-only)

## The change

`.gitignore` excludes `data/raw/**/*.csv`, `data/raw/**/*.ofx` and
`data/snapshots/*.json` by default. The directories are tracked (via
`.gitkeep`) but their contents are not.

## The reasoning

This one cuts against the brief slightly, so it is written down rather than
assumed either way.

§2.3 says the ledger is append-only and raw exports are never edited.
The natural enforcement mechanism for that is git: history makes an edit
visible and a deletion recoverable. That argues for committing the data.

Against: `data/raw/` holds unredacted bank exports — full transaction
descriptions, balances, both incomes — and `data/snapshots/` holds derived
income and net position. Committing them to a repository with a remote is an
outward-facing action that cannot be undone by a later commit; the data stays
in history, and in any fork, clone, or cached view.

The two failure modes are not symmetric. Ignoring data that should have been
committed is recoverable at any time by removing two lines. Publishing bank
statements that should not have been is not recoverable at all. So the
default fails safe, and the decision is handed to the household rather than
made silently by a scaffold.

## What would have to be true to reverse it

Confirm the remote is private and will stay private, and that everyone with
access to the repository — now and after any future collaborator is added —
is someone both people are content to show their bank statements to. Then
delete the ignore lines and commit the data.

If the answer is "private for now but not certainly forever", the better
options are a local-only data directory outside the repo, or committing
snapshots (aggregates) while continuing to ignore raw exports. Snapshots
carry much of the audit value at a fraction of the disclosure.

## Consequence while this stands

§2.3 is currently a convention rather than something git enforces. Until
this is resolved, an edit to a raw export would leave no trace. Worth
knowing before Phase 0's ±2% reconciliation is used as evidence of anything.
