# CONTINUE-DEEPSEEK Problem 2 — nested inter-model docs are invisible

**Date:** 2026-07-15
**From:** Continue-DeepSeek (synthesis lane — `convmem ask`)
**To:** Cursor (implementer) + Ryan (authorizer) + Codex (auditor)

---

## Problem

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
