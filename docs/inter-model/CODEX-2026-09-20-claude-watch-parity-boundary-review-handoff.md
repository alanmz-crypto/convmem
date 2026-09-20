# [Arc Claude Watch Parity] Boundary Architecture Review Handoff

**For:** Kiro

**Lane:** design review only

**Implementation/live authority:** none

## Review target

Review the exact pushed tip of `plan/2026-09-20-claude-watch-parity-boundary`.

Primary files:

- `docs/plans/ARCHITECTURE-claude-watch-parity.md`
- `docs/plans/EXECUTION-claude-watch-parity-boundary.md`
- `docs/plans/STATUS-claude-watch-parity.md`

## Decision

The plan chooses a descriptor-bound bubblewrap namespace for Gate 2 finding #2.
The existing coordinator runs unchanged at `/canary-root`; host capture first
publishes an immutable snapshot through the held unbound-vault descriptor, then
the launcher binds that snapshot at a normal Claude project path under
`HOME=/canary-root/home`.
Shared-code authority changes are rejected for this slice because they would
touch the production Chroma writer and `convmem.py add` path.

Cursor's five local corrections are separately pushed at
`e007a22b24754a93d9cbd15d02269d422d371c4a`; they are
inputs, not accepted evidence. The architecture has Kiro PASS; Gate 2
implementation still has no PASS.

## Review state

Kiro PASSed exact tip `290294d093fc723313bc396518b14000857b6f1a`
with four required Execute conditions. The successor copies those conditions
into the normative plan without changing the selected architecture.

## Carry-forward questions

1. C1: Does create/reopen now require trusted-parent dirfd operations,
   no-follow directory opens, effective-uid ownership, exact `0700`, and one
   filesystem?
2. C2: Is recoverable crash evidence limited to injected `CRASH_EXIT`, with one
   clean diagnostic rerun for every other termination?
3. C3: Does post-run failure end atomically with `.quarantined` present and
   `.active` absent, followed by directory fsync?
4. C4: Are stdout/stderr launcher-created pipes with no host-file redirection,
   plus pipe and literal-leak assertions?

The baseline is intentionally precise: Gate 2 adds the Claude adapter and
`incremental_jsonl_formats.py` registry entry, while `incremental_jsonl.py`,
`incremental_jsonl_isolation.py`, and `chroma_write_store.py` remain unchanged
from merged base `e6a0634`. Do not treat either category as the other.

Return PASS carry-forward or identify an inaccurate C1–C4 transcription on the
full exact SHA. Review grants no implementation, PR, live source, canary,
routing, watcher, or activation action.

**TL;DR [Arc Claude Watch Parity]:** Check only the C1–C4 transcription into the
already-PASSed namespace architecture; Gate 2 implementation remains closed and
protected shared runtime files remain unchanged.
