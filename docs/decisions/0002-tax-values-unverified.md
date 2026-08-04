# 0002 — FY2027 tax values recorded UNVERIFIED; ATO unreachable

**Date:** 2026-08-04
**Status:** Mostly resolved — 13 of 15 verified, 2 still gated
**Touches invariants:** §2.4 (tax values are config, verified, never from memory)

> **Update 2026-08-04.** Resolved by the second route this record anticipated:
> the household opened the ATO pages and confirmed the figures. 13 of 15
> values are now `VERIFIED`, stamped `verified_by: household` with
> `verified_via` recording that a person read the source rather than the
> model. Two remain deliberately gated:
>
> * `super.maximum_contribution_base` — the figure was not confirmed and the
>   **period** is still unresolved. Renamed from
>   `maximum_contribution_base_quarterly`, because the old name presupposed
>   the answer to the open question.
> * `super.carry_forward.total_super_balance_threshold` — no figure captured,
>   and still no candidate.
>
> Per-value verification worked as designed: `config/loader.py` raises per
> value, so the 13 are usable while the 2 stay blocked. The network egress
> block described below is unchanged — it is simply no longer the binding
> constraint.

## The change

`tax/FY2027.yaml` has been created covering the 2026–27 income year. Every
figure in it carries `status: UNVERIFIED` and `value: null`. Candidate figures
are recorded in a separate `candidate:` field, each stamped with where it came
from.

`policy.reporting.block_on_unverified_tax_values` is set to `true`, so a
correctly-implemented engine will refuse to emit a recommendation rather than
fall back to a candidate.

## The reasoning

§2.4 requires each value to be stamped with the source and the date it was
verified against ATO guidance. Verification was attempted on 2026-08-04 and
failed: `www.ato.gov.au:443` is blocked by this session's network egress
policy, which answered 403 to CONNECT. Both the public pages and the ATO's
public content API were unreachable. No ATO page was read.

What *is* available is search-engine summaries of those pages. That is
strictly better than model memory but it is not verification: a summary can
conflate income years, can quote a superseded figure, and cannot be audited
later. Recording those figures in `value:` would satisfy the letter of the
invariant while defeating its purpose — the file would look verified.

Hence the split. `candidate:` is a lead for a human verifier; `value:` stays
null until a person reads the source. The distinction is load-bearing and
should not be collapsed for convenience.

Three items deserve particular attention when someone does verify:

- **`super.maximum_contribution_base_quarterly`** — the figure found (270,830)
  was not qualified as quarterly or annual. The ATO has historically published
  it per quarter. Reading a quarterly cap as annual understates employer SG
  roughly fourfold for a high earner, which flows straight into the §5.2 cap
  headroom calculation.
- **`super.carry_forward.total_super_balance_threshold`** — no candidate is
  recorded at all, because none was confirmed. This one gates a real
  contribution decision, so a remembered number was not worth the risk.
- **`income_tax.medicare_levy`** and **`super.contributions_tax_rate`** — the
  candidates are marked `MODEL_MEMORY`, which §2.4 forbids relying on. They
  are the weakest lines in the file despite looking like the most obvious.

## What would have to be true to reverse it

Someone with network access to ato.gov.au opens each `source_url`, confirms
the figure applies to 2026–27, and fills in `value`, `status: VERIFIED`,
`verified_on`, `verified_by`. Verification is per-value, not per-file: a
partly-verified file is fine and better than an all-or-nothing gate.

Alternatives if the egress block is permanent: verify from a downloaded ATO
publication committed to the repo, or accept a registered tax agent's written
figures as the source of record — stamping `verified_by` accordingly. Either
is a real source. A search summary is not.

`block_on_unverified_tax_values: false` should only ever be set with its own
decision record explaining why acting on unconfirmed thresholds is acceptable
that month.

## Note on scope

FY2027 runs to 2027-06-30. At rollover, create `tax/FY2028.yaml` — do not edit
this file. The lowest marginal rate is understood to change again on
2027-07-01, which is precisely the kind of thing an in-place edit would
silently backdate across every stored snapshot.
