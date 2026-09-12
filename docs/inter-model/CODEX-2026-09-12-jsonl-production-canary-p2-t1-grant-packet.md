# Review Packet: Arc Codex P2-T1 Exact-Resource Grant

**Arc:** Codex

**Date:** 2026-09-12

**Author:** Codex planning/handoff lane

**For:** Kiro exact-artifact review -> Ryan disposition

**Authorization:** Ryan, 2026-09-12 — remeasure the named closed source
read-only, prepare the exact P2-T1 grant packet, push documentation, and stop
for fresh Kiro review

> **This packet is not operational authority.** It freezes one complete grant
> candidate and its digest for review. Gate 0, nonce consumption, P2 execution,
> production mutation, configuration changes, watcher operations, indexing,
> provider/network calls, activation, and PR creation remain prohibited.

---

## Resume state

| Field | Value |
|---|---|
| State | `READY_FOR_KIRO_REVIEW` |
| Reviewed runtime base | `7360a04e1e8154eca76eddf72c492251ae830c0f` on merged `main` |
| Candidate grant SHA-256 | `6022294bb8c00375346fad55f27c8251bd60e58a850a6686484b7fefdd9e4343` |
| Grant authority | **None** — candidate digest is review-only |
| Next decision | Kiro PASS/FAIL on this exact packet and merged runtime revision |
| After PASS | Ryan alone decides whether to authorize this exact digest and non-mutating Gate 0 |
| PR | Not opened; separately Ryan-gated |

## Product consequence

The dedicated Kiro transcript is closed, quiescent, and still inside the
reviewed two-chunk baseline window. This packet binds every grant field needed
to make a later decision concrete without yet touching production state. A
change to any source byte, metadata byte, path, model identity, cap, fault,
rollback field, expiry, nonce, or code revision creates a different digest and
requires a new review and Ryan decision.

## Read-only source freeze

Codex used `parse_complete_prefix()` for three stable reads spanning more than
two seconds. The source and metadata were regular, canonical, non-symlink
files and did not change during or between reads. No source/session file was
written or locked.

The previous 224,318-byte prefix remains byte-identical. The later 773-byte
pure append contains a completed `fetch_cloud_config` tool call and successful
tool result; both record types are adapter-excluded. The accepted-message count
therefore remains 68.

