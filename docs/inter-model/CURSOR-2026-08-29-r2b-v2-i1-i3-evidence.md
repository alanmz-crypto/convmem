# R2b v2 I1–I3 reviewer-conflict corrective evidence

**Arc:** R2b Capture Authorization
**Current base:** `a19b5cbb2e431aafeda304057c98e6bd81aa0ffd` (PR #247 scope/read relocation)
**Prior reviewed candidate:** `0298d44a8a0be78f68bd2ba83632212ce6d8195a`
**Preservation tip (stale-base):** `23b8e0d0de3c1fe00e784bb5832fdb3579c6b034`
**Status:** A19b5cb recovery — NOT operational VERIFY

## Two-SHA model

| Role | SHA |
|---|---|
| `implementation_tip` | `b3bed5ca70284b80cbde9d454dce7ff2156f3a33` |
| `evidence_tip` | *(this commit)* |

`docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` generated at
`implementation_tip` with `code_revision == implementation_tip`.
Evidence commit changes only inventory JSON and this doc.

## PR #247 compatibility

- New writer route introduced: **NO**
- Existing writer route semantics changed: **NO**
- Shadow writer inventory: **PASS** (line coordinates updated on `a19b5cb`)
- R2b independent mutation scans: **PASS** (0 undocumented sinks)

## PR #245 watch/F0 compatibility

Unchanged on `a19b5cb` path — `watch.py:watch_index_event` route preserved.

## Restart/reload adjudication (Ryan lock)

Process-local I1–I3 invariant: process death/reload invalidates all prior live
lease/coverage/source-authority handles. Same textual `run_id` may start a
**new** authority chain only via fresh lock + coverage + registry proof.

Durable run-ID uniqueness across process death: **DEFERRED — PRE-I4 BLOCKER**.

## Corrective scope closed

- P0-A: lock custodian subprocess ownership
- P0-B: authority registry + one-shot mint tickets
- P0-C: full-chain cross-slice binding at authority sink
- P0-D: runtime attestation identity hardening
- P0-E: independent Chroma / FileGenerationStore / generation-pointer discovery

## Pre-I4 blocker (recorded)

Durable transaction state preventing textual `run_id` reuse after process death
is **not** in I1–I3 scope. Required before live authority / I4.
