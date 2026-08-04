# Finance Planner — Project Brief

Read this file in full before doing anything. It is the contract for this project.

---

## 1. Purpose

A medium-term (5–10 year) household financial planning workflow. It answers one question:

> **What percentage of this month's surplus should go to mortgage offset, superannuation, and investment — and why?**

It is a decision-support tool with a monthly cadence. It is not a budgeting app, not a dashboard, and not a trading system.

Jurisdiction: Australia. Household is dual-income. Owner-occupied mortgage with an offset account into which both incomes are deposited.

---

## 2. Invariants

These are not up for renegotiation without an explicit decision record (see §6).

1. **The LLM never does arithmetic.** Every dollar figure in any output must come from a tested pure function in `engine/`. Claude's role is transaction classification, narration of results, and challenging assumptions. If you find yourself computing a projection in prose, stop and write the function instead.
2. **Three layers, hard-separated.** `ledger/` (facts), `engine/` (pure functions), `policy.yaml` + `tax/` (config). Nothing in `engine/` reads a file or hits a network. Nothing in `ledger/` contains judgement.
3. **The ledger is append-only.** Raw exports are never edited. Corrections are adjustment entries, not mutations.
4. **Tax and threshold values are config, never hardcoded.** They live in `tax/FY<year>.yaml`, are stamped with the source and date they were verified, and are re-verified against ATO guidance at each financial-year rollover. Never assert a cap or bracket from model memory — if a value is unverified, mark it `UNVERIFIED` and surface it in the output.
5. **`owner` is a first-class field on every income line.** Cashflow rolls up to household; tax, super, and asset-ownership decisions drop back to individual.
6. **Scope creep is a decision, not a drift.** If a phase's exit criteria aren't met, the next phase does not start.

---

## 3. Repo layout

```
finance-planner/
├── CLAUDE.md              # this file
├── policy.yaml            # user's stated preferences and constraints
├── tax/
│   └── FY2027.yaml        # brackets, caps, CGT rules — with verification stamps
├── data/
│   ├── raw/YYYY-MM/       # bank CSV exports, never edited
│   └── snapshots/         # computed monthly snapshot.json, append-only
├── ledger/
│   ├── schema.py          # transaction + account models
│   ├── ingest.py          # CSV → normalised transactions
│   └── rules.yaml         # merchant/description → category, owner, is_transfer
├── engine/
│   ├── cashflow.py        # surplus calculation
│   ├── allocation.py      # the waterfall (§5)
│   ├── projection.py      # deterministic paths (Phase 2)
│   └── tax.py             # after-tax return helpers
├── tests/
├── docs/
│   ├── decisions/         # NNNN-short-title.md, one per policy change
│   └── monthly/           # YYYY-MM.md, the monthly review output
└── README.md
```

---

## 4. Data contracts

### Transaction (normalised)

| Field | Type | Notes |
|---|---|---|
| `date` | date | Transaction date, not settlement |
| `account_id` | str | Stable key, mapped in `accounts.yaml` |
| `amount` | Decimal | Signed. **Never float.** |
| `description` | str | Raw, unmodified |
| `owner` | enum | `person_a` \| `person_b` \| `joint` |
| `category` | str | From `rules.yaml`; `UNCLASSIFIED` until resolved |
| `is_transfer` | bool | Internal movement — excluded from income and expenses |

`is_transfer` is the highest-risk field. Offset accounts generate heavy internal movement; misclassifying it inflates both income and expenses and silently corrupts surplus.

### Snapshot (monthly output)

```
period, account_balances[], mortgage_principal, offset_balance,
household_income{by_owner}, expenses, surplus, net_position
```

### Portfolio API (Phase 3, read-only, one-way)

`GET /positions` → `[{symbol, units, market_value, cost_base, acquisition_date}]`

Cost base and acquisition date are mandatory — CGT discount eligibility changes the after-tax return and is invisible without them. The planner never sends orders. The tracker never plans.

---

## 5. The allocation waterfall

Evaluated strictly in order. Each step consumes surplus until its condition is satisfied.

1. **Buffer** — top up offset to `policy.buffer_months` of expenses. Non-negotiable, first claim on all surplus.
2. **Concessional super** — per person, up to the cap (incl. carry-forward), *only if* the marginal tax saving exceeds the hurdle rate. Cap and brackets from `tax/`.
3. **Offset** — the default sink. The hurdle rate: a dollar in offset returns the mortgage rate, risk-free, tax-free, liquid. On a post-tax basis this is a high bar.
4. **Investment** — only the residual where expected after-tax return exceeds `mortgage_rate + policy.risk_premium_bps`.

Output is a **split plus a written rationale**, never a bare number.

**Explicitly out of scope until Phase 5:** debt recycling, investment property, trusts or second entities. Log them in `docs/decisions/` as deferred, with reasoning.

---

## 6. Decision records

Every change to `policy.yaml` is a commit accompanied by `docs/decisions/NNNN-title.md` containing: the change, the reasoning, what would have to be true to reverse it. This log is the most valuable artefact in the repo — it prevents re-litigating the same decision every time markets move.

---

## 7. Phases and exit criteria

**Phase 0 — Ledger and surplus.** Manual CSV drop, no connectors or scraping. Deterministic rules first; LLM classifies only the residual and writes results back to `rules.yaml` so no merchant is asked about twice.
*Exit:* two consecutive months where computed surplus matches reality within 2%. Everything downstream inherits this error — do not proceed early.

**Phase 1 — Allocation rule.** Implement §5. Config-driven, fully tested.
*Exit:* engine produces a split for the last three months' snapshots that the user agrees with, or disagrees with for reasons that are expressible as a policy change.

**Phase 2 — Projection.** Deterministic 5- and 10-year paths for three strategies: 100% offset, 100% invest, current policy. Net position and mortgage-free date.
*Exit:* the three-line chart is boring and trusted. Only then add stochastic modelling — and use the user's existing factor-model work, not a lognormal hand-wave. The useful output is the 10th-percentile spread, not the median.

**Phase 3 — Portfolio API integration.** Narrow read-only contract per §4.

**Phase 4 — Monthly ritual.** A skill that ingests the new snapshot and outputs: what changed, drift from policy, recommended split, and one challenge question. Target: 15 minutes, monthly. This is the actual product.

**Phase 5 — Structural (deferred).** Debt recycling and deductibility. Requires professional advice before implementation.

---

## 8. Household modelling

Both incomes land in the same offset, so for cashflow the household is one pot — a dollar is a dollar. Three decisions are individual, not household: asset ownership (driven by differing marginal rates), super contributions (individual caps and balances), and deductibility if debt recycling is ever adopted.

The engine takes `household_surplus` and returns **per-person** allocations.

Where marginal rates differ materially, the optimiser will consistently favour holding assets in the lower earner's name. That is mathematically correct and may be the wrong answer for other reasons. Any constraint on this belongs in `policy.yaml` as an explicit rule — the engine must not surprise the user here.

---

## 9. Starting a session

Say what phase you're in and what the exit criterion is. Then:

- Confirm which invariants (§2) the requested work touches.
- If the work would breach one, say so and propose a decision record instead of proceeding.
- Prefer adding a test over adding a feature.
- Flag any tax or threshold value you cannot verify rather than asserting it.

**First task, before any code:** fill in `policy.yaml` and `tax/FY2027.yaml`. If the user can't state their risk premium and buffer size, that is the real blocker and it isn't a software one.

---

## 10. Standing caveat

This is not financial advice. Australian specifics — super caps, CGT discount, deductibility of recycled debt — must be confirmed against current ATO guidance, and the structural phases warrant a session with a licensed adviser before implementation.
