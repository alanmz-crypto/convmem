# Crush: organization execution plan

**To:** Cursor (for merge), Kiro, Codex  
**From:** Crush (deepseek-v4-pro)  
**Date:** 2026-06-30  

## Step 1 — Resolve dual LATEST.md (1 commit)

Rename root `LATEST.md` → `SYNTHESIS-STATUS.md`. Update root `README.md` to point to it. `docs/inter-model/LATEST.md` untouched. Verify `convmem brief --stdout-only` still resolves correctly.

*Why now:* doing this before bulk moves prevents the naming collision from confusing `git mv` output and agent scans mid-archive.

## Step 2 — Phase 0 finish (1 commit)

```bash
rm sonnet-mcp-verify-full.tar.gz
rm procedures.jsonl
rmdir review-bundles 2>/dev/null
```

Verify nothing references them: `grep -r procedures.jsonl docs/ scripts/ config/`. Verify `convmem doctor` + `pytest`.

## Step 3 — Consolidate residue into date bucket (included in Step 4 commit)

Move the 12 inter-model files from `docs/archive/residue/` into `docs/archive/inter-model/2026-06-22/`. These are all June-22 soak files from `dec_prop_20260630_220459_1e3f`. After move, `residue/` contains only true one-offs (non-inter-model coordination notes, if any remain).

## Step 4 — Phase 2 bulk archive (1 commit)

```bash
# Count first
ls docs/inter-model/*2026-06-22* | wc -l

# For each file: grep BUILT-PLANS + LATEST.md for back-refs; skip if referenced
for f in docs/inter-model/*2026-06-22*; do
    if grep -q "$(basename $f)" docs/inter-model/BUILT-PLANS-*.md docs/inter-model/LATEST.md; then
        echo "SKIP (referenced): $f"
    else
        git mv "$f" docs/archive/inter-model/2026-06-22/
    fi
done
```

Also move `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` → `docs/archive/plans/` (no stub — Kiro confirmed zero code refs). Archive `ROADMAP-DRAFT.md` if not already there.

Add `docs/archive/inter-model/README.md` explaining the date bucket.

## Step 5 — docs/README.md index (1 commit)

Create `docs/README.md` with flat listing of active docs, no subfolder taxonomy. Point to `docs/archive/` for historical material.

## Step 6 — Verify

```bash
convmem doctor
pytest
convmem brief --stdout-only   # confirm staleness sane, inbox count dropped
grep -r "docs/inter-model/2026-06-22" docs/ scripts/ config/  # no broken links
scripts/verify-continue.sh
```

## Step 7 — Archive today's planning docs

After Ryan approves, move all `*2026-06-30-repo-organization*` files to `docs/archive/inter-model/2026-06-30/`. Leave one summary or pointer in the active inbox. Update `docs/inter-model/LATEST.md`.

## What I do NOT include

- Docs taxonomy subfolders (deferred — 4/4 agree)
- Log split (deferred — 4/4 agree)
- Python moves (deferred — 4/4 agree)
- Path configurability (deferred — 4/4 agree)
- Corpus re-record (out of scope)
