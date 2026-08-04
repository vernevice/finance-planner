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
| **Blocked on** | No mortgage rate, 12 undecided policy fields, 2 gated tax values |

`ledger/` and `config/` exist and are tested. `engine/` is still empty by
design: the §5 waterfall encodes preferences that `policy.yaml` has not
stated yet, and writing it early means guessing them in code, where a guess
is far harder to spot than a `REQUIRED` sentinel in YAML
([0007](docs/decisions/0007-code-before-config-complete.md)).

### Settled

- **Buffer: 3 months** of expenses — [0005](docs/decisions/0005-buffer-three-months.md).
- **Risk premium: 250bps** over the mortgage rate, provisional within a stated
  200–300 range — [0006](docs/decisions/0006-risk-premium-250bps.md).
- **Raw data stays out of git** — [0004](docs/decisions/0004-raw-data-not-committed.md).
- **13 of 15 FY2027 tax values verified** against ATO pages by the household
  on 2026-08-04 — [0002](docs/decisions/0002-tax-values-unverified.md).

### What is still blocking

1. **`accounts.yaml` has no accounts**, so there is no mortgage rate — and
   §5.4 compares against `mortgage_rate + risk_premium_bps`. The premium is
   set; the thing it is a premium *over* is not.
2. **`policy.yaml` is still partly unfilled.** `super.hurdle_bps`,
   `investment.expected_return`, and `ownership.optimise_for_marginal_rate`
   are the consequential ones. Full list in
   [0001](docs/decisions/0001-policy-values-pending.md).
3. **Two tax values remain gated**, both deliberately:
   `super.maximum_contribution_base` (quarterly or annual — unresolved, and a
   4× error in employer SG if read wrong) and
   `super.carry_forward.total_super_balance_threshold` (no figure captured;
   `policy.super.use_carry_forward` cannot be acted on without it).

Also note: with raw data out of git, §2.3's append-only invariant is
convention rather than something git enforces, so an edit to a raw export
would leave no trace. Worth knowing before Phase 0's ±2% reconciliation is
treated as evidence of anything.

---

## Layout

```
policy.yaml       preferences and constraints          ← 14 fields REQUIRED
accounts.yaml     account_id → metadata, loan rate     ← unfilled
tax/FY2027.yaml   brackets, caps, CGT                  ← 13 verified, 2 gated
config/           loads and gates the above
data/raw/         bank exports, never edited           ← gitignored
data/snapshots/   computed monthly snapshots           ← gitignored
ledger/           facts: schema.py, rules.yaml         ← no ingest.py yet
engine/           pure functions — no I/O, no network  ← empty, by design
tests/            47 tests, all passing
docs/decisions/   one record per policy change
docs/monthly/     the monthly review output
```

The three-layer split is hard: `ledger/` holds facts and no judgement,
`engine/` holds pure functions that never touch a file or a network, and
`policy.yaml` + `tax/` hold config. Nothing crosses. `config/` is the I/O
boundary that turns YAML into values — it exists because `engine/` is
forbidden from reading files, and it is an addition to the §3 layout
([0007](docs/decisions/0007-code-before-config-complete.md)).

## Running the tests

```sh
python3 -m pytest
```

Use `python3 -m pytest`, not bare `pytest` — on some setups the `pytest` on
PATH is an isolated tool install with its own interpreter that cannot see
PyYAML.

The suite is mostly the invariants written as executable checks: floats
rejected as amounts, `owner` never inferred, the ledger offering no delete,
`UNVERIFIED` tax values raising instead of returning, `REQUIRED` policy fields
raising instead of returning the string, and every `VERIFIED` value carrying a
source, a date and a verifier.

Several tests pin the *current* state — which two tax values are still gated,
and that the repo cannot yet produce a recommendation. These are expected to
fail as config gets filled in; a failure there means progress, not a bug. Two
already have: verifying the tax table broke the tests asserting it was
entirely unverified, which is what they were for.

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

1. Fill in `accounts.yaml`, including the current mortgage rate — §5.4 has
   nothing to compare against without it.
2. Close out the two remaining tax values (see above); both have their
   `source_url` recorded.
3. Fill in the remaining 12 `policy.yaml` fields, one decision record per
   material choice.
4. Then `ledger/ingest.py`, once real bank exports exist to write it against.
   It is deliberately absent: a parser for CSVs nobody has seen would be
   fiction.
5. Then `engine/` and the §5 waterfall — not before, since the waterfall
   encodes the preferences that step 3 sets.

`python3 -c "from config.loader import Config; print(*Config.load('.').blockers(), sep=chr(10))"`
prints exactly what is standing in the way at any point.
