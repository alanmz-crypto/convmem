# Cursor final additions to v4 runbook

**To:** Kiro, Ryan, any model executing  
**From:** Cursor  
**Date:** 2026-06-30  
**Status:** Merged into [`KIRO-2026-06-30-redrafted-plan-v4.md`](KIRO-2026-06-30-redrafted-plan-v4.md) — this note is the audit trail

Chains to: `dec_prop_20260630_220459_1e3f`

---

## Verdict

v4 is **ready to execute** after these additions. No strategy changes — execution-shape fixes only.

---

## Commit 2 — Consolidate residue + rename root LATEST

### Residue: do-not-move list

After `ls docs/archive/residue/`, **do not** move these into `docs/archive/inter-model/2026-06-22/`:

| File | Reason |
|------|--------|
| `HANDOFF-CURSOR-AUTO-COMPOSER-2026-06-25-soak.md` | Dated 2026-06-25 — not June-22 soak |
| `README.md` | Residue folder index — leave in place |

Move the remaining ~12 files only after confirming each basename against the grep gate (includes undated soak residue such as `KIRO-TO-ALL-MODELS.md`, `README-FOR-CHATGPT.md`, `CONVERSATION_COMPACT.md`).

### Option A link patch (live cross-ref)

Root `README.md` has **no** `LATEST` references. The live cross-ref is in BUILT-PLANS:

- **File:** `docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`
- **Line:** ~1311
- **Change:** `../../LATEST.md` → `../../SYNTHESIS-STATUS.md`

Apply in the same commit as `git mv LATEST.md SYNTHESIS-STATUS.md`.

### Verify (add to Commit 2)

```bash
grep -rn '../../LATEST.md' docs/inter-model/BUILT-PLANS* || echo "clean"
grep LATEST brief.py mcp_server.py   # only docs/inter-model/LATEST.md
```

---

## Header / metadata

Resolve status inconsistency in v4:

- **Was:** `Status: Proposed final — awaiting ship A or ship B`
- **Now:** `Status: Approved — Option A; ready to execute`

Decision section already records Option A.

---

## Commit 4 — Flat docs index

In `docs/README.md`, include an explicit link to root **`SYNTHESIS-STATUS.md`** for the synthesis lane (not only “Option A was chosen” prose). Include in Commit 4 path grep verify.

---

## Commit 5

Add this file to the explicit archive list:

```bash
git mv docs/inter-model/CURSOR-2026-06-30-v4-final-additions.md docs/archive/inter-model/2026-06-30-org-planning/
```

---

## Not a plan change

Pre-flight pytest baseline count — optional operator note, not a gate requirement.
