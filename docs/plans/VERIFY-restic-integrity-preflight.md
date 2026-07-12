# VERIFY — Restic Integrity Preflight (Gate 6)

**Branch:** `plan/2026-07-12-restic-integrity-preflight`  
**Architecture:** [`ARCHITECTURE-restic-integrity-preflight.md`](ARCHITECTURE-restic-integrity-preflight.md)  
**Execution:** [`EXECUTION-restic-integrity-preflight.md`](EXECUTION-restic-integrity-preflight.md)

## Mechanical checks (fill after Execute)

```bash
# Hermetic
pytest -q tests/test_restic_integrity_check.py

# Happy path (local repo; may take minutes for 5% read-data)
python scripts/restic_integrity_check.py

# Intentional failure (example — exact flag per implementation)
python scripts/restic_integrity_check.py --intentional-missing-repo
# or: CONVMEM_RESTIC_ENV pointing at bad password file
```

| Check | PASS |
|-------|------|
| Default invokes structural check + `--read-data-subset 5%` + `--tag convmem-chroma` | happy-path report flags |
| Report under `~/.local/share/convmem/integrity-check/reports/` | inspect path |
| Report initialized / finalized on failure paths | intentional-failure report |
| Lock (restic exit 11) recorded distinctly | unit or live evidence |
| No `doctor.py` freshness probe for integrity reports | `rg` clean |
| No restore-drill / write-gate / chroma mutation | diff review |
| Hermetic tests PASS without live Restic | pytest |

## Evidence (fill after runs)

- Happy-path report: `~/.local/share/convmem/integrity-check/reports/integrity-20260712T182314Z.json` (argv includes `--tag convmem-chroma --read-data-subset 5%`; duration ~0.8s)
- Failure report: `~/.local/share/convmem/integrity-check/reports/integrity-20260712T182311Z.json` (`--intentional-missing-repo`, exit 10 / `restic_missing_repo`)
- Hermetic: `pytest -q tests/test_restic_integrity_check.py` → 8 passed
- Doctor probe: none added (`rg` clean on doctor freshness for integrity)
- Tip SHA: filled at commit time below

```text
Mechanical PASS: 2026-07-12 — tip PENDING_COMMIT
```