| Field | Frozen value |
|---|---|
| Dedicated source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Accepted messages | **68**; required baseline window is 61–109 |
| Source device / inode | `66306` / `23609783` |
| Source size / complete boundary | `225091` / `225091` bytes |
| Complete-prefix SHA-256 | `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741` |
| Metadata | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/session.json` |
| Metadata device / inode / size | `66306` / `23605861` / `1272` bytes |
| Metadata SHA-256 | `68ef7b750290655f00438125e5b3d38bb3ea65d342372acce6e0369c263c662` |
| Quiescence | metadata status `idle`; no open file handles; more than 24 hours unchanged at freeze time |
| Publish cursor | `225091:216`; byte position equals the frozen source EOF |

Any later drift invalidates the candidate digest before Gate 0. The session
must remain unused unless the reviewed P2 append stage explicitly pauses for a
Ryan-authored benign interaction under the approved envelope.

## Exact code and resource binding

The grant binds runtime code at merged `main` commit
`7360a04e1e8154eca76eddf72c492251ae830c0f`. The packet branch contains only
documentation and is not an executable substitute for that revision.

The eleven mutable resource roles are:

| Role | Exact path |
|---|---|
| `chroma` | `/home/lauer/.local/share/convmem/chroma` |
| `incremental_state` | `/home/lauer/.local/share/convmem/incremental-jsonl` |
| `export` | `/home/lauer/.local/share/convmem/knowledge_units.jsonl` |
| `dedupe` | `/home/lauer/.local/share/convmem` |
| `processed` | `/home/lauer/.local/share/convmem/processed.json` |
| `writer_lock` | `/home/lauer/.local/share/convmem/locks/chroma_writer_gate.lock` |
| `source_lock` | `/home/lauer/.local/share/convmem/locks/source/fc38a9e06cba5d32d167d4417ebb963e27f39b15d6af6f83c48c6dc012a70866.lock` |
| `export_lock` | `/home/lauer/.local/share/convmem/knowledge_units.jsonl.lock` |
| `processed_lock` | `/home/lauer/.local/share/convmem/processed.json.lock` |
| `attestations` | `/home/lauer/.local/share/convmem/writer_attestations` |
| `census` | `/home/lauer/.local/share/convmem/writer_census` |

No resource was opened or inspected during this preparation. Zero adoption,
lock freedom, attestation/census state, path hardening, and persistent
false/false configuration remain Gate 0 facts, not claims made by this packet.

## Exact local-model binding

Both model manifests were read directly from the configured local model store;
no Ollama request, provider call, pull, or network request occurred.

| Use | Exact model | Full manifest SHA-256 | Grant field |
|---|---|---|---|
| Summarize / distill | `llama3.1:8b` | `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e` | `46e0c10c039e` |
| Embedding | configured alias `nomic-embed-text`; canonical tag `nomic-embed-text:latest` | `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f` | `0a109f422b47` |

The grant uses the 12-hex identities enforced by `MODEL_DIGESTS` at the bound
runtime revision. Gate 0 must independently re-prove installation and identity
without pulling a model.

## Append, calls, faults, and generations

- Baseline: 68 accepted messages, exactly two chunk starts `[0, 50]` under
  chunk size 60 and overlap 10.
- Maximum final complete boundary: `356163` bytes, the frozen boundary plus
  exactly 128 KiB.
- Maximum accepted records: `110`; reaching 111 creates a third chunk and must
  stop P2.
- Maximum post-baseline append epochs: `6`; immutable prefix required.
- Expected generations: one initial generation, one control append generation,
  and five separately paused fault-append generations.
- Initial ceilings: summarize/distill/summary-embed/unit-embed `2/2/2/16`.
- Each append ceiling: `1/1/1/8`.
- Every unchanged replay/reconcile ceiling: `0/0/0/0`.
- Whole-run ceilings: `8/8/8/64`.
- Fault selectors, in order: `summary_upsert`, `unit_upsert`, `units_prune`,
  `checkpoint_publish`, `dedupe_reconcile`.

## Rollback and backup binding

Rollback authority is **source-path-only**. It may restore or delete only
candidate IDs and followers belonging to the exact granted source. It does not
authorize broad Chroma replacement, restic restore, unrelated-source mutation,
config repair, lock deletion, or retry with fresh transforms.

| Field | Bound value |
|---|---|
| Capsule path | `/home/lauer/.local/share/convmem/jsonl-production-canary/p2-f59b9863135ae90ee3a08c7b186bfc8f/rollback-capsule.json` |
| Expected digest | 64 zeroes — the merged runner's reviewed expected-empty sentinel before fresh capsule capture |
| Required primary backup | restic snapshot `64040b6fb2c40d5d00352c7f5f472e6461b38ad89b40155f9e142a481bc8c862`, tag `convmem-data-v2` |
| Offsite evidence | copy `16fa9a504bfe60e9845918b9426bb521dbadacce7ee218da1d4e726a15904ab2` |
| Restore authority | **None**; identifiers are evidence only |

Kiro must specifically confirm that the zero-digest sentinel and
`expected_pre_state` backup binding are sufficient at revision `7360a04`.
Gate 0 must capture and verify the fresh expected-empty source-scoped capsule
before any P2 write; this packet does not create that capsule.

## Exact temporary overlay

Proposed machine-local grant path (not created by this packet):
`/home/lauer/.local/share/convmem/jsonl-production-canary/p2-f59b9863135ae90ee3a08c7b186bfc8f/p2-grant.json`.

The exact overlay path is
`/home/lauer/.local/share/convmem/jsonl-production-canary/p2-f59b9863135ae90ee3a08c7b186bfc8f/overlay.toml`.
Its exact bytes and SHA-256 are:

```toml
[index]
chroma_dir = "/home/lauer/.local/share/convmem/chroma"
processed_log = "/home/lauer/.local/share/convmem/processed.json"
units_export = "/home/lauer/.local/share/convmem/knowledge_units.jsonl"
chunk_size = 60
chunk_overlap = 10

[index.incremental_jsonl]
enabled = true
state_dir = "/home/lauer/.local/share/convmem/incremental-jsonl"
allow_full_rebuild = false

