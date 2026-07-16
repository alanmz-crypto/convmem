# CONTINUE-DEEPSEEK — top two problems + implementation plans

**Date:** 2026-07-15
**From:** Continue-DeepSeek (synthesis lane — `convmem ask` / DeepSeek V4 via Continue)
**To:** Cursor (implementer) + Ryan (authorizer) + all debate lanes
**Source:** Local drafts that were written under the debate folder on a non-debate
checkout and never pushed — Cursor found them and filed them here as one board
document. Original split drafts (same content):
`CONTINUE-DEEPSEEK-problem-1-evidence-domain-scoping.md`,
`CONTINUE-DEEPSEEK-problem-2-nested-inter-model.md`.

## Ranking

| Rank | Problem | Why now |
|---|---|---|
| **1** | Evidence path injects unscoped recent decisions and can zero out semantic slots | MCP default `evidence=True`; cross-project willowyhollow decisions crowd citations |
| **2** | Nested `docs/inter-model/**` not recognized as inter-model docs | Debate folder invisible to ingest / ask |

---

## Problem 1 — evidence path injects cross-project noise

### Symptom / problem

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

---

## Problem 2 — nested inter-model docs are invisible

### Symptom / problem

`is_inter_model_doc` only recognizes Markdown files whose **direct parent** is
`inter-model` and grandparent is `docs`. This means files under nested
directories — like the debate folder `docs/inter-model/debate-2026-07-15-*/` —
are invisible to the corpus. Every `convmem index --file` on a debate file
silently skips it.

This is the **capture contract defect** Codex identified: the debate itself
can never enter shared memory. Every lane's opinion, stance, and synthesis
exists only on the filesystem — `convmem ask` can't find them.

### Root cause

```python
# adapters/inter_model_doc.py — current check
return p.parent.name == "inter-model" and p.parent.parent.name == "docs"
```

For `docs/inter-model/debate-2026-07-15-who-fixes-retrieval/README.md`:
- `p.parent.name` → `"debate-2026-07-15-who-fixes-retrieval"` (not `"inter-model"`)
- `p.parent.parent.name` → `"inter-model"` (correct!)
- Result: `False` — rejected

### What `ec59fcc` (P0a) did and didn't fix

The P0a commit added `.kiro`/`snapshots` path exclusion but preserved the
strict direct-parent check. Kiro snapshots are now excluded. Debate nested
files remain excluded. The fix needs to generalize the ancestry check without
reopening the Kiro snapshot vulnerability.

### Files affected

Only one file needs to change: `adapters/inter_model_doc.py`. Two test files
should be updated: `tests/test_inter_model_doc.py` (add nested-doc tests) and
the debate folder's README (update the indexing instructions).

---

## Plan

### Step 1: Replace direct-parent check with ancestor-walk (~10 lines)

Replace the strict parent-name check with an ancestor search that finds the
first `inter-model` directory in the path ancestry and verifies its parent
is `docs`.

```python
def is_inter_model_doc(path: Path | str) -> bool:
    """True for active coordination docs under docs/inter-model/ (any depth)."""
    p = Path(path).expanduser().resolve()
    if p.suffix != ".md":
        return False
    if "archive" in p.parts:
        return False
    if _EXCLUDE_PATH_TOKENS & set(p.parts):
        return False
    # Walk ancestors: find the first 'inter-model' directory and check
    # its parent is 'docs'. This supports both direct children
    # (docs/inter-model/PLAN.md) and nested descendants
    # (docs/inter-model/debate-.../OPINION.md).
    parts = list(p.parts)
    for i, part in enumerate(parts):
        if part == "inter-model" and i > 0 and parts[i - 1] == "docs":
            return True
    return False
```

**Why this is safe:** The `archive` exclusion is checked first against ALL
parts (not just parent), so `docs/archive/inter-model/old.md` still returns
`False`. The `.kiro`/`snapshots` exclusion is also checked against ALL parts
first, so Kiro snapshot paths like
`.kiro/sessions/.../snapshots/.../docs/inter-model/...md` still return
`False`. The ancestor walk only fires after both exclusions pass.

**Boundary cases:**
- `docs/inter-model/PLAN.md` → ancestors: `[..., "inter-model"]`, `"inter-model"` at i, `parts[i-1]` = `"docs"` → `True` ✅
- `docs/inter-model/debate-x/README.md` → ancestors: `[..., "debate-x", "inter-model"]`, `"inter-model"` found at i, `parts[i-1]` = `"docs"` → `True` ✅
- `docs/archive/inter-model/old.md` → `"archive" in p.parts` → `False` (early return) ✅
- `.kiro/sessions/x/snapshots/y/docs/inter-model/KIRO.md` → `_EXCLUDE_PATH_TOKENS & set(p.parts)` → `False` (early return) ✅
- `docs/inter-model/debate-x/deeply/nested/PLAN.md` → ancestors: `[..., "PLAN", "nested", "deeply", "debate-x", "inter-model"]`, `"inter-model"` at i, `parts[i-1]` = `"docs"` → `True` ✅
- `other/inter-model/PLAN.md` (no `docs` parent) → `"inter-model"` found but `parts[i-1]` ≠ `"docs"` → `False` ✅

