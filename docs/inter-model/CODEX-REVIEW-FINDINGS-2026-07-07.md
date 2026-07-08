# Codex Review Findings

Date: 2026-07-07
Repo: `/home/lauer/Projects/convmem`

## Scope

Review of the large pending change set across:

- `doctor.py`
- `ingest.py`
- `chroma_store.py`
- `query.py`
- `refine.py`
- `scripts/deploy-builder-reference.sh`
- `scripts/verify-builder-reference.sh`
- `scripts/crush-hook-convmem-allow.sh`
- `tests/test_doctor.py`
- `tests/test_chroma_superseded.py`

## Verification

- Focused tests passed: `53 passed`
- The change set is broad but mostly coherent: cache invalidation, ingest dedupe, standing-check probes, and ranking adjustments all have direct tests.

## Findings To Recheck

1. `scripts/deploy-builder-reference.sh` does not restore `~/.config/crush/CONVMEM-RITUAL.md` when the ritual entry is missing from `global_context_paths`.
   - The new ordering logic preserves the ritual only if it already exists in the array.
   - Result: a partially migrated or manually edited config can stay invalid after deploy.
   - File reference: [`scripts/deploy-builder-reference.sh`](/home/lauer/Projects/convmem/scripts/deploy-builder-reference.sh#L159)

2. `scripts/crush-hook-convmem-allow.sh` treats search completion as session-local, even when ritual completion is inherited from the base session.
   - `_ritual_complete()` can succeed via `base_progress`, but `_seen_search()` only checks the current session progress file.
   - Result: child sessions can still get denied for survey tools even after the parent session already searched.
   - File references: [`scripts/crush-hook-convmem-allow.sh`](/home/lauer/Projects/convmem/scripts/crush-hook-convmem-allow.sh#L41) and [`scripts/crush-hook-convmem-allow.sh`](/home/lauer/Projects/convmem/scripts/crush-hook-convmem-allow.sh#L121)

## Notes

- I did not run `convmem index`.
- This log is intentionally separate from the convmem corpus until you explicitly want it indexed.