[models]
embed_model = "nomic-embed-text"
summarize_model = "llama3.1:8b"
distill_model = "llama3.1:8b"
ollama_host = "127.0.0.1:11434"

[distill]
min_confidence = 0.6
```

Overlay SHA-256:
`de1185c568ffb7fe7bd259524a968b5d01827e7210e0e6847a54b98183aba2b7`.

The persistent configuration is not changed. Creating this overlay is not
authorized by the packet-preparation grant.

## Complete candidate grant JSON

```json
{
  "schema_version": 1,
  "code_revision": "7360a04e1e8154eca76eddf72c492251ae830c0f",
  "expires_at": "2026-09-19T06:23:44Z",
  "nonce": "f59b9863135ae90ee3a08c7b186bfc8f",
  "run_once": true,
  "source": {
    "path": "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl",
    "metadata_path": "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/session.json",
    "device": 66306,
    "inode": 23609783,
    "size": 225091,
    "complete_boundary": 225091,
    "prefix_sha256": "dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741",
    "metadata_sha256": "68ef7b750290655f00438125e5b3d38bb3ea65d342372acce6e0369c263c662"
  },
  "append_envelope": {
    "max_byte_boundary": 356163,
    "max_accepted_records": 110,
    "max_append_epochs": 6,
    "immutable_prefix": true
  },
  "resources": [
    {
      "path": "/home/lauer/.local/share/convmem/chroma",
      "role": "chroma"
    },
    {
      "path": "/home/lauer/.local/share/convmem/incremental-jsonl",
      "role": "incremental_state"
    },
    {
      "path": "/home/lauer/.local/share/convmem/knowledge_units.jsonl",
      "role": "export"
    },
    {
      "path": "/home/lauer/.local/share/convmem",
      "role": "dedupe"
    },
    {
      "path": "/home/lauer/.local/share/convmem/processed.json",
      "role": "processed"
    },
    {
      "path": "/home/lauer/.local/share/convmem/locks/chroma_writer_gate.lock",
      "role": "writer_lock"
    },
    {
      "path": "/home/lauer/.local/share/convmem/locks/source/fc38a9e06cba5d32d167d4417ebb963e27f39b15d6af6f83c48c6dc012a70866.lock",
      "role": "source_lock"
    },
    {
      "path": "/home/lauer/.local/share/convmem/knowledge_units.jsonl.lock",
      "role": "export_lock"
    },
    {
      "path": "/home/lauer/.local/share/convmem/processed.json.lock",
      "role": "processed_lock"
    },
    {
      "path": "/home/lauer/.local/share/convmem/writer_attestations",
      "role": "attestations"
    },
    {
      "path": "/home/lauer/.local/share/convmem/writer_census",
      "role": "census"
    }
  ],
  "config_overlay": {
    "path": "/home/lauer/.local/share/convmem/jsonl-production-canary/p2-f59b9863135ae90ee3a08c7b186bfc8f/overlay.toml",
    "digest": "de1185c568ffb7fe7bd259524a968b5d01827e7210e0e6847a54b98183aba2b7"
  },
  "provider": {
    "loopback_host": "127.0.0.1:11434",
    "summarize_model": "llama3.1:8b",
    "summarize_digest": "46e0c10c039e",
    "embed_model": "nomic-embed-text",
    "embed_canonical_tag": "nomic-embed-text:latest",
    "embed_digest": "0a109f422b47",
    "distill_model": "llama3.1:8b",
    "distill_digest": "46e0c10c039e"
  },
  "call_ceilings": {
    "initial": {
      "summarize": 2,
      "distill": 2,
      "summary_embed": 2,
      "unit_embed": 16
    },
    "append": {
      "summarize": 1,
      "distill": 1,
      "summary_embed": 1,
      "unit_embed": 8
    },
    "replay": {
      "summarize": 0,
      "distill": 0,
      "summary_embed": 0,
      "unit_embed": 0
    },
    "whole_run": {
      "summarize": 8,
      "distill": 8,
      "summary_embed": 8,
      "unit_embed": 64
    }
  },
  "faults": [
    "summary_upsert",
    "unit_upsert",
    "units_prune",
    "checkpoint_publish",
    "dedupe_reconcile"
  ],
  "rollback": {
    "capsule_path": "/home/lauer/.local/share/convmem/jsonl-production-canary/p2-f59b9863135ae90ee3a08c7b186bfc8f/rollback-capsule.json",
    "expected_digest": "0000000000000000000000000000000000000000000000000000000000000000"
  },
  "evidence_dir": "/home/lauer/.local/share/convmem/jsonl-production-canary/p2-f59b9863135ae90ee3a08c7b186bfc8f/evidence",
  "expected_pre_state": {
    "checkpoint": null,
    "generation": null,
    "processed_entry": null,
    "conversation_summaries_rows": 0,
    "knowledge_units_rows": 0,
    "incremental_state_present": false,
    "rollback_scope": "source_path_only",
    "restic_backup_id": "64040b6fb2c40d5d00352c7f5f472e6461b38ad89b40155f9e142a481bc8c862",
    "restic_backup_tag": "convmem-data-v2",
    "restic_offsite_copy_id": "16fa9a504bfe60e9845918b9426bb521dbadacce7ee218da1d4e726a15904ab2"
  },
  "capability_mode": "p2-exact-resource-v1"
}
```

The digest is computed over UTF-8 canonical JSON using
`json.dumps(payload, sort_keys=True, separators=(",", ":"))`, exactly as
`CanaryGrant.digest_payload()` does at revision `7360a04`.

**Candidate grant SHA-256:**
`6022294bb8c00375346fad55f27c8251bd60e58a850a6686484b7fefdd9e4343`

## Kiro review request

Kiro should issue PASS or FAIL against both this exact packet and runtime
revision `7360a04e1e8154eca76eddf72c492251ae830c0f`. In particular, verify:

1. the JSON decodes under the closed schema and recomputes to the stated
   digest;
2. source identity, eleven roles, lock derivation, overlay bytes, model
   identities, append envelope, call caps, nonce, expiry, and fault ordering
   match the reviewed architecture and execution plan;
3. `expected_pre_state` adequately binds the required backup and zero-adoption
   expectations even though live proof is deferred to Gate 0;
4. the 64-zero rollback digest sentinel cannot allow mutation before a fresh,
   readable expected-empty capsule is captured and verified; and
5. the bound runtime's default P2 Gate 0 probes actually validate the named
   backup/model/rollback facts rather than accepting hermetic placeholders.

A PASS authorizes nothing by itself. After PASS, Ryan decides whether to
authorize exactly
`6022294bb8c00375346fad55f27c8251bd60e58a850a6686484b7fefdd9e4343`
and the non-mutating twelve-part Gate 0. P2-T3–T6 still require later,
separately explicit run authority.

## Scope firewall

This preparation did not and does not authorize:

- creating the machine-local grant, overlay, evidence directory, nonce
  receipt, or rollback capsule;
- running Gate 0, `--preflight-only`, P2-T3–T6, or any canary worker;
- opening Chroma or production follower data;
- reading or changing persistent configuration;
- calling a model/provider, contacting a network endpoint, or pulling models;
- indexing any file, starting/stopping the watcher, or operating services;
- editing the source or metadata;
- opening a PR, merging, retrying, or activating incremental ingestion.

## Related artifacts

| What | Path / identity |
|---|---|
| Current Arc Codex snapshot | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Reviewed canary architecture | `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` |
| Reviewed P2 execution contract | `docs/plans/EXECUTION-codex-jsonl-production-canary.md` §4 |
| Corrective implementation evidence | `docs/plans/VERIFY-codex-jsonl-production-canary.md` |
| P2 capability-gap predecessor | `docs/inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-grant-packet.md` |
| Merged corrective runtime | PR #299 merge `8beda7d`; status synchronized by PR #300 merge `7360a04` |

## TL;DR

- **Arc Codex:** the closed source is freshly frozen at 68 accepted messages;
  the current identity is stable and the old prefix remains intact.
- The complete review candidate binds runtime `7360a04`, all eleven resource
  roles, models, caps, faults, rollback/backup expectations, expiry, and nonce.
- Candidate digest:
  `6022294bb8c00375346fad55f27c8251bd60e58a850a6686484b7fefdd9e4343`.
- Stop for Kiro. No digest authority, Gate 0, P2, production access, PR, or
  activation exists.
