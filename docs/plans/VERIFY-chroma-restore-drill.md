# VERIFY — Chroma Restore Drill

**Branch:** `plan/2026-07-12-chroma-restore-drill`  
**Architecture:** [`ARCHITECTURE-chroma-restore-drill.md`](ARCHITECTURE-chroma-restore-drill.md)  
**Execution:** [`EXECUTION-chroma-restore-drill.md`](EXECUTION-chroma-restore-drill.md)

## Mechanical checks

```bash
# From worktree or checkout on the plan branch:
pytest -q tests/test_chroma_restore_drill.py tests/test_eval_retrieval.py -k chroma_dir

# Happy path (explicit snapshot — never "latest"):
python scripts/chroma_restore_drill.py --snapshot <SHORT_ID>

# Intentional failure:
python scripts/chroma_restore_drill.py --intentional-missing-snapshot
```

| Check | PASS |
|-------|------|
| Verify-only open never calls `get_or_create_collection` | unit test |
| Discover restored root under run dir | unit test + happy-path report |
| Mandatory offline checks (counts, pinned fixture, vector top-3) | happy-path report PASS |
| Logical fingerprint identical before/after (collections + embedding ids; sqlite/HNSW byte churn on read excluded) | happy-path report |
| Semantic SKIP or PASS (not FAIL on Ollama down) | happy-path report |
| Run dir deleted; report retained outside it | inspect paths in report |
| Missing snapshot exits nonzero + report | intentional-failure report |

## Evidence (fill after runs)

- Happy-path report: `~/.local/share/convmem/restore-drill/reports/drill-20260712T174915Z.json` (snapshot `1584dccd`)
- Failure report: `~/.local/share/convmem/restore-drill/reports/drill-20260712T174731Z.json` (`--intentional-missing-snapshot`)
- Tip SHA: `912431f`

```text
Mechanical PASS: 2026-07-12 — tip 912431f
```
