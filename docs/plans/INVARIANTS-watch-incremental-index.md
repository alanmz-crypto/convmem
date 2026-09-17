# INVARIANTS — Incremental Codex JSONL transform reuse (S0 inventory)

**Arc: Trapdoor Hunt** · **Issue:** [#286](https://github.com/alanmz-crypto/convmem/issues/286) · **Baseline:** `ef4a7dd` + plan tip `6b62f0f` · **Date:** 2026-09-17

Code-derived oracle map for S0–S3 Execute. This document pins behavior the
implementation must preserve; it is not an authorization grant.

## Format detection (`adapters/detect.py`)

| Format | Detector | Parser module |
|---|---|---|
| `jsonl_kiro_session` | `sess_*/messages.jsonl`, not under `snapshots/` | `adapters.kiro_session_jsonl` |
| `jsonl_codex_history` | resolved path equals `~/.codex/history.jsonl` | `adapters.codex_history_jsonl` |
| `jsonl_codex_rollout` | `rollout-*.jsonl` under `~/.codex/sessions/**` | `adapters.codex_rollout_jsonl` |

Incremental routing (pre-S3) accepts only `jsonl_kiro_session`. S3 adds Codex
formats under the same default-off flag and `CONVMEM_INCREMENTAL_ROOT` gate.

## Incremental eligibility (`incremental_jsonl.decide_eligibility`)

| Condition | Outcome |
|---|---|
| `enabled=false` | `disabled` |
| format not in eligible registry | `ineligible_format` |
| `force_reindex` or `supersede_on_reindex` | `incremental_force_unsupported` |
| no checkpoint and (`processed` entry or Chroma rows) | `bootstrap_required` |
| no checkpoint, clean source | `eligible_new_source` |
| invalid checkpoint | `invalid_state` |
| valid checkpoint | `eligible_checkpointed_source` |

Live activation without `CONVMEM_INCREMENTAL_ROOT` returns `skipped` (zero writes).

## Source authority

1. **Complete prefix** ends at the byte after the last `\n`, or `0` when no newline.
2. **Partial trailing record** is excluded until a terminating newline appears.
3. **Continuity** compares `(device, inode)`, `transform_fingerprint`, and SHA-256
   of the prior complete prefix; size/tail-window alone never authorizes reuse.
4. **Revalidation** re-reads live bytes before Chroma writes and checkpoint publish.

## Chunking and transform fingerprint

- Chunks: `ingest.chunk_messages(size, overlap)` with absolute `start_offset` /
  `end_offset` on canonical messages.
- Fingerprint (`compute_transform_fingerprint`): adapter format + contract version,
  chunk/overlap, rendering limits, prompt versions, models, embed dimension,
  provenance/ID/dedupe contracts, `implementation_revision`.
- Prepared cache key: `sha256(source_id:input_digest:transform_fingerprint:chunk_start)`.

## Physical keep set (S2 contract)

Publication must derive the prune keep set from **physical** Chroma IDs after:

1. `evaluate_ingest_batch` exact suppressions (`matched_id` retained, `suppressed_id` not written).
2. Provenance collision projection (`convmem-p3-projection-v1:…` IDs when written).

Logical prepared unit IDs alone are insufficient. Checkpoint `summary_ids` /
`unit_ids` store the complete post-apply manifest.

## Prepared replay

- Prepared artifacts are fsynced before first Chroma write.
- Replay validates digest, fingerprint, input, embedding shape.
- Crash after first write replays cached outputs with **zero** new provider calls.

## Kiro adapter oracle (`adapters/kiro_session_jsonl`)

- `parse_complete_prefix`: same message order as `parse()` on the complete prefix.
- Accepted payload types: `user`, `assistant` with non-empty content.
- Skipped payload types: `turn_start`, `turn_end`, `tool_*`, metadata, etc.
- Malformed complete JSON lines: silently skipped (legacy); not counted as messages.
- `session.json` digest tracked when present (non-symlink).

## Codex history oracle (`adapters/codex_history_jsonl`)

Legacy `parse()`:

- UTF-8 text mode; invalid file encoding fails at read (not per-line recovery).
- Blank lines skipped.
- Malformed JSON, non-dict, missing/blank `text`: skipped silently.
- Emitted: `role=user`, `source_type=prompt_only`, optional `session_id` / `timestamp`.

Prefix adapter (S1) adds auditable `line_outcomes` for every **complete** line:

| Outcome | Meaning |
|---|---|
| `skipped_blank` | whitespace-only line |
| `skipped_invalid_utf8` | line bytes are not valid UTF-8 |
| `skipped_malformed_json` | JSON decode failure |
| `skipped_non_object` | decoded value is not a dict |
| `skipped_no_message` | dict lacks usable `text` |
| `emitted` | canonical user message produced |

## Codex rollout oracle (`adapters/codex_rollout_jsonl`)

Legacy `parse()`:

- `response_item` / `event_msg` with dict `payload` only.
- Message payload types: `message` (user/assistant), `user_message`, `agent_message`.
- Text blocks: `input_text`, `output_text`, `text`.
- Non-message records and metadata-only lines: skipped silently.

Prefix adapter (S1) adds auditable `line_outcomes` with the same categories plus
`skipped_no_message` for ignored event kinds.

## Hermetic verification fixtures

| Fixture module | Role |
|---|---|
| `tests/test_incremental_index_contract_inventory.py` | S0 parity oracles |
| `tests/test_codex_jsonl_prefix_adapters.py` | S1 prefix matrix |
| `tests/test_incremental_jsonl_physical_keep_set.py` | S2 physical-ID pruning |
| `tests/test_codex_incremental_jsonl_route.py` | S3 isolated Codex route |

## Explicit non-goals (this Execute)

- S4 existing-source adoption, S5 tail-only I/O, live Codex paths, watcher/config changes.
- Claiming #268 historical OOM is fixed.
