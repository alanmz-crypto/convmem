# Implementation Handoff: Arc Runway Ledger — Agent Run Identity Tracking

**Date:** 2026-08-20  
**Author:** Kiro (design review + handoff)  
**For:** Cursor (implementation)  
**Authorization:** Ryan, 2026-08-20 (verbal — Architecture + Execution lock granted after Kiro PASS)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `IN_PROGRESS` |
| **Branch** | `feat/2026-08-20-agent-run-ledger` (create from `origin/main`) |
| **Tip SHA** | see branch tip after T3–T7 commit |
| **Push status** | n/a |
| **PR** | not opened |
| **Ryan GATE** | Hook installation requires separate exact external-change grant after T0/T4 pass. Forward-only ingest association requires separate grant after V9. |
| **Track A ingest** | n/a |

---

## What to build

A durable, append-only event log that records which coding agent (Kiro, Codex, Cursor, Crush, Copilot) performed work, using deterministic capture at the infrastructure level. ConvMem gets a new correlation layer that answers "which agent/session did this work?" and "what work did this agent/session do?" with honest unknown/ambiguous results when evidence is insufficient.

**Why this exists:** After an agent finishes work, Ryan often loses track of the agent/session ID that performed it. Native session IDs are ephemeral and scattered across client-specific paths. ConvMem needs a unified, client-neutral identity ledger.

---

## Integration point

New module — no existing file is the primary target. Touches:

- **New:** `agent_run_ledger.py` — core schema, writer, reducer, query
- **New:** `scripts/kiro-agent-run-hook.py` — Kiro edge adapter for hooks
- **New:** `.kiro/hooks/agent-run-start.json` + `.kiro/hooks/agent-run-stop.json` — Kiro hook entries (NOT installed live until Ryan grant)
- **New:** `tests/test_agent_run_ledger.py` — V0–V13 verification
- **Modify (additive):** `ingest.py` ~line 198 — optional `agent_run_id` in session meta (T6, forward-only, unique-match-only)
- **Modify (additive):** `convmem.py` — new `agent-run` command group (start/stop/enrich/show/list/validate)

```python
# ingest.py integration sketch (T6 — additive only)
meta = {
    "conversation_id": conv_id or "",
    "session_id": session_id or "",
    "workspace_directory": workspace or "",
}
# NEW — optional, forward-only
run_id = _resolve_agent_run_id(client=tool, native_session_id=session_id, repository=...)
if run_id:
    meta["agent_run_id"] = run_id
```

---

## Specification

### Inputs

- Kiro hook stdin JSON (SessionStart/Stop — schema to be determined empirically in T0)
- Git working directory state (confirmed via `git rev-parse`, `git log`, `git diff --name-only`)
- Explicit enrichment from callers (`convmem agent-run enrich --run-id <id> --commits <sha> --files <path>`)

### Algorithm / behavior

```
T0: Prove Kiro hook contract with fixture (what stdin provides)
T1: Schema envelope + reducer (event-sourced, deterministic replay)
T2: Durable writer (flock sibling lock, sequence, fsync, corruption refusal)
T3: CLI surface (agent-run start/stop/enrich/show/list/validate)
T4: Kiro edge adapter (SessionStart → run_started, Stop → run_stopped)
T5: Git enrichment (head_revision, commits, files — observed vs explicit)
T6: Ingest association (optional agent_run_id for unique exact match)
T7: Explicit ledger links (obs_/dec_/ver_ enrichment)
T8: Verification package
```

### Output / contract

- `~/.local/share/convmem/agent_runs.jsonl` — append-only event log
- `~/.local/share/convmem/agent_runs.lock` — sibling flock
- File mode `0600`, directory mode `0700`
- Events: `run_started`, `run_enriched`, `run_stopped`, `capture_diagnostic`
- CLI: machine-readable JSON output mode for hooks; human-friendly default

### Constants

```python
AGENT_RUN_LOG = Path("~/.local/share/convmem/agent_runs.jsonl")
AGENT_RUN_LOCK = Path("~/.local/share/convmem/agent_runs.lock")
SCHEMA_VERSION = 1
VALID_CLIENTS = ("kiro", "codex", "cursor", "crush", "copilot", "continue", "aider", "openwebui", "unknown")
VALID_STATUSES = ("active", "completed", "aborted", "unknown")
VALID_RELATIONS = ("observed", "explicit")
```

---

## What NOT to build

