# Repo organization runbook (v4 — final)

**To:** Ryan (approver), any model executing  
**From:** Kiro — incorporates Cursor serious-flags + Codex red-flags-after-redraft  
**Date:** 2026-06-30  
**Status:** Approved — Option A; ready to execute

Chains to: `dec_prop_20260630_220459_1e3f`

---

## Decision (resolved)

**Option A chosen:** rename root `LATEST.md` → `SYNTHESIS-STATUS.md`.  
`docs/inter-model/LATEST.md` stays unchanged (hard constraint — SPOF for brief, MCP, all agent rules).

---

## Scope

Archive historical soak. Delete dead files. Add navigation. No code changes.

**Not in scope:** Python refactors, `src/convmem/`, taxonomy subfolders, log splits, path configurability, watch-indexing archived prose.

---

## Invariants (any failure = stop and revert that commit)

1. `convmem doctor` exits 0
2. `pytest` passes
3. `convmem brief --stdout-only` — no false stale alarm
4. No frozen-path file changes location

---

## Frozen paths

| Path | Reason |
|------|--------|
| `convmem.py`, `mcp_server.py`, `brief.py`, `doctor.py` | Entrypoints |
| All flat `*.py` at root | Import anchors |
| `docs/inter-model/` directory | `brief.py` hardcodes it |
| `docs/inter-model/LATEST.md` | SPOF |
| `docs/inter-model/SESSION-CLOSE-RECORD.md` | Protocol generation |
| `docs/ROADMAP-DRAFT.md` | **Referenced by ROADMAP.md line 120 + BUILT-PLANS** |
| `export_report_to_observations.py`, `extract_procedures.py` | cwd-sensitive |

---

## Archive decision rule

A file moves **only if** its basename returns zero hits when grepped against the **minimum required set** below. This is not exhaustive — if you know of additional active docs that reference a candidate file, check those too.

Minimum grep targets:

- `docs/inter-model/LATEST.md`
- `docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`
- `docs/inter-model/CONTINUE-VERIFY.md`
- `docs/inter-model/SOAK-REPORT-2026-06-25.md`
- Any active `PLAN-*` or `HANDOFF-*` after 2026-06-24
- `docs/ROADMAP.md`

No file moves on date alone. Grep gate is mechanical.

---

## Rollback

Each commit is independently revertible: `git revert <sha>`.
If Commit 3 fails verification, do not proceed to Commits 4–5.

---

## Ordering constraint

Commits execute strictly in order 1 → 2 → 3 → 4 → 5. Specifically:

- **Commit 2 must complete** (root LATEST renamed, residue consolidated) before Commit 3 begins — Commit 3's grep gate assumes the residue files are already in the date bucket.
- **Commit 3 must pass verification** before Commits 4–5. If it fails, stop.
- Do not revisit root `SYNTHESIS-STATUS.md` during Commits 3–5.

---

## Commit 1 — Delete dead artifacts

**Message:** `chore: delete dead artifacts (procedures.jsonl, sonnet tarball)`

```bash
rm -f procedures.jsonl sonnet-mcp-verify-full.tar.gz
rmdir review-bundles 2>/dev/null || true
```

**Verify:** `convmem doctor`, `pytest`.

---

## Commit 2 — Consolidate residue + rename root LATEST

**Message:** `chore: consolidate residue into date bucket; rename root LATEST to SYNTHESIS-STATUS`

