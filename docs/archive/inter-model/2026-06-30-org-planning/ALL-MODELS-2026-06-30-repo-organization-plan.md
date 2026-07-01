# ALL-MODELS: repo organization — execution runbook (v3 final)

**To:** Ryan + any model executing this plan  
**From:** Cursor (merge lead) — incorporates Kiro synthesized critique, Crush new-flags, Codex forward plan  
**Date:** 2026-06-30  
**Status:** **Final runbook — execute on Ryan `ship`**

**This is the only file to follow.** Individual plans/assessments → archived in Commit 5.

**Stop list:** [CURSOR-2026-06-30-repo-organization-red-flags.md](CURSOR-2026-06-30-repo-organization-red-flags.md)

**Chains to:** `dec_prop_20260630_220459_1e3f`

---

## Ryan: decide before Commit 2 (required)

Pick **one** — blocks Commit 3 until chosen:

| Option | Action |
|--------|--------|
| **A — Rename** (Kiro, Crush, Codex) | `git mv LATEST.md SYNTHESIS-STATUS.md`; update root [README.md](../../README.md) |
| **B — Document** (Cursor) | Keep root `LATEST.md`; dual-lane note in Commit 4 `docs/README.md` |

**Never rename or relocate [docs/inter-model/LATEST.md](LATEST.md).**

Reply: `ship A` or `ship B` (or `ship` + pick at Commit 2).

---

## Goal

Cleaner repo layout without breaking runtime paths. **Ledger + brief = truth.** Archive inter-model soak chatter; keep active handoffs.

---

## Preconditions (run once — Kiro)

```bash
cd ~/Projects/convmem
convmem doctor                    # exit 0
pytest                            # baseline green — note count
ls docs/inter-model/*2026-06-22* | wc -l    # expect 102
ls docs/inter-model/*.md | wc -l            # expect ~153 (incl. org meta)
ls docs/archive/residue/*2026-06-22*        # preview residue glob (9 files)
```

---

## Frozen — do not move

`convmem.py`, `mcp_server.py`, `brief.py`, `doctor.py`, flat library `*.py`, `docs/inter-model/` **path**, `docs/inter-model/LATEST.md`, `docs/inter-model/SESSION-CLOSE-RECORD.md`, cwd-sensitive export/extract scripts.

No `src/convmem/`. No taxonomy subfolders. No log split. No Python refactors in this PR.

---

## Archive decision rule (Codex — Crush flag #7)

**If grep finds the basename in any active doc, keep the file in the inbox.** Only move files with **zero live references** in:

- `docs/inter-model/LATEST.md`
- `docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`
- Other active handoffs you touch

No exceptions for date alone.

---

## Rollback (Kiro flag #8)

Each commit is independently revertible: `git revert <commit>`. If `brief --stdout-only` false-stales after Commit 3, revert Commit 3 only; investigate `git mv` mtime before retry.

---

## Commit 1 — Cleanup

**Message:** `chore: delete dead artifacts and consolidate residue soak files`

```bash
rm -f procedures.jsonl sonnet-mcp-verify-full.tar.gz
rmdir review-bundles 2>/dev/null || true

mkdir -p docs/archive/inter-model/2026-06-22
git mv docs/archive/residue/*2026-06-22* docs/archive/inter-model/2026-06-22/
# Leaves in residue/: CONVERSATION_COMPACT, README-FOR-CHATGPT, KIRO-TO-ALL-MODELS,
# HANDOFF-CURSOR-AUTO-COMPOSER-2026-06-25-soak, README.md
```

**Verify:** `convmem doctor`, `pytest`

---

## Commit 2 — Resolve root LATEST (Ryan Option A or B)

**Message:** `chore: resolve root LATEST.md synthesis lane (option A|B)`

**Option A:**

```bash
git mv LATEST.md SYNTHESIS-STATUS.md
# grep README.md root LATEST references → update to SYNTHESIS-STATUS.md
```

**Option B:** add header comment to root `LATEST.md` pointing to `docs/inter-model/LATEST.md` for protocol handoff.

**Verify:** `grep LATEST brief.py mcp_server.py` — runtime uses `docs/inter-model/LATEST.md` only

---

## Commit 3 — Bulk archive June-22 soak

**Message:** `chore: archive June-22 inter-model soak files to dated bucket`

**Glob safety:** `docs/inter-model/*2026-06-22*` does not match any keep-list file (dates/patterns differ). No manual exclusions from glob.

**Keep in inbox** (not matched by glob — do not move):

