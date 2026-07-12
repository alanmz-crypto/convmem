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

- Happy-path report: _(path)_
- Failure report: _(path)_
- Tip SHA: _(sha)_

```text
Mechanical PASS: YYYY-MM-DD — tip <sha>   # Cursor fills after T4–T5
```
