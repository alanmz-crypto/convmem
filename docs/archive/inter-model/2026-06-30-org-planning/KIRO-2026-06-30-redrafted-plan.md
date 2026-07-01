# Repo organization runbook — best-practices redraft

**To:** Ryan (approver), any model executing  
**From:** Kiro  
**Date:** 2026-06-30  
**Status:** Proposed final runbook — awaiting `ship A` or `ship B`

Chains to: `dec_prop_20260630_220459_1e3f`

---

## Prerequisite decision (resolve before execution)

Root `LATEST.md` and `docs/inter-model/LATEST.md` share a name at different levels.

| Option | Action | Affects |
|--------|--------|---------|
| **A — Rename** | `git mv LATEST.md SYNTHESIS-STATUS.md` | Commit 2; docs/README.md wording in Commit 4 |
| **B — Document** | Keep both; add disambiguation note to docs/README.md | Commit 4 only |

**Constraint:** `docs/inter-model/LATEST.md` is never renamed or relocated (runtime SPOF).

---

## Scope

Make the repo navigable without breaking runtime paths. Archive historical soak; preserve active coordination. No code changes.

**Not in scope:** Python refactors, `src/convmem/` layout, taxonomy subfolders (`specs/`, `milestones/`, `guides/`), log splits, path configurability, watch-indexing archived prose, corpus re-record for old paths in signed decisions.

---

## Invariants (violation = stop and revert)

1. `convmem doctor` exits 0 after every commit
2. `pytest` passes after every commit
3. `convmem brief --stdout-only` reports no false stale alarm after bulk archive
4. No file in the "frozen" list below changes path

---

## Frozen paths (do not move in this effort)

| Path | Reason |
|------|--------|
| `convmem.py`, `mcp_server.py`, `brief.py`, `doctor.py` | CLI/MCP entrypoints |
| All flat `*.py` at repo root | Import anchors; no casual package restructure |
| `docs/inter-model/` directory | `brief.py` hardcodes inbox path |
| `docs/inter-model/LATEST.md` | SPOF: brief, MCP, all agent rules |
| `docs/inter-model/SESSION-CLOSE-RECORD.md` | Referenced by `scripts/generate-agent-protocol.sh` |
| `export_report_to_observations.py`, `extract_procedures.py` | cwd-sensitive; path-proof in a separate PR |
| `adapters/`, `config/`, `scripts/`, `systemd/`, `tests/`, `examples/` | Deploy/test conventions |

---

## Archive decision rule

A file moves to archive **only if** all of the following are true:

1. Its basename returns zero hits when grepped against `docs/inter-model/LATEST.md`, `BUILT-PLANS-2026-06-24-to-2026-06-29.md`, and any active `PLAN-*` or `HANDOFF-*` after 2026-06-24
2. It is not in the frozen list above
3. It is not in the explicit keep-list for its commit

No file moves on date alone. The grep gate is mechanical, not discretionary.

---

## Rollback policy

Each commit is independently revertible via `git revert <sha>`. If any invariant fails after a commit:

1. Revert that commit immediately
2. Investigate root cause (likely `git mv` mtime interaction with `brief.py` staleness check)
3. Fix and retry as a new commit — do not amend

If Commit 3 (bulk archive) fails verification, do not proceed to Commits 4–5.

---

## Execution

### Commit 1 — Delete dead artifacts

**Message:** `chore: delete dead artifacts (procedures.jsonl, sonnet tarball)`

```bash
rm -f procedures.jsonl sonnet-mcp-verify-full.tar.gz
rmdir review-bundles 2>/dev/null || true
```

**Verify:** `convmem doctor` exit 0, `pytest` passes.

---

### Commit 2 — Consolidate residue + resolve root LATEST

**Message:** `chore: consolidate residue soak into date bucket; resolve root LATEST (option A|B)`

```bash
mkdir -p docs/archive/inter-model/2026-06-22

# Move June-22 inter-model files currently in residue/ to the proper date bucket
git mv docs/archive/residue/*2026-06-22* docs/archive/inter-model/2026-06-22/

# Option A only:
git mv LATEST.md SYNTHESIS-STATUS.md
# Then grep root README.md for "LATEST.md" references and update to SYNTHESIS-STATUS.md

# Option B only:
# Add header to root LATEST.md: "This is the synthesis lane. Protocol handoff: docs/inter-model/LATEST.md"
```

**Verify:** `convmem doctor`, `pytest`. `grep LATEST brief.py mcp_server.py` still points only to `docs/inter-model/LATEST.md`.

---

### Commit 3 — Bulk archive June-22 soak

**Message:** `chore: archive 102 June-22 inter-model soak files to dated bucket`

**Precondition check:**
```bash
ls docs/inter-model/*2026-06-22* | wc -l   # expect ~102
```

**Grep-gated move:**
```bash
for f in docs/inter-model/*2026-06-22*; do
  base=$(basename "$f")
  if grep -rq "$base" docs/inter-model/LATEST.md \
      docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md 2>/dev/null; then
    echo "KEEP (referenced): $f"
  else
    git mv "$f" docs/archive/inter-model/2026-06-22/
  fi
done
```

**Additional moves (confirmed unreferenced):**
```bash
git mv GLOBAL-CONVMEM-PROTOCOL-PLANNER.md docs/archive/inter-model/
```

