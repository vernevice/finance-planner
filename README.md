# finance-planner

A medium-term (5–10 year) household financial planning workflow for an
Australian dual-income household with an owner-occupied mortgage and offset
account. It answers one question, once a month:

> What percentage of this month's surplus should go to mortgage offset,
> superannuation, and investment — and why?

Decision support, not a budgeting app, not a dashboard, not a trading system.

**[`CLAUDE.md`](CLAUDE.md) is the contract.** Read it before changing anything
here. This README is orientation only; where the two disagree, `CLAUDE.md`
wins.

**This is not financial advice.** Australian tax specifics must be confirmed
against current ATO guidance, and the structural phases warrant a licensed
adviser.

---

## Current state — Phase 0, not started

| | |
|---|---|
| **Phase** | 0 — Ledger and surplus |
| **Exit criterion** | Two consecutive months where computed surplus matches reality within 2% |
| **Blocked on** | `policy.yaml` and `tax/FY2027.yaml` are scaffolded but unfilled |

No engine code exists yet, by design: §9 puts config before code, and both
config files are still incomplete.

### Settled

- **Buffer: 3 months** of expenses — [0005](docs/decisions/0005-buffer-three-months.md).
- **Risk premium: 250bps** over the mortgage rate, provisional within a stated
  200–300 range — [0006](docs/decisions/0006-risk-premium-250bps.md).
- **Raw data stays out of git** — [0004](docs/decisions/0004-raw-data-not-committed.md).

### What is still blocking

1. **Every value in `tax/FY2027.yaml` is `UNVERIFIED`.** `ato.gov.au` was
   unreachable from the environment where this was scaffolded, so nothing
   could be checked against source. Needs a person on a network that can
   reach it — [0002](docs/decisions/0002-tax-values-unverified.md).
2. **`policy.yaml` is still partly unfilled.** `super.hurdle_bps`,
   `investment.expected_return`, and `ownership.optimise_for_marginal_rate`
   are the consequential ones. Full list in
   [0001](docs/decisions/0001-policy-values-pending.md).
3. **`accounts.yaml` has no accounts**, so there is no mortgage rate — and
   §5.4 compares against `mortgage_rate + risk_premium_bps`. The premium is
   set; the thing it is a premium *over* is not.

Also note: with raw data out of git, §2.3's append-only invariant is
convention rather than something git enforces, so an edit to a raw export
would leave no trace. Worth knowing before Phase 0's ±2% reconciliation is
treated as evidence of anything.

---

## Layout

```
policy.yaml       preferences and constraints          ← unfilled
accounts.yaml     account_id → metadata, loan rate     ← unfilled
tax/FY2027.yaml   brackets, caps, CGT                  ← UNVERIFIED
data/raw/         bank exports, never edited           ← gitignored
data/snapshots/   computed monthly snapshots           ← gitignored
ledger/           facts: schema, ingest, rules         ← rules.yaml only
engine/           pure functions — no I/O, no network  ← empty
tests/                                                 ← empty
docs/decisions/   one record per policy change
docs/monthly/     the monthly review output
```

The three-layer split is hard: `ledger/` holds facts and no judgement,
`engine/` holds pure functions that never touch a file or a network, and
`policy.yaml` + `tax/` hold config. Nothing crosses.

## The waterfall

Surplus is consumed strictly in order — buffer, then concessional super, then
offset, then investment. Offset is the default sink because a dollar there
returns the mortgage rate risk-free, tax-free and liquid, which on a post-tax
basis is a high bar for anything else to clear. Full definition in §5 of
`CLAUDE.md`.

Output is always a split **and** a written rationale, never a bare number.

## Two rules worth knowing before you touch this

**No arithmetic outside `engine/`.** Every dollar figure in every output comes
from a tested pure function. If a projection is being computed in prose,
that is a bug — write the function.

**No tax value from memory.** Caps and brackets live in `tax/FY<year>.yaml`,
stamped with source and verification date. An unverified value is marked
`UNVERIFIED` and surfaced in the output rather than quietly used.

## Decisions

`docs/decisions/` is the most valuable thing in this repo. Every change to
`policy.yaml` gets a record: what changed, why, and what would have to be true
to reverse it. It exists so the same argument is not re-run every time markets
move.

---

## Next steps

1. Fill in `policy.yaml`, one decision record per material choice.
2. Fill in `accounts.yaml`, including the current mortgage rate.
3. Verify `tax/FY2027.yaml` against ATO guidance from a network that can
   reach it.
4. Decide the raw-data question in
   [0004](docs/decisions/0004-raw-data-not-committed.md).
5. Only then start Phase 0 code: `ledger/schema.py`, `ledger/ingest.py`, and a
   config loader that enforces the `UNVERIFIED` gate — with tests first.
