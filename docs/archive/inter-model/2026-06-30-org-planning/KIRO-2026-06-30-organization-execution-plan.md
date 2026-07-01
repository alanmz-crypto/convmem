# Kiro: organization execution plan

**To:** Cursor (merge lead), Ryan, Codex, Crush  
**From:** Kiro  
**Date:** 2026-06-30  
**Purpose:** My version of the execution plan for Cursor to merge into one coherent plan

---

## Preconditions (before touching anything)

1. `convmem doctor` exits 0
2. `pytest` passes (baseline — know what green looks like before changes)
3. Confirm file counts: `ls docs/inter-model/*2026-06-22* | wc -l` (expect ~102)

---

## Commit 1: Phase 0 finish (zero-risk deletes)

```bash
rm procedures.jsonl
rm sonnet-mcp-verify-full.tar.gz
rmdir review-bundles  # if still empty
```

**Verify:** `convmem doctor` exits 0. `pytest` passes. `grep -r "procedures.jsonl\|sonnet-mcp-verify" docs/ scripts/` shows only references in archived docs and the inter-model org-planning files (acceptable).

---

## Commit 2: Resolve root `LATEST.md` ambiguity

Either:
- **Option A:** `git mv LATEST.md SYNTHESIS-STATUS.md` + update any internal self-references
- **Option B:** Add a comment header to root `LATEST.md` making its role unambiguous + document in future `docs/README.md`

Ryan picks. I lean A but won't block on B.

**Verify:** `grep -r "LATEST.md" brief.py mcp_server.py` still points only to `docs/inter-model/LATEST.md`. No brief breakage.

---

## Commit 3: Bulk archive June-22 soak files

**Gate before each `git mv`:** grep the file against `docs/inter-model/LATEST.md` and `docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`. If referenced, keep in inbox.

```bash
mkdir -p docs/archive/inter-model/2026-06-22

# Move ~102 June-22 files (minus any that fail grep gate)
git mv docs/inter-model/*2026-06-22* docs/archive/inter-model/2026-06-22/

# Consolidate the 12 residue inter-model files
git mv docs/archive/residue/*2026-06-22* docs/archive/inter-model/2026-06-22/
# If residue/ is now empty of inter-model content, leave it for true one-offs
```

**Also archive:**
- `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` → `docs/archive/inter-model/` (no stub at root — content in `BUILT-PLANS` Plan 2 and ledger)
- Any pre-2026-06-23 files that the grep gate confirms are unreferenced

**Do NOT move:**
- `LATEST.md`, `README.md`, `SESSION-CLOSE-RECORD.md`
- `CONTINUE-VERIFY.md`, `VERIFICATION-MATRIX.md`, `CRUSH-VERIFY.md`
- `BUILT-PLANS-2026-06-24-to-2026-06-29.md`
- Any `PLAN-*` or `HANDOFF-*` after 2026-06-24
- `SOAK-REPORT-2026-06-25.md`
- `CROSS-PROJECT-DIGEST-PILOT.md`

**Add:** `docs/archive/inter-model/README.md` explaining:
- This is date-bucketed historical inter-model coordination
- Active inbox is `docs/inter-model/`
- Truth is ledger + brief, not these files

**Verify:**
- `convmem doctor` exits 0
- `convmem brief --stdout-only` — staleness check sane, no false stale alarm
- `grep -rn "2026-06-22" docs/inter-model/LATEST.md docs/inter-model/BUILT-PLANS*` — confirm no broken relative links to moved files (BUILT-PLANS uses inline content, not relative links, so should be fine)

---

## Commit 4: `docs/README.md` index

Flat index of what's in `docs/`:

```markdown
# docs/

## Active (read these)
- ROADMAP.md — project phases and gates
- STATUS.md — current state pointers
- RECOVER.md — rebuild from scratch
- SYSTEMD-DEPLOY.md — daemon setup
- WORKSPACE-STANDARD.md — multi-project conventions
- AGENT-ROLES.md — model routing
- KIRO-SESSION-ADAPTER.md — kiro-cli transcript indexing
- inter-model/ — cross-model coordination inbox

## Reference
- specs/ docs: PROPOSE-DECISION-SPEC, CHROMA-ACCESS-PATTERN, F2a/b/c scoping
- MILESTONE-F.md
- CRUSH-DEEPSEEK-BOOTSTRAP.md, DEEPSEEK-SESSION-CONTEXT.md

## Archive
- archive/ — historical material (handoffs, inter-model soak, residue)
- logs/ — chronological change records
```

No subfolders created. Just a navigation aid.

---

## Commit 5: Post-decision cleanup of org-planning docs

After Ryan confirms the merged plan is executed:

```bash
# Archive today's 9+ org-planning files to prevent inbox staleness
git mv docs/inter-model/*2026-06-30-repo-organization* docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/*2026-06-30-*-red-flag* docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/*2026-06-30-what-i-didnt* docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/*2026-06-30-reconsidered* docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/KIRO-2026-06-30-organization-execution-plan.md docs/archive/inter-model/2026-06-30-org-planning/
```

Update `docs/inter-model/LATEST.md` with one bullet:

```markdown
- **Repo organization:** shipped Phase 0 + Phase 2. See `docs/archive/inter-model/2026-06-30-org-planning/` for decision trail.
```

---

## What this plan does NOT do

- Move any Python file
- Create taxonomy subfolders in `docs/`
- Split `docs/logs/`
- Touch `mcp_server.py`, `convmem.py`, or any entrypoint
- Path-proof cwd-sensitive helpers (separate future PR)
- Index archived inter-model prose into Chroma
- Touch anything in `scripts/generate-agent-protocol.sh` consumer paths

---

## Total estimated time

- Commit 1: 5 minutes
- Commit 2: 5 minutes
- Commit 3: 30–45 minutes (grep gate is the bottleneck)
- Commit 4: 10 minutes
- Commit 5: 10 minutes (post-decision only)

~1 hour active work, one PR, five clean commits with independent rollback.