- `README.md`, `LATEST.md`, `SESSION-CLOSE-RECORD.md`
- `CONTINUE-VERIFY.md`, `VERIFICATION-MATRIX.md`, `CRUSH-VERIFY.md`, `SOAK-REPORT-2026-06-25.md`
- `BUILT-PLANS-2026-06-24-to-2026-06-29.md`
- `PLAN-2026-06-25-surface-coverage.md`, `PLAN-2026-06-29-streaming-synthesis.md`, `PLAN-2026-06-29-searchable-cli-chats-HANDOFF.md`
- `HANDOFF-CLAUDE-CLOUD-2026-06-29-qwen-continue-verify.md`, `HANDOFF-CLAUDE-CLOUD-2026-06-25-global-protocol.md`, `HANDOFF-CODEX-2026-06-29-continue-workspace-smoke.md`, `HANDOFF-DEEPSEEK-R1-2026-06-29-continue-workspace-smoke.md`
- `CROSS-PROJECT-DIGEST-PILOT.md`
- `ALL-MODELS-2026-06-30-repo-organization-plan.md` (this runbook)

```bash
mkdir -p docs/archive/inter-model/2026-06-22

for f in docs/inter-model/*2026-06-22*; do
  base=$(basename "$f")
  if grep -rq "$base" docs/inter-model/LATEST.md \
      docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md 2>/dev/null; then
    echo "KEEP (live consumer): $f"
  else
    git mv "$f" docs/archive/inter-model/2026-06-22/
  fi
done

git mv GLOBAL-CONVMEM-PROTOCOL-PLANNER.md docs/archive/inter-model/
git mv docs/ROADMAP-DRAFT.md docs/archive/inter-model/
# No root stub. No docs/archive/plans/ subfolder.
```

**Add** `docs/archive/inter-model/README.md`:

```markdown
# Archived inter-model coordination

Date-bucketed soak and retired plans. **Not** scanned by `brief` staleness.
Active inbox: `docs/inter-model/`. Truth: ledger + brief.
```

**Update** [docs/inter-model/README.md](README.md) — pointer to `docs/archive/inter-model/` for pre-2026-06-24 context.

**Verify after Commit 3 (mandatory — do not proceed if fail):**

```bash
convmem doctor
pytest
convmem brief --stdout-only    # staleness sane; inbox count dropped
ls docs/inter-model/*.md | wc -l   # expect ~35–45 (org meta still present)
grep -rn "docs/inter-model/[A-Z].*2026-06-22" docs/ README.md STATUS.md || true
```

---

## Commit 4 — Docs index

**Message:** `docs: add flat docs/README.md navigation index`

Create [docs/README.md](../README.md) — flat list of active docs, `inter-model/` inbox, `archive/`, `logs/`. If Option B, document dual-LATEST lanes; if Option A, reference `SYNTHESIS-STATUS.md`.

No new subfolders.

**Verify:** grep for broken paths in README, STATUS, root README

---

## Commit 5 — Meta-close (same PR — unconditional, Kiro flag #4)

**Message:** `chore: archive 2026-06-30 org-planning meta-docs`

Runs **immediately after Commit 4** in the same PR. No second Ryan approval.

```bash
mkdir -p docs/archive/inter-model/2026-06-30-org-planning

git mv docs/inter-model/CODEX-2026-06-30-* docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-file-organization-plan.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-organization-assessment.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CURSOR-2026-06-30-repo-organization-red-flags.md docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/KIRO-2026-06-30-* docs/archive/inter-model/2026-06-30-org-planning/
git mv docs/inter-model/CRUSH-2026-06-30-* docs/archive/inter-model/2026-06-30-org-planning/
# KEEP: ALL-MODELS-2026-06-30-repo-organization-plan.md
```

Update [LATEST.md](LATEST.md) — one bullet:

```markdown
- **Repo organization:** shipped (2026-06-30). Runbook: `ALL-MODELS-2026-06-30-repo-organization-plan.md`. Trail: `docs/archive/inter-model/2026-06-30-org-planning/`
```

**Verify:**

```bash
convmem brief --stdout-only
ls docs/inter-model/*.md | wc -l   # expect ~20–25 operational files
scripts/verify-continue.sh         # unlikely to fail; run if protocol docs moved
```

---

## End state

| Metric | Before | After Commit 5 |
|--------|--------|----------------|
| Inbox `*.md` count | ~153 | ~20–25 |
| June-22 soak in inbox | ~102 | 0 (minus grep keeps) |
| Org meta in inbox | ~15 | 0 (except this runbook) |
| Root clutter | procedures.jsonl, tarball | gone |

---

## Provenance (merged from)

Codex forward plan · Kiro execution plan + synthesized critique · Crush execution plan + critiques + new flags · Cursor red-flags + assessments

**Do not append to this file.** New notes → separate dated doc → Commit 5 archives them.

---

## Handoff

**Ryan:** `ship A` or `ship B`  
**Executor:** Commits 1–5 in order; stop if Commit 3 verify fails.
