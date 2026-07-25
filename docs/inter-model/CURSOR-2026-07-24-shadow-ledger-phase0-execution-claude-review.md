# Cursor → Claude: review Shadow Ledger Phase 0 Execution Plan

**Who:** Cursor packages after Ryan lock **B** (Kiro revisions applied); Claude
Cloud reviews (strategy / adversarial — no code, no prod writes).  
**What:** Advise Ryan whether to **approve** the revised Execution Plan for
Cursor Execute (disabled-by-default Phase 0 only).  
**When:** After Architecture HITL + Gate 1b PASS + Codex plan + DeepSeek/Kiro
Execution review. Tip is the commit that lands this handoff + revised plan.  
**Why:** Second opinion before Execute spend.  
**How:** Read the linked plan; answer the questions below. Do **not** rewrite
Architecture, authorize production activation, or start Neutral/backup Track 1.

## Authority (locked — do not reopen)

| Gate | State |
|---|---|
| Architecture Option B | APPROVED (#115) |
| Gate 1b audit corrections | PASS (#121 → `main` `0d08310`) |
| Execution Planning authorship | Authorized; Codex authored plan @ `5104022` |
| Dense consult on plan | DeepSeek **APPROVE** (95); Kiro **APPROVE_WITH_REVISIONS** (82) |
| Ryan lock | **B** — apply Kiro revisions, then Claude look |
| Revisions | Applied in `EXECUTION-shadow-ledger-phase0.md` (this tip) |
| Execute / production activation | **Still forbidden** until Ryan approves after your review |

## Primary artifact (read this)

**Execution Plan (revised):**  
[`docs/plans/EXECUTION-shadow-ledger-phase0.md`](../plans/EXECUTION-shadow-ledger-phase0.md)

**Companion VERIFY stub (do not fill):**  
[`docs/plans/VERIFY-shadow-ledger-phase0.md`](../plans/VERIFY-shadow-ledger-phase0.md)

**Approved Architecture (context only):**  
[`docs/plans/ARCHITECTURE-shadow-ledger-phase0.md`](../plans/ARCHITECTURE-shadow-ledger-phase0.md)

**PR:** https://github.com/alanmz-crypto/convmem/pull/115  
**Branch:** `docs/2026-07-24-shadow-ledger-phase0-architecture`

## What Kiro required (now in the plan)

**Blocking (applied):** Stop if `UnitMutationSink` collection discriminator
cannot be enforced without a `ChromaStore` API change that reopens Option B
(including accidental observation of `conversation_summaries`).

**Should-fix (applied):**
1. T2 allowlist: extend only for callers that cannot reach production Chroma;
   otherwise stop.
2. T3 250 ms lock timeout: log/stderr warn + health sidecar; doctor WARN only
   after N consecutive timeouts.
3. T4 live embed: fail explicitly if local model unreachable — no silent stub
   fallback.
4. Runtime stamp: paste full output into Execute PR description before first
   code edit.

## Dense-consult residual (for Claude to weigh)

DeepSeek said approve as-is was fine; Kiro said the stop-condition gap was the
only blocker. After B, is the plan safe for Cursor Execute HITL, or do you still
want further revisions?

## Your job (Claude)

Produce a short Ryan-facing memo:

1. **Verdict:** `APPROVE` | `APPROVE_WITH_REVISIONS` | `REJECT`
2. **Confidence** 0–100
3. **Blocking issues** (if any) — exact section cites
4. **Non-blocking notes** Cursor/Codex can absorb during Execute
5. **One sentence** Ryan should lock: approve Execute / revise again / park

### Method

- Prefer repository-grounded constraints over abstract ledger theory.
- Do not reopen “is ledger-first a good idea?” or Architecture Option A/B/C.
- Do not authorize production activation, restore-order flip, Neutral, or Track 1
  backup merge.
- Separate facts / inferences / recommendations.

## Hard stops for Claude

- No Python, hooks, commits, or PRs.
- No Execute grant (only Ryan can grant after your memo).
- No backup/Restic Hybrid audit of `492e6e7` in this review.

## Paste-ready opener for Claude

```text
Review the revised Shadow Ledger Phase 0 Execution Plan for Ryan HITL.

Primary file:
docs/plans/EXECUTION-shadow-ledger-phase0.md
on branch docs/2026-07-24-shadow-ledger-phase0-architecture (PR #115).

Context handoff:
docs/inter-model/CURSOR-2026-07-24-shadow-ledger-phase0-execution-claude-review.md

Architecture is APPROVED; Gate 1b PASS; Kiro revision lock B is applied.
Advise APPROVE / APPROVE_WITH_REVISIONS / REJECT for Cursor Execute
(disabled-by-default only). No production activation. No code.
```

---

## Claude verdict (received 2026-07-24)

**Verdict: APPROVE** — Confidence **90/100**. Blocking issues: none.

Claude confirmed Kiro lock-B fixes present, Architecture fitness functions mapped
to T1–T5, VERIFY stub genuine, scope fences intact, production activation still
a separate Ryan grant.

**Non-blocking (absorb in Execute / filled VERIFY — no plan edit):**
1. Record chosen N for consecutive lock-timeout doctor WARN + rationale in VERIFY.
2. Explicitly evidence `mutation_sink=None` path is behavior- and latency-neutral
   vs shadow-enabled tests (not only that shadow tests pass).

**Ryan status:** Claude advises Approve Execute. **Cursor Execute remains
unauthorized until Ryan explicitly grants Execution HITL** (e.g. “Approve
Execute” / “Lock it”). Production activation stays a later separate grant.