- No LLM calls anywhere in capture/reduce/query path
- No historical reindex or Chroma bulk mutation
- No changes to existing `session_id`, `author_model`, `--author`, or `--signer` semantics
- No required `--run-id` argument on `convmem record`
- No semantic reconciliation or "most recent" inference
- No non-Kiro client hooks (future slices)
- No cloud sync or cross-machine replication
- No auto-repair of corrupt event logs
- No prompt/content/model-output capture in events

---

## Test expectations

Focused tests in `tests/test_agent_run_ledger.py`:

1. **V0 — Envelope fixtures:** Valid records round-trip for all clients; unknown client and missing native ID accepted explicitly
2. **V1 — Reducer replay:** Append sequence determines state, not wall-clock; duplicate exact event IDs are idempotent
3. **V2 — Corruption handling:** Invalid schema, unsupported version, illegal transition, interior JSON corruption, truncated tail all fail closed
4. **V3 — Concurrent writers:** Two+ processes with barriers → no interleave, unique increasing sequences, durable bytes
5. **V4 — Idempotency:** Same delivery retried = idempotent; same event_id with changed payload = error
6. **V5 — Missing/ambiguous ID:** Start with no native ID works; stop with no/ambiguous ID produces diagnostic, not arbitrary close
7. **V6 — Git facts:** Repository, branch, detached HEAD, dirty tree, non-Git cwd all handled truthfully
8. **V7 — Observed vs explicit:** Relations remain distinct; temporal presence ≠ authored work
9. **V8 — Kiro hook fixture:** Successful, missing-ID, duplicate, and writer-failure cases; fail-open; no prompts captured
10. **V9 — Ingest compatibility:** No run log = existing behavior unchanged; unique match adds `agent_run_id`; ambiguous match omits it
11. **V10 — Ledger links:** Explicit obs_/dec_/ver_ enrichment round-trips without changing ledger content
12. **V11 — Permissions:** Private file/dir; symlink refusal visible
13. **V12 — Cross-client envelopes:** Same reducer handles Kiro/Codex/Cursor/Crush/Copilot fixtures
14. **V13 — No regressions:** Full existing test suite passes

---

## Acceptance criteria

- [ ] `agent_run_ledger.py` implements envelope, writer, reducer, and query
- [ ] `convmem agent-run start/stop/enrich/show/list/validate` commands work
- [ ] Kiro hook files exist in `.kiro/hooks/` (disabled by default — not installed live)
- [ ] V0–V13 tests pass
- [ ] Existing test suite passes unchanged (no regressions)
- [ ] Ruff / pylint clean per repo gates
- [ ] `convmem doctor` passes (no new warnings)
- [ ] No LLM dependency in capture/reduce/query
- [ ] Missing/ambiguous identity never silently resolved
- [ ] Concurrent append proven safe under test

---

## Branch convention

```
feat/2026-08-20-agent-run-ledger
```

Push immediately after each commit. Open PR when acceptance criteria pass. Ryan squash-merges.

---

## Related files

| What | Path |
|------|------|
| Architecture authority | `docs/plans/ARCHITECTURE-agent-run-ledger.md` (on `plan/2026-08-20-agent-run-ledger`) |
| Execution order + tests | `docs/plans/EXECUTION-agent-run-ledger.md` (on `plan/2026-08-20-agent-run-ledger`) |
| Arc brief | `docs/plans/STATUS-agent-run-ledger.md` (on `plan/2026-08-20-agent-run-ledger`) |
| Existing client vocabulary | `adapters/detect.py` |
| Existing session metadata | `ingest.py` (lines 180–205) |
| Kiro session parser | `adapters/kiro_session_jsonl.py` |
| JSONL event patterns | `shadow_sink.py`, `propose_decision.py`, `conflict_events.py` |
| Writer attestation pattern | `chroma_write_store.py` (lines 60–80) |
| Kiro session.json example | `~/.kiro/sessions/*/sess_*/session.json` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed (or on pushed branch)
- [x] `LATEST.md` bullet at top with link and resume state
- [x] `STATUS-agent-run-ledger.md` Update Log line (on planning branch)
- [x] Branch pushed

**Implementer (picking up):**

- [x] Read this file before first edit
- [x] Read `ARCHITECTURE-agent-run-ledger.md` and `EXECUTION-agent-run-ledger.md`
- [x] `convmem work start --worktree feat agent-run-ledger`
- [x] State Goal / role / system state / next action per STATUS
- [x] T0 hook contract fixture landed (`tests/fixtures/agent_run_ledger/`)
