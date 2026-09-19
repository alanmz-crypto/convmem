# VERIFY — Claude Watch Parity Gate 2

**Arc:** Claude Watch Parity
**Code revision:** `a6d70eaa7cc4445a236078a381b339cccf935ae9` (last implementation/test commit)
**Review tip:** `cursor/claude-watch-parity-gate2-b20a` — Kiro reviews the exact pushed branch HEAD after this VERIFY correction
**Base:** `e6a0634c214cf07c89b551d13410bb276a93b38d` (`origin/main` after Gate 1 #311)
**Plan:** `a811f58` — `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md`
**Live-source canary:** `NOT_RUN` (Ryan grant required; hermetic harness only)

## Scope delivered

- `adapters/claude_session_jsonl.py`: shared `_accepted_message()` mapper;
  `parse_complete_prefix()` via `complete_prefix_view`; byte-tolerant
  `read_session_meta()` for invalid UTF-8 lines in the prefix scan path.
- `incremental_jsonl_formats.py`: `jsonl_claude_session` spec
  (`claude-complete-prefix-v1`); `ISOLATED_CLAUDE_FORMATS`; union into
  `ALL_ISOLATED_FORMATS`; `KIRO_ROUTE_FORMATS` unchanged.
- `claude_incremental_canary.py` + `tests/claude_incremental_canary_worker.py`:
  hermetic Gate 0, frozen-source validation, read-only capture, scratch matrix
  using production `IncrementalJsonlCoordinator` inside `IsolationBoundary`.
- Focused tests: prefix, route/replay/fallback/repair/isolation, canary contract.
- Production surfaces **not** changed: `incremental_jsonl.py`, watcher config,
  sources, services, activation.

## Routing oracle

| Condition | Expected routed formats |
|---|---|
| Default (`CONVMEM_INCREMENTAL_ROOT` absent) | `jsonl_kiro_session` only |
| Isolation root present (`isolated_codex=True`) | Kiro + Codex history/rollout + Claude session |

Verified by `test_claude_format_spec_and_default_routing` and existing Codex/Kiro
route regressions (72 focused tests, all PASS).

## Commands and results

Environment: Python 3.12 venv in worktree (`.venv`), deps from `requirements.txt`.

```bash
cd /tmp/convmem-gate2-worktrees/claude-watch-parity-gate2
.venv/bin/python -m pytest \
  tests/test_claude_session_jsonl.py \
  tests/test_claude_jsonl_prefix_adapters.py \
  tests/test_claude_incremental_jsonl_route.py \
  tests/test_claude_incremental_canary.py \
  tests/test_codex_jsonl_prefix_adapters.py \
  tests/test_codex_incremental_jsonl_route.py \
  -q
# 72 passed in ~21s

.venv/bin/python -m compileall -q .
# exit 0

.venv/bin/pylint adapters/claude_session_jsonl.py incremental_jsonl_formats.py \
  claude_incremental_canary.py tests/claude_incremental_canary_worker.py \
  tests/test_claude_jsonl_prefix_adapters.py \
  tests/test_claude_incremental_jsonl_route.py \
  tests/test_claude_incremental_canary.py
# rated 9.85/10 (informational warnings only)

git diff --check e6a0634c214cf07c89b551d13410bb276a93b38d..HEAD
# exit 0

git diff origin/main -- incremental_jsonl.py watch.py config/
# (empty — unchanged)
```

## Static diff checks

| Surface | Status |
|---|---|
| `incremental_jsonl.py` | unchanged |
| `KIRO_ROUTE_FORMATS` | unchanged (`jsonl_kiro_session` only) |
| Watcher / sources / services / activation | unchanged |
| Real Claude transcript access | none |
| Network / provider calls | none |
| Production Chroma / ledger mutation | none |
| PR opened | no (Kiro exact-tip review gate) |

## Changed files (production + tests + verify)

- `adapters/claude_session_jsonl.py`
- `incremental_jsonl_formats.py`
- `claude_incremental_canary.py`
- `tests/claude_incremental_canary_worker.py`
- `tests/incremental_jsonl_helpers.py` (Claude fixture helpers)
- `tests/test_claude_jsonl_prefix_adapters.py`
- `tests/test_claude_incremental_jsonl_route.py`
- `tests/test_claude_incremental_canary.py`
- `docs/inter-model/VERIFY-claude-watch-parity-gate2.md`

## Known limits

- Live-source canary marked **NOT_RUN**; Ryan must grant exact file identity
  before any read of a real Claude transcript.
- Watcher was not stopped; Gate 0 live watcher probe requires an inactive window
  or hermetic hooks (hermetic tests use injectable probes / worker hermetic hooks).
- `read_session_meta()` now skips invalid UTF-8 lines when scanning for session
  id (prefix scan still records `skipped_invalid_utf8` per complete line).

## Evidence (content-free)

- Gate 2 hermetic matrix: first run `committed`, unchanged replay `unchanged`,
  append `committed`/`incremental` with bounded transform reuse counters.
- Prefix oracle: `parse(path) == parse_complete_prefix(path).messages` on complete
  fixtures; full byte-range coverage; partial line excluded until newline.
- Canary capture emits descriptor fields (alias, size, digests, boundaries) only;
  no transcript text in evidence payloads.

**TL;DR [Arc Claude Watch Parity]:** Isolated Claude incremental route registered;
default production routing remains Kiro-only; hermetic tests PASS; live canary
NOT_RUN; stopped for Kiro exact-tip review.
