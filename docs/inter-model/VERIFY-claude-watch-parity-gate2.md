# VERIFY — Claude Watch Parity Gate 2

**Arc:** Claude Watch Parity
**Code revision:** capability-bound redesign — replace pathname reopen, post-publication
refusal, caller-supplied Gate 0 authority, and dictionary evidence
**Review tip:** `fix/2026-09-20-claude-gate2-cap-bound` @ `3d00819d9f4b02a7700a7bf28768f987c5f6aa88` — Copilot exact-tip re-audit before Kiro (Kiro blocked until Copilot PASS)
**Predecessor tip (FAIL):** `a5ccc68f47f54c9cfabf00411d1c292b3185864d`
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
  **capability-bound redesign**
  - Isolation root opened and validated once; directory descriptor + stat identity
    retained; descendants resolved via anchored `dir_fd` only (no pathname reopen).
  - Publication is the final transition: stage+fsync temp under destination dirfd,
    revalidate source identity/digest, then directory-relative atomic rename only.
    Failures before publish unlink the temp via dirfd; no post-publish refusal that
    must locate a published inode by pathname.
  - Mutable commands call one internal Gate 0 routine; caller/env authority objects,
    reports, and digests are refused. Report must pass and is bound to open root
    identity, token marker, config digest, and current watcher result; freshness and
    config are re-read before the first mutable transition.
  - Evidence is closed typed dataclasses/enums (`Gate0Evidence`, `MatrixEvidence`,
    `CaptureEvidence`, …); paths only via `RelativePath` / `SourceAlias`; no type
    coercion; serialize/hash only validated objects.
- Focused tests: prefix, route/replay/fallback/repair/isolation, canary contract,
  plus adversarial capability-bound regressions.
- Production surfaces **not** changed: `incremental_jsonl.py`, watcher config,
  sources, services, activation.

## Routing oracle

| Condition | Expected routed formats |
|---|---|
| Default (`CONVMEM_INCREMENTAL_ROOT` absent) | `jsonl_kiro_session` only |
| Isolation root present (`isolated_codex=True`) | Kiro + Codex history/rollout + Claude session |

Verified by `test_claude_format_spec_and_default_routing` and existing Codex/Kiro
route regressions.

## Commands and results

Environment: Python 3.12 venv (`.venv` from main checkout), deps from `requirements.txt`.

```bash
cd .worktrees/fix-2026-09-20-claude-gate2-cap-bound
/home/lauer/Projects/convmem/.venv/bin/python -m pytest \
  tests/test_claude_session_jsonl.py \
  tests/test_claude_jsonl_prefix_adapters.py \
  tests/test_claude_incremental_jsonl_route.py \
  tests/test_claude_incremental_canary.py \
  tests/test_codex_jsonl_prefix_adapters.py \
  tests/test_codex_incremental_jsonl_route.py \
  -q
# 97 passed (84 prior regressions + adversarial capability-bound tests)

/home/lauer/Projects/convmem/.venv/bin/python -m compileall -q \
  claude_incremental_canary.py tests/claude_incremental_canary_worker.py \
  tests/test_claude_incremental_canary.py
# exit 0

git diff --check a5ccc68f47f54c9cfabf00411d1c292b3185864d..HEAD
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
| PR opened | no (Copilot exact-tip gate; Kiro blocked until Copilot PASS) |

## Changed files (this corrective)

- `claude_incremental_canary.py`
- `tests/claude_incremental_canary_worker.py`
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
- Canary capture emits relative-path descriptor fields only; no transcript text
  and no absolute credential/transcript paths in evidence payloads.
- Adversarial: root replacement after Gate 0, destination symlink substitution,
  source removal / temp rename cleanup, forged Gate 0 report/digest, stale marker,
  config replacement, closed evidence coercion/injection refusals.

**TL;DR [Arc Claude Watch Parity]:** Capability-bound redesign replaces the four
Copilot residual mechanisms (anchored root capability, publication-final rename,
internal Gate 0, closed typed evidence); 97 focused tests PASS; live canary
NOT_RUN; stopped for Copilot exact-tip re-audit before Kiro.
