# 0007 — Starting schema and config-loader code before policy.yaml is complete

**Date:** 2026-08-04
**Status:** Accepted
**Touches invariants:** §2.6 (scope creep is a decision, not a drift), §9

## The change

`ledger/schema.py` and a new top-level `config/` package are written while
`policy.yaml` still has 12 `REQUIRED` fields and every value in
`tax/FY2027.yaml` is `UNVERIFIED`.

§9 says: *"First task, before any code: fill in `policy.yaml` and
`tax/FY2027.yaml`."* On a literal reading, this is out of order. Recording it
so it is a decision rather than a drift.

## The reasoning

The remaining config work is blocked on inputs this repo cannot produce:
household decisions, and network access to ato.gov.au that the environment
denies ([0002](0002-tax-values-unverified.md)). Waiting is not a plan.

The question is which code, if any, is safe to write while blocked. The test
applied: **could any answer the household gives invalidate this code?**

- `ledger/schema.py` — no. §4 specifies the transaction contract completely
  and independently of any preference. `owner` is an enum of three values,
  `amount` is a Decimal and never a float, `is_transfer` is a bool. None of
  that moves when a risk premium is chosen.
- `config/` loader — no. It validates structure and enforces gates. It reads
  whatever values are present and refuses to hand out the ones that are not
  set. Filling in `policy.yaml` exercises it; it does not rewrite it.

What is deliberately *not* written:

- **`ledger/ingest.py`** — needs the real column layouts of real bank
  exports. A parser for CSVs nobody has seen would be fiction, and the same
  reasoning already keeps `ledger/rules.yaml` free of invented merchant
  patterns.
- **`engine/allocation.py`** and the rest of the waterfall — this is exactly
  what §9 is protecting. The waterfall encodes preferences, and writing it
  before the preferences are stated means guessing them in code, where the
  guess is much harder to see than a `REQUIRED` sentinel in a YAML file.

The positive case: `policy.reporting.block_on_unverified_tax_values: true` is
currently aspirational. Nothing reads it, so §2.4's promise that unverified
values are surfaced rather than used is enforced only by whoever remembers.
The loader turns that into a raised exception and a failing test. Given the
tax file is *entirely* unverified, that gate is the single most load-bearing
piece of code in the repo right now.

§9 also says *"prefer adding a test over adding a feature."* This is closer to
a test of the invariants than to a feature.

## What would have to be true to reverse it

If writing the schema now turns out to have pre-committed a data-model
decision that should have been the household's, delete it and start from the
filled config. The schema is small and has no dependents yet, so the cost of
being wrong is a few hundred lines — deliberately, which is why the loader and
schema were chosen and `ingest.py` was not.

The boundary holds only while `engine/` stays empty. The moment allocation
logic is written against unset policy values, this record no longer covers it
and §9 applies with full force.

## Note on layout

`config/` is not in the §3 layout. It is needed because §2.2 forbids `engine/`
from reading files, so something outside both `engine/` and `ledger/` must
turn YAML into values. Flagged rather than resolved silently, same as
`accounts.yaml` in [0001](0001-policy-values-pending.md).