### Step 2: Add tests (~15 lines)

Add a `test_is_nested_inter_model_doc` to the existing test class:

```python
def test_is_nested_inter_model_doc(self):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Nested debate file — should be recognized
        debate = root / "docs" / "inter-model" / "debate-test" / "README.md"
        debate.parent.mkdir(parents=True)
        debate.write_text("# Debate\n", encoding="utf-8")
        self.assertTrue(is_inter_model_doc(debate))
        self.assertEqual(detect_format(debate), "inter_model_doc")
        self.assertIsNotNone(get_parser(debate))

        # Deeply nested
        deep = root / "docs" / "inter-model" / "a" / "b" / "c" / "notes.md"
        deep.parent.mkdir(parents=True)
        deep.write_text("# Deep\n", encoding="utf-8")
        self.assertTrue(is_inter_model_doc(deep))

        # Kiro snapshot nested — still excluded (P0a)
        kiro_snap = root / ".kiro" / "sessions" / "s" / "snapshots" / "h" / "docs" / "inter-model" / "debate" / "f.md"
        kiro_snap.parent.mkdir(parents=True)
        kiro_snap.write_text("# KIRO\n", encoding="utf-8")
        self.assertFalse(is_inter_model_doc(kiro_snap))
```

### Step 3: Re-index the debate folder (~1 command)

After the fix lands, index all debate files:

```bash
for f in docs/inter-model/debate-2026-07-15-who-fixes-retrieval/*.md; do
    convmem index --file "$f"
done
```

Or add a one-shot script: `scripts/index-debate-folder.sh` that finds all
`.md` files under `docs/inter-model/debate-*/` and indexes them.

### Lines of code: ~25 (10 for fix + 15 for tests)

---

## Acceptance check

1. **Unit tests (3 new):**
   - Nested debate file → `is_inter_model_doc` returns `True`
   - Deeply nested file (3+ levels) → `True`
   - Kiro snapshot nested file → `False` (P0a exclusion preserved)
   - All existing tests still pass (direct-child, archive, random .md)

2. **Integration test:** `convmem index --file docs/inter-model/debate-2026-07-15-who-fixes-retrieval/README.md`
   — indexes successfully. Pre-fix: silently skipped. Post-fix: reports units indexed.

3. **Retrieval test:** After re-indexing all debate files, `convmem ask "debate
   retrieval fix"` returns debate folder opinions in the top results.

4. **Regression:** `convmem index` (full scan) does not re-ingest any Kiro
   snapshot files. `detect_format` returns `None` for all snapshot paths.

---

## Explicitly out of scope

- **Adding support for non-Markdown debate artifacts.** Only `.md` files are
  recognized. PDF exports, JSON transcripts, or other formats in the debate
  folder will be skipped — that's correct behavior.
- **Nested `archive/` under `docs/inter-model/debate-*/`.** The `"archive" in
  p.parts` check already handles this. No additional nesting logic needed.
- **Performance optimization for deep nesting.** The ancestor walk is O(depth)
  — ~6-8 parts for typical paths. No measurable cost.
- **Changing how `inventory.py` discovers nested files.** The inventory
  scanner already recursively discovers all `.md` files. No changes needed —
  `detect_format` is the gate.

---

## Relationship to other proposals

| Proposal | Overlap? | Resolution |
|---|---|---|
| Kiro-sanctioned P0 landing (`ec59fcc`) | Same file, different check | This extends the parent check; `.kiro`/`snapshots` exclusion is untouched |
| Codex "nested inter-model" (CODEX-final-all-views.md) | Identical problem | This is the implementation plan Codex requested |
| CURSOR-final-synthesis item 1 | Identical problem | Codex/Cursor agreement — implement as described |

---

## Meta

**Author:** Continue-DeepSeek (Continue MCP, writing `ask`)
**Related diagnosis:** Nil-to-Minor section of CONTINUE-DEEPSEEK-2026-07-15-retrieval-diagnosis.md (debate folder invisible)
**Related debate files:** CODEX-final-all-views.md, CURSOR-final-synthesis.md, ALERT-2026-07-15-deepseek-p0-landed.md
**Depends on:** P0a (`ec59fcc` — the `.kiro`/`snapshots` exclusion must be in place before extending the parent check)
**Conflicts with:** Nothing filed yet
**Risk:** Very low — ancestor walk is a generalization of the existing check, not a replacement. All exclusion logic runs first.
