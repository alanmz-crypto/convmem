# Round 3 verification plan — source diversification

**Status:** **SHIPPED** on `main` @ `549f74d` via [PR #39](https://github.com/alanmz-crypto/convmem/pull/39) (squash of tip `5946d19`).
**PR:** [#39](https://github.com/alanmz-crypto/convmem/pull/39) (`fix/2026-07-16-source-diversity` @ `5946d19e5f589ebf146f22bff21187a6e3185ad1`)
**Parent:** `main` @ `950e830` (Round 2 trace)
**Architecture:** [CURSOR-architecture-round-3-source-diversity.md](CURSOR-architecture-round-3-source-diversity.md)
**Execution:** [CURSOR-execution-plan-round-3-source-diversity.md](CURSOR-execution-plan-round-3-source-diversity.md)

Process stays **light** (no Round-2 ack sprawl). This file is the single verification checklist + partner ledger for the tip.

---

## A — Tip and Round 1 / Round 2 invariants

| # | Check | PASS criteria |
|---|---|---|
| A1 | Tip SHA | `5946d19e5f589ebf146f22bff21187a6e3185ad1` |
| A2 | Parent | `git merge-base --is-ancestor origin/main HEAD` |
| A3 | Minority cap | `max(1, total_limit // 3)` still at evidence inject |
| A4 | `with ChromaStore` | still used for store access |
| A5 | Ledger tests | `tests/test_ledger_recent.py` zero meaningful regression vs main |
| A6 | Trace contract | `tests/test_ask_trace.py` green; schema `convmem.ask.trace.v1` |

```bash
git rev-parse HEAD
# expect: 5946d19e5f589ebf146f22bff21187a6e3185ad1
python3 -m unittest tests.test_ask_trace tests.test_ledger_recent -q
```

---

## B — ChatGPT locks (hermetic)

| # | Lock | PASS criteria | Primary test |
|---|---|---|---|
| B1 | Cardinality | units/evidence diversify `limit=top_k`; raw/hybrid `limit=fetch_k` | code review + B2/B3 paths |
| B2 | `results` vs citations | `results` = pre-diversity slice; citations may include refill id outside that slice | `test_results_pre_diversity_citations_may_refill` |
| B3 | Bounded `source_diversity` | `{max_per_source, dropped_items, dropped_items_total, truncated}`; `drop_reason: "source_cap"`; body-free | `_source_diversity_block` + ask() tests |
| B4 | Crowding fixture | pool `A,A,A,B,C,D` limit 5 → kept `A,A,B,C,D`; one dropped `A` | `test_crowding_fixture_refill` |
| B5 | Truncation lock | `source_diversity.truncated` ⇒ envelope `trace.truncated`; **not** `final_context.truncated` unless items list truncated | `test_source_diversity_truncation_sets_envelope_not_stage_items` |
| B6 | Empty path | empty `source_path` always admissible (not id-bucketed) | `test_empty_source_path_always_admissible` |

```bash
python3 -m unittest tests.test_ask_source_diversity -q
```

---

## C — Suites and tooling

| # | Check | Command / criterion |
|---|---|---|
| C1 | Focused | `python3 -m unittest tests.test_ask_source_diversity tests.test_ask_trace tests.test_ledger_recent -q` |
| C2 | Full suite | `python3 -m unittest discover -s tests -q` exit 0 (baseline-relative on Ryan host if env flakes) |
| C3 | Pylint gate | local `scripts/pylint_regression_gate.py ci …` exit 0 **or** GitHub Actions Pylint green on tip |
| C4 | Doctor | `convmem doctor` — non-fatal env warnings OK |

---

## D — Live probe (optional, not merge-blocking)

```bash
convmem ask --evidence --trace "current plan arc" 2>/dev/null | head -c 2000
# Inspect: final_context.source_diversity present; source_path counts ≤ 2 per path in citations
```

---

## E — Partner ledger (exact tip `5946d19`)

| Lane | Verdict | Notes |
|---|---|---|
| ChatGPT | **PASS** (process) | No code blocker; held merge for partner PASS — now satisfied |
| Independent / Grok-style recheck | **PASS** | Focused + pylint + lock table |
| R1 | **PASS** | 505 tests; Round 1/2 invariants; all locks |
| Continue-DeepSeek V4 | **PASS** | Live probe + full lock table |
| Kiro | **PASS** | 505 suite; five locks; merge when Ryan ready |

**Independent exact-tip review gate:** satisfied (multiple PASSes above).

---

## F — Merge gate

- [x] Hermetic locks B1–B6
- [x] Focused suites green
- [x] GitHub Pylint green on `5946d19`
- [x] One (or more) independent partner PASS on exact tip
- [x] Ryan merges PR #39 → `549f74d`

Agents do not merge `main`.

---

## Out of scope (unchanged)

MCP `evidence` default, `retrieve_for_ask`, retrieval-eval rewrite, title-collapse, cardinality-change PR.
