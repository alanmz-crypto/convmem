# CONTINUE-DEEPSEEK Problem 1 — evidence path injects cross-project noise

**Date:** 2026-07-15
**From:** Continue-DeepSeek (synthesis lane — `convmem ask`)
**To:** Cursor (implementer) + Ryan (authorizer) + Codex (auditor)

---

## Problem

When `ask(evidence=True)` is called (MCP default), `_prepend_recent_decisions`
injects the 8 most recent approved decisions into the context block **without
domain filtering**. This means a convmem query like "Why was purge-drift
deferred?" gets 4 of 5 citation slots filled by WordPress willowyhollow
arc-closure decisions instead of convmem retrieval results.

Kiro independently verified this (Finding 1, KIRO-stance.md): with 8 recent
decisions and `total_limit=8`, `slots` computes to 0 — zero semantic retrieval
survives. The MCP path is structurally broken for any corpus with cross-project
decisions.

### Root cause: two interacting defects

```python
# ask.py — _prepend_recent_decisions
def _prepend_recent_decisions(semantic, recent_records, *, max_recent=8, total_limit=8):
    recent_units = [decision_record_to_unit(r) for r in recent_records[:max_recent]]
    # ... dedupe ...
    slots = max(total_limit - len(recent_units), 0)   # ← 8 - 8 = 0
    return recent_units + rest[:slots]                 # ← rest[:0] = []
```

1. **No domain filter on recent records.** `recent_decisions_for_cfg` loads
   ALL approved decisions from the last 7 days. WordPress willowyhollow and
   convmem decisions are treated identically. When the user asks a convmem
   question, `_prepend_recent_decisions` can't distinguish relevant from
   irrelevant decisions.

2. **No semantic slot reservation.** When 8 recent decisions exist, all 8
   context slots go to decisions — zero semantic retrieval. Even if every
   decision is perfectly relevant (same-project), this is wrong: recent
   decisions should supplement semantic retrieval, not replace it.

Both defects are in `ask.py` alone. No other files need to change.

### Evidence (live, verified)

```bash
# MCP default: evidence=True
convmem ask --evidence "Why was purge-drift deferred after the exclude-purge review?"
# Result: 4 WordPress willowyhollow arc-closure decisions in slots 1-4.
# Semantic retrieval (correction trail) pushed to slot 5.
# Answer: "no excerpts contain the deferral rationale."

# CLI default: evidence=False
convmem ask "Why was purge-drift deferred after the exclude-purge review?"
# Result: correction trail in slots 1-3. Clean semantic retrieval.
# Same answer quality — but the context pool was correct.
```

The evidence path **worsens** answer quality for cross-project queries because
it substitutes relevant context with irrelevant decisions. This is a
context-selection defect, not an answer-quality defect.

---

## Plan

### Fix 1: Domain-filter recent decisions (~5 lines)

Add an optional `domain` parameter to `_prepend_recent_decisions`. When the
caller passes a domain, filter recent records to only those matching that
domain (or its prefix).

```python
def _prepend_recent_decisions(
    semantic: list[dict],
    recent_records: list[dict],
    *,
    max_recent: int = RECENT_DECISIONS_LIMIT,
    total_limit: int,
    domain: str | None = None,       # NEW
) -> list[dict]:
    if domain:
        recent_records = [
            r for r in recent_records
            if (r.get("domain") or "").startswith(domain.split(".")[0])
        ]
    # ... rest unchanged ...
```

**Domain matching strategy:** Match on the top-level domain component (first
segment before `.`). A `domain="coding"` call matches `coding.tooling`,
`coding.backend`, and any future `coding.*` decision — but not
`web_stack.wordpress` or `project_management`. This is deliberately coarse:
convmem decisions live under `coding`, WordPress under `web_stack`. Fine-grained
matching adds complexity without benefit given the current corpus structure.

**Caller change in `ask()`:**

```python
if recent:
    units = _prepend_recent_decisions(
        units, recent, total_limit=fetch_k, domain=domain
    )
```

**Behavior:** When the user passes `--domain coding` (or the MCP caller
supplies a domain), only recent decisions from that top-level domain are
injected. When no domain is specified — or when the domain doesn't match any
recent decision — the behavior is unchanged (no filtering).

### Fix 2: Reserve semantic slots (~1 line)

Guarantee at least 50% of context slots come from semantic retrieval:

```python
# Before:
slots = max(total_limit - len(recent_units), 0)
# After:
slots = max(total_limit - len(recent_units), total_limit // 2)
```

This ensures that even with 8 perfectly relevant recent decisions, at least 4
slots remain for semantic retrieval. The decisions still get priority placement
(positions 1-4), but semantic results fill positions 5-8.

**Combined effect of both fixes:**

| Scenario | Before | After |
|---|---|---|
| convmem query, 8 recent WordPress decisions, `--evidence` | 8 WordPress decisions, 0 semantic (broken) | 4 convmem semantic + 0 irrelevant decisions (domain filter blocks all 8) |
| convmem query, 8 recent convmem decisions, `--evidence` | 8 decisions, 0 semantic (broken) | 4 decisions + 4 semantic (balanced) |
| convmem query, no recent decisions, `--evidence` | 8 semantic (unchanged) | 8 semantic (unchanged) |
| convmem query, `evidence=False` (CLI default) | 8 semantic (unchanged) | 8 semantic (unchanged) |

---

## Acceptance check

1. **Unit test:** `test_prepend_recent_decisions_domain_filter` — 4 recent
   decisions (2 convmem `coding.*`, 2 WordPress `web_stack.*`), domain=`coding`.
   Expect: only 2 convmem decisions prepended, 6 semantic slots remain.

2. **Integration test (CLI):** `convmem ask --evidence --domain coding "current
   corpus state"` — citations include only `coding.*` decisions. No WordPress
   decisions in context.

3. **Integration test (MCP):** Call `ask(evidence=True, domain="coding")` via
   MCP and verify no WordPress willowyhollow decisions appear in the returned
   citations array. The MCP surface currently discards trace diagnostics —
   check the returned citation metadata for domain field.

4. **Regression:** `convmem ask "current plan arc"` (CLI default,
   `evidence=False`) — behavior unchanged from post-P0 state (July 15 facts at
   ranks 1-3).

---

## Explicitly out of scope

- **Adding domain to `_prepend_recent_decisions` via MCP tool parameter.**
  MCP `ask()` already supports an optional `domain` parameter. The caller
  change in `ask.py` wires it through. No MCP surface changes needed.
- **Fine-grained domain matching (subdomain filtering).** Top-level matching
  is sufficient given the current corpus. If projects develop sub-domains
  that cross-pollinate, add a `_domain_match()` helper later.
- **Source diversification in `_format_context`.** That's a separate problem
  (ChatGPT's proposal). This fix is about context selection, not formatting.
- **Adding a `domain` parameter to `recent_decisions_for_cfg`.** Filtering
  in `_prepend_recent_decisions` is the right place: it keeps
  `recent_decisions_for_cfg` as a pure data-fetch and lets context assembly
  decide what to include.

---

## Meta

**Author:** Continue-DeepSeek (Continue MCP, writing `ask`)
**Related diagnosis:** Layer 6 (corrected) of CONTINUE-DEEPSEEK-2026-07-15-retrieval-diagnosis.md
**Related debate files:** KIRO-stance.md (Finding 1), CODEX-final-all-views.md, CURSOR-final-synthesis.md
**Depends on:** Nothing (standalone fix)
**Conflicts with:** Nothing filed yet
**Risk:** Low — domain filter is additive (default behavior unchanged), slot reservation is a single arithmetic change
