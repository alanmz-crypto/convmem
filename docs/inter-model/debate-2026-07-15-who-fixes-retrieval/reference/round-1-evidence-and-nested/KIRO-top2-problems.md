# KIRO — Top 2 Problems + Implementation Plans for Cursor

**Date:** 2026-07-15
**From:** Kiro (design / sign-off lane)
**To:** Cursor (implementer) + Plan Maker

---

## Problem 1: `_prepend_recent_decisions` replaces the semantic retrieval pool

### What's broken

When `evidence=True` (MCP default for every agent), `_prepend_recent_decisions`
can allocate ALL context slots to recent decisions, leaving ZERO slots for
semantic retrieval results. The math:

- `total_limit = fetch_k = max(top_k, 8) = 8`
- `RECENT_DECISIONS_LIMIT = 8`
- `slots = max(8 - 8, 0) = 0`

Every MCP agent (Cursor, Kiro, Crush, Continue) calling `ask()` gets answers
built from unrelated project decisions instead of retrieved corpus material.
This is the **primary cause** of retrieval failure for MCP callers — not
stale mass, not duplicate attractors.

Additionally: the evidence path opens `ChromaStore(...)` without closing it
(no context manager, no `try/finally`), leaking SQLite connections in
long-lived MCP processes.

### Implementation plan

**File:** `ask.py`

**Change 1 — Guarantee semantic survival (line ~187):**

Replace:
```python
slots = max(total_limit - len(recent_units), 0)
```

With:
```python
slots = max(total_limit - len(recent_units), total_limit // 2)
```

This guarantees at least 50% of the context budget goes to semantic retrieval,
regardless of how many recent decisions exist.

**Change 2 — Scope recent decisions by domain (lines ~320-323):**

After `recent = recent_decisions_for_cfg(...)`, filter to only include
decisions whose `domain` shares a prefix with the query's domain (if domain
was passed) or with the top-scoring semantic unit's domain:

```python
if recent and domain:
    recent = [r for r in recent
              if (r.get("domain") or "").startswith(domain.split(".")[0])]
elif recent and units:
    top_domain = (units[0].get("metadata") or {}).get("domain", "")
    if top_domain:
        prefix = top_domain.split(".")[0]
        recent = [r for r in recent
                  if (r.get("domain") or "").startswith(prefix)]
```

This prevents WordPress decisions from consuming slots in convmem queries.

**Change 3 — Fix ChromaStore leak (lines ~309-317):**

Replace the bare `ChromaStore(...)` instantiation:
```python
store = ChromaStore(cfg["index"]["chroma_dir"])
```

With a context manager or try/finally:
```python
from chroma_readonly import open_readonly_unit_store
store = open_readonly_unit_store(cfg["index"]["chroma_dir"])
try:
    # ... existing evidence rerank logic ...
finally:
    store.close()
```

(Or use `ChromaStore` as a context manager if it supports `__enter__`/`__exit__`.)

### Acceptance test

```bash
# Before fix: 4-5 of 5 citations are unrelated project decisions
convmem ask "Why was purge-drift deferred after the exclude-purge review?" --evidence

# After fix: at least 3 of 5 citations must be semantic retrieval hits
# (type != "recent_decision" and source_path relevant to convmem)
convmem ask "Why was purge-drift deferred after the exclude-purge review?" --evidence

# Regression: non-evidence path unchanged
convmem ask "Why was purge-drift deferred after the exclude-purge review?"

# Regression: evidence path still surfaces relevant recent decisions when they exist
convmem ask "What was the last decision about retrieval?" --evidence
```

### Scope

- `ask.py` only (3 changes, ~15 lines total)
- No behavior change for `evidence=False` (CLI default)
- No new dependencies

---

## Problem 2: Nested `docs/inter-model/` paths are invisible to the corpus

### What's broken

`is_inter_model_doc()` in `adapters/inter_model_doc.py` requires:
```python
p.parent.name == "inter-model" and p.parent.parent.name == "docs"
```

This only matches direct children of `docs/inter-model/`. Any file in a
subdirectory (like this entire debate folder at
`docs/inter-model/debate-2026-07-15-who-fixes-retrieval/*.md`) fails the
check because `parent.name` is the subfolder name, not `"inter-model"`.

