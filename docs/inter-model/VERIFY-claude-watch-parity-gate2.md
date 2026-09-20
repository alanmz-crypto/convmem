# VERIFY — Claude Watch Parity Gate 2

**Arc:** Claude Watch Parity
**Code revision:** namespace execute — bubblewrap launcher, vault capture, control-root lifecycle
**Review tip:** exact HEAD of `fix/2026-09-20-claude-gate2-namespace-execute` (worktree
`/tmp/convmem-gate2-namespace-execute`, base `e007a22`)
**Predecessor:** local safety corrective `e007a22` (findings #1, #3–#6)
**Architecture:** `2f09469` — `docs/plans/ARCHITECTURE-claude-watch-parity.md`
**Plan:** `EXECUTION-claude-watch-parity-boundary.md` (E1–E4)
**Live-source canary:** `NOT_RUN` (Ryan grant required; hermetic harness only)

## Scope delivered (namespace execute)

Implements descriptor-bound bubblewrap namespace for Gate 2 finding #2 per
architecture `2f09469` and handoff C1–C4:

| Condition | Implementation |
|---|---|
| **C1** Control-root create/reopen | `create_control_root` / `_reopen_control_root` via trusted parent; `mkdirat` 0700; dirfd opens; uid/mode 0700; common `st_dev` |
| **C2** Recoverable crash evidence | Only `CRASH_EXIT=86` recoverable; other exits quarantine; one diagnostic rerun in `run_worker` |
| **C3** Marker invariant | `.active` / `.quarantined` via held control dirfd + `fsync`; exclusive `flock` on control dirfd |
| **C4** Worker output pipes | `subprocess.PIPE` stdout/stderr; `close_fds=True`; fixed `pass_fds`; worker `_assert_stdio_pipes()`; mountinfo scrub |

### Core mechanism

1. Validate `/usr/bin/bwrap` 0.12.0+, non-setuid; `_probe_bwrap_namespace()` disposable probe
2. Control root with sibling `scratch` + `snapshot-vault` (`prepare_fixture_env` / `create_control_root`)
3. Host Gate 0 with watch-root disjointness (`assert_watch_roots_disjoint` + `watch.watch_roots` pattern; hermetic tests use empty watch roots)
4. Host capture: `O_TMPFILE`/`linkat` to vault as `<capture-id>.jsonl` (128-bit hex)
5. bwrap: `--bind-fd scratch` → `/canary-root`; `--ro-bind-fd snapshot` → granted Claude path; `--ro-bind-data config`
6. `HOME=/canary-root/home`; unchanged coordinator with fake providers; namespace config uses `/canary-root/...` paths
7. Post-run snapshot revalidation + vault cleanup via held dirfd
8. Post-run Gate 0 + watch-root disjointness recheck

### Host binding manifest (no host-sensitive values in evidence)

| Mount | Mode |
|---|---|
| `/usr`, `/bin`, `/lib`, `/lib64` | read-only |
| `/home/lauer/miniforge3` | read-only (Python runtime) |
| repo → `/app` | read-only |
| `/tmp`, `/run` | tmpfs |
| scratch dirfd → `/canary-root` | read-write bind-fd |
| snapshot dirfd → `.../granted/<alias>.jsonl` | read-only bind-fd |
| config memfd → `.../config.toml` | read-only bind-data |

**Execution host:** Linux `7.2.6-arch2-1`; bubblewrap `0.12.0`; unprivileged user namespaces enabled.

## Changed files (this execute slice)

- `claude_incremental_canary.py`
- `tests/claude_incremental_canary_worker.py`
- `tests/test_claude_incremental_canary.py`
- `tests/test_claude_incremental_canary_namespace.py` (new)
- `docs/inter-model/VERIFY-claude-watch-parity-gate2.md`

## Commands and results

```bash
/home/lauer/Projects/convmem/.venv/bin/python -m pytest \
  tests/test_claude_incremental_canary.py \
  tests/test_claude_incremental_canary_namespace.py -q
# 56 passed (43 unit + 13 namespace integration)

/home/lauer/Projects/convmem/.venv/bin/python -m pytest \
  tests/test_claude_gate1_hermetic_smoke.py \
  tests/test_claude_incremental_jsonl_route.py \
  tests/test_claude_jsonl_prefix_adapters.py \
  tests/test_claude_session_jsonl.py \
  tests/test_kiro_session_jsonl.py \
  tests/test_codex_jsonl_prefix_adapters.py \
  tests/test_codex_incremental_jsonl_route.py \
  tests/test_codex_history_jsonl.py \
  tests/test_codex_rollout_jsonl.py \
  -q
# 112 passed
```

## Static diff checks

| Surface | Status |
|---|---|
| `incremental_jsonl.py` | unchanged |
| `incremental_jsonl_isolation.py` | unchanged |
| `chroma_write_store.py` | unchanged |
| Watcher / sources / services / activation | unchanged |
| Gate 2 PASS claimed | **no** — Security Review not requested |
| PR opened | no |

## Known limits

- Live-source canary **NOT_RUN**.
- `NO_GATE2_ROUTE` fallback remains if bubblewrap fitness gates fail on a future host.
- Matrix append inside namespace copies grant to writable `canary-slug` path when grant mount is read-only (host still owns vault capture).
- Full E5 regression matrix (Kiro/Codex route suites) not run in this slice.

**TL;DR [Arc Claude Watch Parity]:** Namespace execute landed on
`fix/2026-09-20-claude-gate2-namespace-execute`; 56 focused tests PASS on primary host;
finding #2 mechanism implemented per `2f09469` C1–C4; live canary NOT_RUN; Gate 2 PASS not claimed.
