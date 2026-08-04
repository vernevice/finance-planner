# 0006 — Investment risk premium set to 250bps

**Date:** 2026-08-04
**Status:** Accepted — exact figure provisional
**Supersedes:** the `REQUIRED` sentinel in [0001](0001-policy-values-pending.md)

## The change

`policy.investment.risk_premium_bps`: `REQUIRED` → `250`.

A dollar goes to investment rather than the offset only where expected
after-tax return exceeds `mortgage_rate + 2.50%` (§5.4).

## The reasoning

The household stated a range of 200–300bps rather than a single figure. 250 is
the midpoint. This is the one number in the file that was not stated exactly,
and it is recorded as provisional for that reason — the range, not the
midpoint, is what was actually decided.

The substance of the choice: a conventional equity risk premium charged for
giving up a return that is risk-free, tax-free and liquid. It rejects the
position that any expected outperformance justifies market risk, while not
treating the offset's certainty as so valuable that investment never clears
the bar.

Worth being explicit about what this number has to beat, because §5.4 is a
harder test than it looks. The offset return is the mortgage rate, *after tax*
— there is no tax on interest not paid. An investment must clear the mortgage
rate plus 250bps on an **after-tax** basis, which for a higher-rate taxpayer
means a materially larger pre-tax return. On plausible mortgage rates this
sets a bar that a broad equity allocation does not obviously clear on expected
returns alone. That is the intended behaviour of the waterfall, not a fault in
it: §5.3 calls the offset the default sink precisely because it is hard to
beat.

## What would have to be true to reverse it

- **Narrowing within the range.** 200 vs 300 is not a rounding difference. At
  a plausible mortgage rate the 100bps gap is enough to flip the §5.4 test for
  a broad equity allocation. Settling on a specific figure should be the first
  revision to this record.
- **The mortgage is repaid, or the offset reaches the loan principal.** At
  that point the offset's marginal return is zero, the comparison in §5.4 no
  longer applies, and the premium is measuring against nothing.
  `offset.cap_at_principal` handles the mechanics; the premium itself would
  need rethinking.
- A change in the household's view of the liquidity value of offset funds —
  for example after the buffer question in
  [0005](0005-buffer-three-months.md) is revisited.

## Blocked dependency

This number cannot yet be *acted* on. §5.4 compares it against
`investment.expected_return`, which is still `REQUIRED`, and the comparison
runs through after-tax helpers that read `tax/FY2027.yaml` — where every value
is `UNVERIFIED` ([0002](0002-tax-values-unverified.md)). Setting the premium
resolves the preference, not the calculation.

§7 Phase 2 refers to the household's existing factor-model work as the source
for expected returns. That work is not in this repo, and whether it should be
imported or merely referenced is still open per
[0001](0001-policy-values-pending.md).