The result: 23 debate files containing the project's governance decisions
about retrieval are invisible to the memory bus. Lanes contributing to
shared coordination cannot retrieve each other's work. This is the exact
capture-contract failure that Arc 0 identified, recurring one directory
level deeper.

### Implementation plan

**File:** `adapters/inter_model_doc.py`

**Change — Walk up to find `inter-model` ancestor (replace the final return):**

Replace:
```python
return p.parent.name == "inter-model" and p.parent.parent.name == "docs"
```

With:
```python
# Accept direct children AND descendants of docs/inter-model/
# Walk up from the file to find inter-model/docs ancestry
for ancestor in p.parents:
    if ancestor.name == "inter-model" and ancestor.parent.name == "docs":
        return True
return False
```

This matches:
- `docs/inter-model/LATEST.md` (direct child — existing behavior)
- `docs/inter-model/debate-2026-07-15-who-fixes-retrieval/KIRO-stance.md` (nested)
- NOT `docs/inter-model/archive/old-file.md` (excluded by earlier `archive` check)
- NOT `~/.kiro/sessions/.../snapshots/.../docs/inter-model/file.md` (excluded by `_EXCLUDE_PATH_TOKENS`)

**File:** `tests/` (new or existing test file for inter_model_doc)

Add tests for:
```python
# Direct child — True (existing behavior preserved)
assert is_inter_model_doc("/repo/docs/inter-model/LATEST.md") is True

# Nested descendant — True (new behavior)
assert is_inter_model_doc("/repo/docs/inter-model/debate-folder/KIRO-stance.md") is True

# Deeply nested — True
assert is_inter_model_doc("/repo/docs/inter-model/a/b/c/file.md") is True

# Archive excluded — False
assert is_inter_model_doc("/repo/docs/inter-model/archive/old.md") is False

# Kiro snapshot excluded — False
assert is_inter_model_doc("~/.kiro/sessions/x/snapshots/y/docs/inter-model/file.md") is False

# Non-markdown — False
assert is_inter_model_doc("/repo/docs/inter-model/debate/file.txt") is False

# Wrong parent structure — False
assert is_inter_model_doc("/repo/other/inter-model/file.md") is False
```

### Post-implementation step

After the code fix ships, re-index the debate folder:
```bash
for f in docs/inter-model/debate-2026-07-15-who-fixes-retrieval/*.md; do
  convmem index --file "$f"
done
```

Then verify retrieval:
```bash
convmem "KIRO trace-first prerequisite"
# Should return KIRO-opinion.md content

convmem "DeepSeek R1 _prepend_recent_decisions bug"
# Should return DEEPSEEK-R1-opinion-v2.md content
```

### Acceptance test

```bash
# The debate folder's files index successfully
convmem index --file docs/inter-model/debate-2026-07-15-who-fixes-retrieval/README.md
# Exit 0, units created > 0

# A distinctive phrase retrieves the correct file
convmem "Kiro snapshot multiplication root cause"
# Returns CONTINUE-DEEPSEEK diagnosis content
```

### Scope

- `adapters/inter_model_doc.py` — ~5 lines changed
- Test file — ~20 lines added
- No behavior change for direct children of `docs/inter-model/`
- No new dependencies
- `archive` and snapshot exclusions still work (tested)

---

## Conflict avoidance notes

These two fixes are independent — they touch different files (`ask.py` vs
`adapters/inter_model_doc.py`) and different subsystems (retrieval pipeline
vs ingestion path). They can be implemented on separate branches or together.

Neither fix touches:
- `query.py` (keyword scoring, candidate retrieval)
- `refine.py` (dedupe jobs)
- `mcp_server.py` (MCP surface — trace contract is a separate future item)
- Live config (`~/.config/convmem/config.toml`)
- Corpus data (no purge, no re-index of existing content)

If another lane proposes source-diversity caps in `_format_context`, that
complements Problem 1 without conflicting — it operates on the final
citation list after `_prepend_recent_decisions` has already allocated slots.