```bash
mkdir -p docs/archive/inter-model/2026-06-22

# Residue contents (verified 2026-06-30):
#   DO move (June-22 soak or undated soak):
#     ALL-MODELS-2026-06-22-joint-verification.md
#     ALL-MODELS-2026-06-22-next-moves-vote.md
#     CODEX-2026-06-22-claude-decision-next-path.md
#     CODEX-2026-06-22-multi-project-workspace.md
#     CONVERSATION_COMPACT.md
#     CURSOR-2026-06-22-chatgpt-decision-pack.md
#     DEEPSEEK-2026-06-22-wrap-up.md
#     KIRO-2026-06-22-workspace-response.md
#     KIRO-RESPONSE-2026-06-22.md
#     KIRO-STATUS-2026-06-22.md
#     KIRO-TO-ALL-MODELS.md
#     README-FOR-CHATGPT.md
#   DO NOT move:
#     HANDOFF-CURSOR-AUTO-COMPOSER-2026-06-25-soak.md  (2026-06-25, not June-22)
#     README.md  (residue folder index)

git mv docs/archive/residue/ALL-MODELS-2026-06-22-joint-verification.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/ALL-MODELS-2026-06-22-next-moves-vote.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/CODEX-2026-06-22-claude-decision-next-path.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/CODEX-2026-06-22-multi-project-workspace.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/CONVERSATION_COMPACT.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/CURSOR-2026-06-22-chatgpt-decision-pack.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/DEEPSEEK-2026-06-22-wrap-up.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/KIRO-2026-06-22-workspace-response.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/KIRO-RESPONSE-2026-06-22.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/KIRO-STATUS-2026-06-22.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/KIRO-TO-ALL-MODELS.md docs/archive/inter-model/2026-06-22/
git mv docs/archive/residue/README-FOR-CHATGPT.md docs/archive/inter-model/2026-06-22/

# Option A (decided):
git mv LATEST.md SYNTHESIS-STATUS.md
# Live cross-ref (root README.md has no LATEST refs):
# docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md line ~1311:
#   ../../LATEST.md → ../../SYNTHESIS-STATUS.md
```

**Verify:**

```bash
convmem doctor
pytest
grep -rn '../../LATEST.md' docs/inter-model/BUILT-PLANS* || echo "clean"
grep LATEST brief.py mcp_server.py   # only docs/inter-model/LATEST.md
```

---

## Commit 3 — Bulk archive June-22 soak

**Message:** `chore: archive June-22 inter-model soak files to dated bucket`

**Precondition check (advisory — sanity only, not a stop gate):**

```bash
ls docs/inter-model/*2026-06-22* | wc -l   # expect ~102; proceed if 80–120
```

**Glob safety:** The pattern `*2026-06-22*` does not match any keep-list file — they contain `2026-06-24`, `2026-06-25`, `2026-06-29`, or `2026-06-30`, never `2026-06-22`. No manual exclusions from the glob are needed.

**Grep-gated move:**

```bash
for f in docs/inter-model/*2026-06-22*; do
  base=$(basename "$f")
  if grep -rq "$base" \
      docs/inter-model/LATEST.md \
      docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md \
      docs/inter-model/CONTINUE-VERIFY.md \
      docs/inter-model/SOAK-REPORT-2026-06-25.md \
      docs/ROADMAP.md 2>/dev/null; then
    echo "KEEP (referenced): $f"
  else
    git mv "$f" docs/archive/inter-model/2026-06-22/
  fi
done
```

**Additional confirmed-safe move:**

```bash
git mv GLOBAL-CONVMEM-PROTOCOL-PLANNER.md docs/archive/inter-model/
```

**Do NOT move:** `docs/ROADMAP-DRAFT.md` (live reference from ROADMAP.md).

**Add** `docs/archive/inter-model/README.md`:

```markdown
# Archived inter-model coordination

Date-bucketed historical soak and retired plans.
Not scanned by brief staleness. Active inbox: docs/inter-model/.
Truth: ledger + brief.
```

**Update:** `docs/inter-model/README.md` — pointer to archive for pre-2026-06-24 context.

**Verify (mandatory — stop if fail):**

```bash
convmem doctor                             # HARD GATE: must exit 0
pytest                                     # HARD GATE: must pass
convmem brief --stdout-only                # HARD GATE: no false stale alarm
ls docs/inter-model/*.md | wc -l           # ADVISORY: expect ~55–60
```