**Do not move** (explicit keep-list):
- `README.md`, `LATEST.md`, `SESSION-CLOSE-RECORD.md`
- `CONTINUE-VERIFY.md`, `VERIFICATION-MATRIX.md`, `CRUSH-VERIFY.md`
- `SOAK-REPORT-2026-06-25.md`
- `BUILT-PLANS-2026-06-24-to-2026-06-29.md`
- All `PLAN-*` and `HANDOFF-*` after 2026-06-24
- `CROSS-PROJECT-DIGEST-PILOT.md`
- `ALL-MODELS-2026-06-30-repo-organization-plan.md` (Cursor's v3)
- This runbook

**Add:** `docs/archive/inter-model/README.md`
```markdown
# Archived inter-model coordination

Date-bucketed historical soak and retired plans.
Not scanned by `brief` staleness. Active inbox: `docs/inter-model/`.
Truth: ledger + brief, not these files.
```

**Update:** `docs/inter-model/README.md` — add pointer: "Pre-2026-06-24 context: `docs/archive/inter-model/`"

**Verify (mandatory — stop if any fail):**
```bash
convmem doctor
pytest
convmem brief --stdout-only        # no false stale alarm
ls docs/inter-model/*.md | wc -l   # expect 35–45 (org meta still present)
grep -rn "2026-06-22" docs/inter-model/LATEST.md docs/inter-model/BUILT-PLANS* || echo "clean"
```

---

### Commit 4 — Flat docs index

**Message:** `docs: add docs/README.md navigation index`

Create `docs/README.md` — flat list:
- Active docs (ROADMAP, STATUS, RECOVER, SYSTEMD-DEPLOY, WORKSPACE-STANDARD, AGENT-ROLES, etc.)
- `inter-model/` inbox description
- `archive/` description
- `logs/` description
- If Option B: dual-LATEST disambiguation note
- If Option A: reference `SYNTHESIS-STATUS.md` at root for synthesis lane

No subfolders created.

**Verify:** grep docs/README.md for any path that doesn't exist.

---

### Commit 5 — Archive org-planning meta-docs (same PR, unconditional)

**Message:** `chore: archive 2026-06-30 org-planning meta-docs`

This commit fires immediately after Commit 4 — no second approval required. The planning discussion is complete once the plan is executed.

```bash
mkdir -p docs/archive/inter-model/2026-06-30-org-planning

git mv docs/inter-model/CODEX-2026-06-30-* docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-file-organization-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-organization-assessment.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-organization-red-flags.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/KIRO-2026-06-30-* docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-* docs/archive/inter-model/2026-06-30-org-planning/
```

**Keep in inbox:**
- `ALL-MODELS-2026-06-30-repo-organization-plan.md` (Cursor's v3 — canonical reference until next LATEST update)

**Update `docs/inter-model/LATEST.md`:**
```markdown
- **Repo organization (2026-06-30):** shipped. Runbook: `ALL-MODELS-2026-06-30-repo-organization-plan.md`. Decision trail: `docs/archive/inter-model/2026-06-30-org-planning/`
```

**Verify:**
```bash
convmem brief --stdout-only
ls docs/inter-model/*.md | wc -l   # expect 20–25
```

---

## Expected end state

| Metric | Before | After |
|--------|--------|-------|
| `docs/inter-model/*.md` count | ~153 | 20–25 |
| June-22 soak in inbox | ~102 | 0 (minus any grep-gate keeps) |
| Org meta in inbox | ~15 | 1 (Cursor v3 runbook) |
| Root dead files | 2 (procedures.jsonl, tarball) | 0 |
| Residue/inter-model split | 2 homes | 1 (date-bucketed) |

---

## Why this ordering (best-practice rationale)

1. **Delete before move** — reduces working set; confirms no hidden consumers before bulk operations
2. **Consolidate before bulk archive** — establishes single archive home before adding 102 files to it
3. **Resolve ambiguity before creating new docs** — Option A/B affects what Commit 4 writes
4. **Bulk move after deletion + consolidation** — largest risk operation has the cleanest possible baseline
5. **Index after content stabilizes** — docs/README.md describes the post-archive state, not an intermediate state
6. **Meta-cleanup unconditional and last** — planning artifacts are definitionally archivable once the plan lands; no second decision gate

---

## What this plan does NOT do

- Move any Python file or change any import
- Create subdirectories under `docs/` (only under `docs/archive/inter-model/`)
- Touch `scripts/generate-agent-protocol.sh` or its consumers
- Mix filesystem moves with code refactoring
- Require manual judgment during the grep gate (mechanical pass/fail)
- Leave planning artifacts in the inbox after execution

---

## Post-execution (future work, separate PRs)

- Path-proof `export_report_to_observations.py` and `extract_procedures.py` with explicit `--output`
- Optional: archive `ALL-MODELS-2026-06-30-repo-organization-plan.md` once `LATEST.md` is updated and a full `brief` cycle confirms no staleness
- Optional: `docs/ROADMAP-DRAFT.md` archive (verify no live consumers first — Cursor v3 included this but I have not confirmed it's unreferenced)

---

## Open question (non-blocking)

Cursor v3 included `docs/ROADMAP-DRAFT.md` in the Commit 3 move list. I have not verified whether active `ROADMAP.md` or other docs reference it. Recommend: grep before including. If unreferenced, add to Commit 3. If referenced, leave for a future PR.

---

## This file is final

Do not append responses. If a model disagrees, write a separate dated note — it gets archived in Commit 5 with the rest.
