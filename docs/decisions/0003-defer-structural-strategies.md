# 0003 — Debt recycling, investment property and trusts deferred to Phase 5

**Date:** 2026-08-04
**Status:** Accepted (deferral)
**Touches invariants:** §2.6 (scope creep is a decision, not a drift)

## The change

Debt recycling, investment property, and trusts or second entities are
recorded as out of scope until Phase 5. They are not modelled in
`policy.yaml`, not represented in `tax/FY2027.yaml`, and the engine will not
consider them. §5 requires this deferral to be logged with reasoning; this is
that log.

## The reasoning

§5 places these out of scope explicitly, and §7 makes Phase 5 conditional on
professional advice. Three reasons the deferral is right on the merits, not
just because the brief says so:

1. **They depend on a surplus figure that is not yet trustworthy.** Phase 0's
   exit criterion is two consecutive months of computed surplus matching
   reality within 2%. Until that holds, every downstream number inherits an
   unknown error. Structural strategies are the most leveraged use of that
   number and so the worst place to spend it early.

2. **They are hard to unwind.** A misallocated month of offset-versus-invest
   is corrected the following month. A badly-executed debt recycle mixes
   deductible and non-deductible borrowings in one loan, and the resulting
   apportionment problem can persist for the life of the loan. The cost of
   being early is asymmetric.

3. **Deductibility is a question of tax law, not arithmetic.** Whether
   interest on recycled debt is deductible turns on the use to which the
   borrowed funds are put, and on facts about the loan structure that this
   repo does not model. It is not something to be inferred from a yield
   comparison, and §10 already requires a licensed adviser.

The engine is expected to be *silent* about these, not to reason about them
and decline. A recommendation that gestures at debt recycling while claiming
to be out of scope is worse than no mention at all.

## What would have to be true to reverse it

All of:

- Phase 0 exit met — two consecutive months within 2% surplus tolerance.
- Phase 1 exit met — the household agrees with the engine's splits, or
  disagrees for reasons expressible as a policy change.
- Phase 2 exit met — the deterministic three-line projection is trusted.
- A session with a licensed adviser, with their position on deductibility
  recorded here and reflected in `tax/`.

Any one of these missing means the deferral stands. Reversing it early is
itself a decision requiring a record (§2.6) — the point of this file is that
"we may as well look at debt recycling while we're here" is a scope change,
not a small step.

## Related

Interest deductibility would also make `purpose` on the mortgage account in
`accounts.yaml` load-bearing rather than descriptive, and would break the §8
simplification that the household is one pot for cashflow purposes. Both are
reasons to keep it firmly on the far side of the phase boundary.
