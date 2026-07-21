# Execution Plan — R2b capture + corpus package

```
Planning Status

Phase:        Execution Planning
Characters:   Task Decomposer, Scope Guardian
Functions:    Planner
Lanes:        Cursor (docs/plan only until Ryan grant); Copilot CLI or Cursor under exact grant for live capture later
Authority:    Awaiting HITL — **R2b live capture not authorized by this document alone**
```

**Source:** Ryan direction 2026-07-20 (#2 toml-fix R2a regenerate, then #3 R2b plan)  
**Parent runbook:** [`EXECUTION-embedding-model-eval.md`](EXECUTION-embedding-model-eval.md)  
**Arc VERIFY companion:** [`VERIFY-r2b-capture.md`](VERIFY-r2b-capture.md) (stub)  
**Prior R2a run (toml-fix):** `2026-07-20-r2a-nomic-vs-mxbai-toml-fix` under `~/.local/share/convmem/eval/` + authorizations (shadow lists as real TOML arrays)

**Goal:** Shape the next pre–Gate 2 checkpoint — immutable capture + corpus package (R2b) — into bounded tasks with gates. No live capture until Ryan posts an exact grant.

---

## Tasks

| ID | Deliverable | In scope | Depends on | Gates | Execution lane |
|----|-------------|----------|------------|-------|----------------|
| T1 | Fill [`VERIFY-r2b-capture.md`](VERIFY-r2b-capture.md) checks from capture CLI + binder (`CAPTURE_FIELDS`, sidecar, restic absolute) | Docs | — | Doctor planning contract | Cursor |
| T2 | Ryan HITL: approve R2b scope (corpus sources, capture_dir under eval run root, Chroma required, overlap policy 40/30/30) | Decision | T1 stub OK | Written grant | Ryan |
| T3 | Author approved R2b run-manifest(s) + sidecars under `authorizations/` (not eval root); bind `export`, `processed`, `capture_dir`, `chroma_dir` | Auth files only | T2 | Packet integrity per VERIFY | Cursor after grant |
| T4 | Live `capture` once under VERIFY pre-state STOP + command evidence; produce corpus package + `historical_spot_check.json` | Eval capture only | T3 | VERIFY mechanical + Kiro | Named operator after grant |
| T5 | Stop for B-Accept — **not** in this arc | Out of scope | T4 | — | — |

## Out of scope

- B-Accept, C0, R3–R7, Gate 2, promotion, cleanup
- Creating Chroma under R2a shadows without a capture grant
- Overwriting prior R2a `shadow.toml` trees
- Live capture before Ryan grant + `restic_gate: PASS`

## Evidence requirements (for Execute phase)

- Absolute `restic_gate: PASS` before any eval-root capture write
- Pre-existing `capture_dir` / package paths → **STOP** (no overwrite without new auth)
- Command evidence pack (cwd, argv, exit, stdout/stderr, artifact hashes)
- Independent Kiro (or named) sign-off on VERIFY

## Arc VERIFY companion

- Path: `docs/plans/VERIFY-r2b-capture.md`
- Status: stub
- Template: `docs/plans/VERIFY-TEMPLATE.md`

## Execute entry

- First task: T1 (docs) anytime on this branch.
- Live T3–T4 only after T2 Ryan grant text naming revision, paths, and exact command tuple(s).

## Hard stops

- This PR/plan does **not** authorize R2b execution.
- Merge of planning docs ≠ grant.
