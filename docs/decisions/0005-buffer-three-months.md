# 0005 — Buffer set to 3 months of expenses

**Date:** 2026-08-04
**Status:** Accepted
**Supersedes:** the `REQUIRED` sentinel in [0001](0001-policy-values-pending.md)

## The change

`policy.buffer.months`: `REQUIRED` → `3`.

## The reasoning

Stated by the household when asked. 3 months is the lean end of the common
3–12 range: it clears the offset's first claim on surplus quickly, which lets
more surplus reach the super and investment steps of the waterfall sooner.

The implicit view is that the household's income is unlikely to stop for
longer than a quarter — short job searches, or enough notice period and
redundancy entitlement to bridge the gap.

## What would have to be true to reverse it

Any of:

- **Both incomes are correlated.** §1 establishes a dual-income household with
  both salaries landing in the same offset. If both people work for the same
  employer, in the same industry, or in sectors that turn down together, the
  buffer is not covering two independent risks — it is covering one, and 3
  months of *household* expenses is roughly 1.5 months of real cover if both
  incomes stop. This is the most likely reason to revisit, and it is a
  question about their employment, not about the model.
- Income becomes variable — commission, bonus-weighted, contract, or
  self-employed.
- A large known capital cost appears within the horizon (renovation, car
  replacement, school fees), which should be funded separately rather than by
  quietly eroding the emergency buffer.
- Notice periods shorten or redundancy entitlements fall.

## Open dependency

`policy.buffer.basis` is still `REQUIRED`, and the dollar target is undefined
without it. The interaction matters more than usual at 3 months:

- `basis: all` → 3 months of every non-transfer outflow, discretionary
  included. The larger, more conservative reading.
- `basis: non_discretionary` → 3 months of essentials only. Combined with the
  leanest month count, this produces a genuinely thin buffer. It may still be
  right — discretionary spend really can be cut in an emergency — but the two
  lean choices compound, and that should be chosen deliberately rather than
  arrived at.

[0001](0001-policy-values-pending.md) notes this cannot be settled until
`ledger/rules.yaml` has enough categories flagged `essential: true` to make
the distinction meaningful. That is Phase 0 work.
