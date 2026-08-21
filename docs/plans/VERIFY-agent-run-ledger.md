# VERIFY — Agent Run Ledger (Arc Runway Ledger)

| Field | Value |
|-------|--------|
| Branch | `feat/2026-08-20-agent-run-ledger` |
| Focused suite | `tests/test_agent_run_ledger.py` + `tests/test_agent_run_ledger_t0_contract.py` |
| Live hook install | **Not authorized** — `.kiro/hooks/*.json` ship with `enabled: false` |
| Forward ingest enable | Resolver present; association is additive when unique |

## Evidence table

| ID | Result | Evidence |
|----|--------|----------|
| V0 | PASS | Envelope fixtures for all clients; missing native ID → `partial` |
| V1 | PASS | Append-order reducer; duplicate event_id idempotent |
| V2 | PASS | Invalid schema, illegal transition, truncated tail, interior JSON, event_id collision |
| V3 | PASS | 40 concurrent writers → unique increasing sequences |
| V4 | PASS | Exact retry `created=False`; changed payload → CorruptionError |
| V5 | PASS | Ambiguous/missing stop lookup; partial identity not closed |
| V6 | PASS | `collect_git_facts` non-Git cwd → nulls |
| V7 | PASS | observed vs explicit commits remain distinct |
| V8 | PASS | Kiro hook adapter fail-open; empty stdout; assistant_response not persisted |
| V9 | PASS | No log / unique / ambiguous ingest resolver |
| V10 | PASS | Explicit ledger_id enrichment round-trip |
| V11 | PASS | 0600/0700 modes; symlink refusal |
| V12 | PASS | Cross-client envelopes reduce |
| V13 | PENDING | Full suite run before PR |

## Ryan GATEs remaining

1. Enable/install reviewed `.kiro/hooks/` bytes (`enabled: true`) for disposable soak.
2. Confirm forward-only `agent_run_id` association is acceptable in production ingest.

## Accidental live note (2026-08-20)

A Cursor smoke test briefly wrote one `run_started` for `sess_test` to
`~/.local/share/convmem/agent_runs.jsonl` before the test data-dir override
landed. File was newly created (mode 0600). No truncation/repair performed
(capture path must not rewrite). Ryan may leave or authorize separate repair.
