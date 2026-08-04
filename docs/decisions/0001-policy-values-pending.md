# 0001 — policy.yaml scaffolded with no values set

**Date:** 2026-08-04
**Status:** Open — blocks Phase 1
**Touches invariants:** §2.6 (scope creep is a decision)

## The change

`policy.yaml` has been created with its full field set, but every field
representing a household decision is set to the sentinel `REQUIRED` rather
than to a default. No numbers have been chosen.

## The reasoning

§9 names this directly: *"If the user can't state their risk premium and
buffer size, that is the real blocker and it isn't a software one."*

Two fields in particular cannot be defaulted without quietly deciding the
whole model:

- **`buffer.months`** sits at the top of the waterfall and has first claim on
  all surplus. Set it to 3 and the engine will push money into investment that
  a cautious household wanted in reserve; set it to 12 and the household may
  never fund anything else. It is a statement about job-loss risk, and nothing
  in a repository knows that.

- **`investment.risk_premium_bps`** is the number the entire §5.4 decision
  turns on. A dollar in the offset returns the mortgage rate risk-free,
  tax-free and liquid; a dollar in the market returns none of those with
  certainty. The premium is the price of giving that up. Defaulting it to a
  conventional-looking 300bps would produce recommendations that look
  reasoned and are actually arbitrary.

A plausible default is more dangerous here than a missing value, because it
survives review. `REQUIRED` fails loudly.

A related judgement call: `owners.person_a.name` and the like are also marked
`REQUIRED`, even though they only affect narration. Leaving them unset keeps
a single rule — nothing in this file is inferred — rather than a rule with
exceptions that later have to be remembered.

## What would have to be true to reverse it

Populate the `REQUIRED` fields. Each material choice (buffer size, super
hurdle, risk premium, ownership tilt) should get its own decision record
recording *why* that number and not another — those records, not the values,
are what stop the same argument being re-run every time markets move (§6).

Defaulting a field instead would need an argument that the default is
genuinely uncontroversial for this household, which is a claim about them,
not about the software.

## Open questions

1. `buffer.basis` — all expenses, or non-discretionary only? This cannot be
   answered until `ledger/rules.yaml` has enough categories to make
   `essential: true` meaningful, so it may need to wait for Phase 0 data.
2. `investment.expected_return` — §7 Phase 2 refers to *"the user's existing
   factor-model work"*. That work is not in this repo. Whether its output
   should be imported, referenced, or restated here is unresolved.
3. Whether `person_a` / `person_b` map to fixed individuals for the life of
   the repo. Snapshots are append-only, so if the mapping ever changes, old
   snapshots become unreadable. Recommend fixing it now and never reusing it.
