# T0 — Kiro hook contract (Arc Runway Ledger)

Reproducible fixture for ConvMem agent-run capture. Derived from Kiro public
docs (2026-08-04 pages) plus local evidence (`kiro-cli 2.18.1`, on-disk
`~/.kiro/sessions/*/sess_*/session.json`). No live hooks installed.

## Hook file shape (repository)

Path: `.kiro/hooks/<name>.json` (project root). Schema `version: "v1"`.

Triggers used by this arc:

| Trigger | When (docs) | Can block? |
|---------|-------------|------------|
| `SessionStart` | New session begins | No |
| `Stop` | Agent finishes responding / session ends (docs disagree — see §Stop cadence) | No (may return optional block JSON; we never do) |

Action type for capture: `command` only (never `agent` — no LLM).

Recommended T4 landing shape (still `enabled: false` until Ryan grant):

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "convmem-agent-run-start",
      "trigger": "SessionStart",
      "enabled": false,
      "timeout": 15,
      "action": {
        "type": "command",
        "command": "python3 scripts/kiro-agent-run-hook.py start"
      }
    },
    {
      "name": "convmem-agent-run-stop",
      "trigger": "Stop",
      "enabled": false,
      "timeout": 15,
      "action": {
        "type": "command",
        "command": "python3 scripts/kiro-agent-run-hook.py stop"
      }
    }
  ]
}
```

## Stdin JSON (command actions)

Kiro pipes a JSON object on STDIN. Documented fields for spawn/stop-class events:

| Field | Type | Required for capture | Notes |
|-------|------|----------------------|-------|
| `hook_event_name` | string | preferred | Legacy names: `agentSpawn`, `stop` / `agentStop`. PascalCase trigger may appear as `SessionStart` / `Stop`. Adapter accepts both families. |
| `cwd` | string | yes when present | Working directory for Git fact collection. |
| `session_id` | string or absent | preferred native ID | Opaque; do not rewrite. |
| `assistant_response` | string | **forbid persist** | Present on some Stop payloads. Never write to the run ledger. |
| tool fields | object | ignore | Not used for SessionStart/Stop. |

Fixture files under `stdin/` are the canonical examples for tests.

### Native session ID resolution order

1. STDIN `session_id` if non-empty string after strip.
2. Explicit `session.json` path only if the wrapper is invoked with one (tests / fallback), via `adapters.kiro_session_jsonl.read_session_meta()` → `session_id`.
3. Else `native_session_id = null` (partial identity). Start still allowed; Stop without an exact match must emit `capture_diagnostic`, never close an arbitrary active run.

Local durable sessions use ids like `sess_<uuid>` in `session.json`. Hook STDIN may supply a bare UUID. Preserve exact source bytes; do not normalize by adding/removing `sess_`.

## Environment

No ConvMem-required env vars. Capture must not depend on undocumented `KIRO_*`
variables. Optional future: `CONVMEM_AGENT_RUN_LOG` override for tests only.

`USER_PROMPT` appears in docs for UserPromptSubmit only — out of scope; never read.

## Exit / stdout / stderr semantics (fail-open)

| Exit | Kiro behavior (docs) | ConvMem adapter policy |
|------|----------------------|------------------------|
| 0 | Success; **SessionStart stdout may be injected into agent context** | Always exit 0 for fail-open. Emit **empty stdout**. |
| 2 | Block (PreToolUse / UserPromptSubmit / PreTaskExec) | Never used for SessionStart/Stop capture. |
| other | Warning via stderr; execution continues | Avoid; prefer exit 0 + `capture_diagnostic` in the run log. |

Stop may return `{"decision":"block","reason":"..."}` on stdout to continue the
agent turn. Capture adapter must never emit a block decision.

Writer failure: still exit 0, empty stdout; append or best-effort diagnostic if
possible; do not claim durable capture success on stderr in a way that blocks
the client.

## Retry / idempotency

Public docs do not guarantee automatic redelivery. Adapter must still treat a
second identical delivery as idempotent:

- Derive a stable delivery key from `(client=kiro, hook_event_name|trigger, session_id|null, cwd|null, source_ref)`.
- Reuse the same `event_id` for that key so exact retries do not create a second run.
- Same `event_id` with different payload bytes is an error / corruption signal.

## Stop cadence (docs conflict — soak gate)

| Source | Stop meaning |
|--------|----------------|
| `kiro.dev/docs/hooks.md` | "When the agent finishes responding" (per-turn risk) |
| `kiro.dev/docs/cli/v3/hooks-migration.md` | "Session ends" |
| CLI 2.x reference | `agentStop`/`stop` → "Session ends" |

**MVP adapter policy (architecture lock):** treat Stop as `run_stopped` lookup
by exact client + native_session_id + repository. Zero/ambiguous matches →
diagnostic only. Empirically verify cadence during Ryan's disposable soak
before enabling production capture. If Stop is per-turn, do not silently close
runs every turn — escalate for a follow-up edge policy (still no recency close).

## Stop / fallback behavior

| Input | Result |
|-------|--------|
| Explicit `run_id` (CLI / wrapper flag) | Stop that run |
| Exact unique active match on client+native_session_id+repository | Stop that run |
| Zero matches | `capture_diagnostic` (unmatched stop) |
| Multiple matches | Ambiguity diagnostic; do not close any |
| Missing native ID and no run_id | Diagnostic; do not invent identity |

Terminal status must come from the adapter argument (`completed` / `aborted` /
`unknown`), never from wall-clock age.

## Git command fixture

See `git/commands.json`. Only confirmed command output is recorded. Non-Git
cwd → repository/branch/head null or unknown. Detached HEAD → `branch` /
`detached` as specified by the collector, never invent a branch from a SHA.

## Local environment notes (2026-08-20)

- `kiro-cli --version` → `2.18.1`
- Logs show: `[KiroAgent] v2 hooks loaded 0 standalone hooks from .kiro/hooks/`
- Sampled 341 `session.json` files: all `id` values start with `sess_`
- No live `.kiro/hooks/` capture files are installed by this T0 package

## References

- https://kiro.dev/docs/hooks.md
- https://kiro.dev/docs/hooks/types.md
- https://kiro.dev/docs/hooks/actions.md
- https://kiro.dev/docs/cli/v3/hooks-migration.md
- https://kiro.dev/docs/cli/2x-reference.md