---

## Commit 4 — Flat docs index

**Message:** `docs: add docs/README.md navigation index`

- Flat list of active docs
- **Explicit link** to root [`SYNTHESIS-STATUS.md`](../../SYNTHESIS-STATUS.md) for synthesis lane (Option A)
- **Record that Option A was chosen** so future sessions know

**Verify:** grep `docs/README.md` for nonexistent paths; confirm `SYNTHESIS-STATUS.md` is linked.

---

## Commit 5 — Archive org-planning meta-docs (same PR, unconditional)

**Message:** `chore: archive 2026-06-30 org-planning meta-docs`

Fires immediately after Commit 4. No second approval.

```bash
mkdir -p docs/archive/inter-model/2026-06-30-org-planning

# Explicit file list — do NOT use date glob (would catch unrelated files)
git mv docs/inter-model/CODEX-2026-06-30-repo-organization-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CODEX-2026-06-30-repo-organization-assessment.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CODEX-2026-06-30-repo-organization-forward-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CODEX-2026-06-30-repo-organization-red-flags.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CODEX-2026-06-30-red-flags-after-redraft.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CODEX-2026-06-30-remaining-flags-after-option-a.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CODEX-2026-06-30-final-additions-for-kiro.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-file-organization-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-organization-assessment.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-organization-red-flags.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-serious-flags-remaining.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/KIRO-2026-06-30-repo-organization-review.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/KIRO-2026-06-30-organization-execution-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/KIRO-2026-06-30-synthesized-plan-critique.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/KIRO-2026-06-30-redrafted-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/KIRO-2026-06-30-redrafted-plan-v4.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-repo-organization-assessment.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-cross-assessment-red-flags.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-reconsidered-red-flags.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-what-i-didnt-flag.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-new-flags-after-kiro-codex.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-organization-execution-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-critique-of-all-models-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/ALL-MODELS-2026-06-30-repo-organization-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-v4-final-additions.md docs/archive/inter-model/2026-06-30-org-planning/
```

**Update `docs/inter-model/LATEST.md`:**

```markdown
- **Repo organization (2026-06-30):** shipped (Option A — root LATEST renamed to SYNTHESIS-STATUS.md).
  Runbook + trail: `docs/archive/inter-model/2026-06-30-org-planning/`
```

**Verify:**

```bash
convmem brief --stdout-only
ls docs/inter-model/*.md | wc -l   # ADVISORY: expect ~30–35
```

---

## Expected end state

| Metric | Before | After |
|--------|--------|-------|
| `docs/inter-model/*.md` count | ~160 | ~30–35 |
| June-22 soak in inbox | ~102 | 0 (minus grep keeps) |
| Org meta in inbox | ~25 | 0 |
| Root dead files | 2 | 0 |
| `docs/ROADMAP-DRAFT.md` | untouched | untouched |

---

## Changes from previous drafts

1. `docs/ROADMAP-DRAFT.md` frozen — confirmed live refs from ROADMAP.md + BUILT-PLANS
2. Residue glob replaced with explicit ls + manual move — not all residue files match `*2026-06-22*`
3. Grep gate expanded — now checks CONTINUE-VERIFY, SOAK-REPORT, and ROADMAP.md too
4. Commit 5 uses explicit file list — no date glob that would accidentally catch unrelated files
5. All org-planning docs archive (including this runbook) — nothing stays behind; LATEST.md gets the pointer
6. Option A/B outcome recorded in both docs/README.md and LATEST.md update
7. Broken stop-list link eliminated — constraints are inline, not cross-referenced to an archived file
8. Cursor final additions (2026-06-30): residue do-not-move list, BUILT-PLANS `../../SYNTHESIS-STATUS.md` link patch, status line, Commit 4 explicit synthesis link — see `CURSOR-2026-06-30-v4-final-additions.md`

---

## This file is final

Do not append responses. Disagreements go in a separate dated note.
