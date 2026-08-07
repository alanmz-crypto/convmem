# Current Observation Authority Map

> **Salvage note (2026-07-24):** Landed from a previously untracked working tree for
> workspace takeover. Draft Architecture [#115](https://github.com/alanmz-crypto/convmem/pull/115)
> (`ARCHITECTURE-shadow-ledger-phase0.md`) requires the corrections below before these
> files are treated as an approved baseline. **Does not authorize** shadow hooks,
> cutover, restore-order flip, or Neutral.

## Architecture #115 corrections (applied 2026-07-24)

- **Chroma remains authoritative** for observations through Phase 0. Shadow is
  non-authoritative candidate capture only.
- Explicit exclusions remain out of shadow/observation ledger scope unless a
  later Architecture says otherwise: conversation **summaries**, and the
  governed **decision approval logs** (`decisions-approved.jsonl` /
  pending/events) which keep their own durability model.

## Files inspected

| File | Role |
|------|------|
| `observe.py` | Observation ingestion: validates, embeds, writes to Chroma + optional JSONL export |
| `ledger.py` | Record normalization (`normalize_ledger_record`), dataclasses, ledger index, related-chain queries |
| `ledger_ids.py` | Deterministic ID generation for tool-sourced observations (`obs_<site>_<producer>_<key>`) |
| `ledger_content_hash.py` | SHA-256 semantic content hash for governed decisions (schema v1) |
| `chroma_store.py` | ChromaDB PersistentClient wrapper; add/update/upsert/query/delete/supersede |
| `verify.py` | Attaches verifier opinion to existing Chroma unit; optionally ingests verification ledger record |
| `propose_decision.py` | Pending decision queue (`pending_decisions.jsonl`), approved log (`decisions-approved.jsonl`), recovery classification |
| `conflict_events.py` | Durable proposal lifecycle events (`pending_decision_events.jsonl`), governed-writer lock |
| `distill.py` | LLM-based knowledge extraction from chat chunks; produces legacy records (no ledger_id) |
| `ingest.py` | Full ingest pipeline: parse -> chunk -> summarize/distill -> embed -> Chroma + JSONL export |
| `purge_locks.py` | Advisory file locks (`fcntl.flock`) for source and export files |
| `process_lock.py` | PID-based daemon locks (watch, refine, monitor) |
| `adapters/jsonl_io.py` | Shared JSONL reading helpers |

## Source-of-truth map

| Record/state | Current authoritative location | Other copies | Reconstructable? | Migration concern |
|---|---|---|---|---|
| **Ledger-kind observations** (80 records) | Chroma `knowledge_units` collection | `knowledge_units.jsonl` (export) | Yes — JSONL has all fields needed to rebuild Chroma | Low |
| **Ledger-kind decisions** (209 records) | Chroma `knowledge_units` + `decisions-approved.jsonl` | `knowledge_units.jsonl` (export) | Partially — `decisions-approved.jsonl` is the durable intent; Chroma copy may have additional metadata (`content_hash`, `proposal_id`, `superseded`) | Medium — must reconcile which is canonical |
| **Ledger-kind verifications** (16 records) | Chroma `knowledge_units` | `knowledge_units.jsonl` (export) | Yes — JSONL has all fields | Low |
| **Legacy distilled units** (21,420 records: solution/explanation/pattern/decision) | Chroma `knowledge_units` | `knowledge_units.jsonl` (export) | **No** — JSONL lacks 14 fields that Chroma metadata may contain (`domain`, `author_model`, `ledger_id`, `ledger_kind`, `relates_to`, `site`, `severity`, `evidence_json`, `status`, `result`, `notes`, `rationale`, `proposal_id`, `content_hash`). However, legacy records in JSONL also lack these fields, so Chroma metadata for legacy records likely matches JSONL. | **High** — 21,420 records have no ledger identity |
| **Approved decision intents** (355 records) | `decisions-approved.jsonl` | Chroma (after ingestion) | Yes — this file IS the authority for approved decisions | Must remain authoritative during migration |
| **Pending decision proposals** (362 records) | `pending_decisions.jsonl` | None | Yes — standalone queue file | Low — transient state |
| **Proposal lifecycle events** | `pending_decision_events.jsonl` | None | Yes — append-only event log | Must be preserved |
| **Chroma-only records** (192 active) | Chroma `knowledge_units` | **No JSONL counterpart** | **No** — these exist only in Chroma | **Critical** — 192 records would be lost if Chroma is rebuilt from JSONL alone |
| **Superseded/tombstoned units** | Chroma metadata (`superseded: true`) | Not in JSONL export | **No** — tombstone state is Chroma-only | Medium — tombstone history would be lost |
| **Verification metadata on parent units** | Chroma metadata (`verified_confidence`, `verifier_model`, `verified_at`, `verification_result`) | Not in JSONL export | **No** — inline verification state is Chroma-only | Medium — must be extracted before migration |
| **Conversation summaries** | Chroma `conversation_summaries` collection | Not in JSONL | **No** — separate collection, not part of ledger | Out of scope for ledger-first but must not be lost |
| **Processed source hashes** | `processed.json` | None | N/A — operational state | Must be preserved for idempotent re-ingest |

## Key findings

1. **Chroma is currently authoritative.** The JSONL export (`knowledge_units.jsonl`) is a *derived* file written alongside Chroma writes, not an independent ledger. It serves as a best-effort backup/export, not a source of truth.

2. **Two distinct record populations exist:**
   - **Ledger-kind records** (305 total): Have `ledger_id`, `ledger_kind`, full metadata. These are the "new" format from `observe.py`.
   - **Legacy records** (21,420 total): Created by `distill.py` via LLM extraction from chat transcripts. Have `type` (solution/explanation/pattern/decision) but no `ledger_id`, no `ledger_kind`, no governance fields.

3. **192 Chroma-active records have no JSONL counterpart.** This means the JSONL export is incomplete — it cannot reconstruct the current Chroma state.

4. **The JSONL export is mutable, not append-only.** `_upsert_jsonl_line()` in `observe.py` rewrites the entire file to replace a matching `ledger_id`. This violates append-only ledger semantics.

5. **Decision authority is split.** `decisions-approved.jsonl` holds the durable approved intent (with `fsync`), while Chroma holds the searchable projection. The two can drift (e.g., if Chroma write succeeds but JSONL export fails, or vice versa).

6. **No single file currently serves as an append-only canonical ledger.** The system has multiple JSONL files serving different purposes (export, queue, approved log, events), but none is the sole authoritative record store.

## Stop condition assessment

The current authority **can** be identified confidently: **Chroma is authoritative today**. The JSONL files are derived/incomplete. This finding does not block the audit — it confirms the need for the proposed migration.
