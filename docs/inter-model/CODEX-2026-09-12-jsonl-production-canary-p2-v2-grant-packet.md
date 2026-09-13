# Arc Codex — P2 v2 Source Freeze and Grant-Packet Review

**Date:** 2026-09-12

**Author:** Codex planning/grant-packet lane

**Reviewer:** Kiro

**Runtime:** `origin/main` at
`8983a6fc909344239e6e3051d85c50c5508c1a16`

**Packet state:** `SOURCE_ELIGIBLE / GRANT_BLOCKED`

**Executable grant digest:** **NOT ISSUED**

## Decision requested from Kiro

Review this bounded packet and answer four questions:

1. Does the fresh read-only measurement bind an eligible, stable, closed Kiro
   source to the merged `p2-exact-resource-v2` runtime?
2. Does the blocked-field inventory correctly cover the live bindings required
   by the v2 schema but excluded from Ryan's read authority?
3. Is withholding both a complete grant JSON and its SHA-256 the correct
   fail-closed result?
4. Did this preparation remain inside the source-and-metadata-only authority?

This review does not authorize the missing reads, packet completion, Gate 0,
P2, a PR, or activation.

## Current context

Ryan authorized this packet after the live-safe exact-resource JSONL canary
implementation in PR #301 was squash-merged. Cursor produced the implementation,
Kiro reviewed its final pre-merge head
`5dac4c01564de5842c91cc781f862894424b8510`, and Ryan merged it as
`8983a6fc909344239e6e3051d85c50c5508c1a16` after all six CI checks passed.
Kiro's post-merge audit returned PASS for packet preparation, not for any live
operation.

The merged runtime recognizes capability mode `p2-exact-resource-v2`. It
requires more than a source freeze: persistent-config, model-manifest, restic,
resource-identity, owner, overlay, rollback, evidence, and expected-pre-state
bindings are part of the material grant. Ryan authorized live reads of only the
source and its metadata. Consequently this document freezes what was actually
observed and records the rest as blocked. It intentionally does not assemble a
`CanaryGrant` payload or hash one.

## Exact authorized read scope

Only these two live files were opened:

- source:
  `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl`
- metadata:
  `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/session.json`

The inspection opened both simultaneously with
`O_RDONLY | O_CLOEXEC | O_NOFOLLOW`, retained the descriptors throughout each
observation, read with `pread`, and compared descriptor `fstat` identity with
path `lstat` before and after parsing. Every path component was checked for
symlinks, both canonical paths matched their requested paths, and both final
objects were regular files. The adapter's merged
`parse_complete_prefix()` parsed the exact source bytes read from the held
descriptor. The two complete observations were 2.1 seconds apart.

No source or metadata lock, chmod, write, rename, unlink, or creation occurred.

## Fresh measurement

### Source identity and complete prefix

| Field | Observation 1 | Observation 2 / after | Result |
|---|---:|---:|---|
| device | `66306` | `66306` | stable |
| inode | `23609783` | `23609783` | stable |
| size | `225091` | `225091` | stable |
| mode | `0644` | `0644` | stable |
| owner UID | `1000` | `1000` | stable |
| mtime ns | `1789106495654155817` | `1789106495654155817` | stable |
| ctime ns | `1789106495654155817` | `1789106495654155817` | stable |
| complete boundary | `225091` | `225091` | stable; at EOF |
| complete-prefix SHA-256 | `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741` | same | stable |
| accepted messages | `68` | `68` | eligible |
| accepted byte ranges | `68` | `68` | stable |
| production chunk starts | `[0, 50]` | `[0, 50]` | expected two chunks |

The full-file SHA-256 equals the complete-prefix SHA-256 because the complete
boundary is the observed EOF.

### Metadata identity

| Field | Observation 1 | Observation 2 / after | Result |
|---|---:|---:|---|
| device | `66306` | `66306` | stable |
| inode | `23605861` | `23605861` | stable |
| size | `1272` | `1272` | stable |
| mode | `0644` | `0644` | stable |
| owner UID | `1000` | `1000` | stable |
| mtime ns | `1789106495655134080` | `1789106495655134080` | stable |
| ctime ns | `1789106495655351532` | `1789106495655351532` | stable |
| SHA-256 | `68ef7b750290655ef00438125e5b3d38bb3ea65d342372acce6e0369c263c662` | same | stable |
| session status | `idle` | `idle` | closed-source signal |

### Eligibility verdict

**PASS.** The source has 68 accepted messages, within the approved 61–109
baseline window. Its complete prefix, file identity, and metadata identity were
stable across both no-follow observations. Both paths are canonical,
non-symlink regular files. Metadata reports `idle`. The source is still closed
and suitable for a fresh P2-T1 freeze.

This is source eligibility only. It is not a Gate 0 result and does not prove
the state of any mutable production resource.

## Frozen fields

The following facts are frozen in this packet because they were either measured
inside the exact read authority or are immutable properties of the merged
runtime and approved architecture:

```json
{
  "append_envelope": {
    "immutable_prefix": true,
    "max_accepted_records": 110,
    "max_append_epochs": 6,
    "max_byte_boundary": 356163
  },
  "call_ceilings": {
    "append": {
      "distill": 1,
      "summarize": 1,
      "summary_embed": 1,
      "unit_embed": 8
    },
    "initial": {
      "distill": 2,
      "summarize": 2,
      "summary_embed": 2,
      "unit_embed": 16
    },
    "replay": {
      "distill": 0,
      "summarize": 0,
      "summary_embed": 0,
      "unit_embed": 0
    },
    "whole_run": {
      "distill": 8,
      "summarize": 8,
      "summary_embed": 8,
      "unit_embed": 64
    }
  },
  "capability_mode": "p2-exact-resource-v2",
  "code_revision": "8983a6fc909344239e6e3051d85c50c5508c1a16",
  "faults": [
    "summary_upsert",
    "unit_upsert",
    "units_prune",
    "checkpoint_publish",
    "dedupe_reconcile"
  ],
  "run_once": true,
  "schema_version": 1,
  "source": {
    "complete_boundary": 225091,
    "device": 66306,
    "inode": 23609783,
    "metadata_path": "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/session.json",
    "metadata_sha256": "68ef7b750290655ef00438125e5b3d38bb3ea65d342372acce6e0369c263c662",
    "path": "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl",
    "prefix_sha256": "dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741",
    "size": 225091
  }
}
```

This JSON is an intentionally incomplete, **non-executable source-freeze
fragment**. It is not a grant, cannot pass `decode_grant()`, and must not be
used as input to `digest_payload()`.

Two of the required v2 identity rows were also directly observed and are
frozen for later assembly. This list remains partial and therefore cannot be
placed into an executable grant yet:

```json
[
  {
    "device": 66306,
    "file_type": "file",
    "inode": 23609783,
    "mode": 420,
    "path": "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl",
    "role": "source",
    "uid": 1000
  },
  {
    "device": 66306,
    "file_type": "file",
    "inode": 23605861,
    "mode": 420,
    "path": "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/session.json",
    "role": "metadata",
    "uid": 1000
  }
]
```

`mode: 420` is the v2 payload's decimal representation of permission mode
`0644`.

This packet also freezes these non-live policy choices from the merged runtime,
approved architecture, and previously reviewed append allowance for a future
complete packet:

- baseline eligibility: 61–109 accepted messages;
- append envelope: immutable prefix, at most 110 accepted messages, at most six
  append epochs (one control append plus five fault epochs), and a final byte
  boundary no greater than 356163 (the frozen 225091-byte boundary plus the
  reviewed 128-KiB allowance);
- production chunk size/overlap: 60/10;
- fault selectors, in order: `summary_upsert`, `unit_upsert`, `units_prune`,
  `checkpoint_publish`, `dedupe_reconcile`;
- call ceilings:
  - initial: summarize 2, distill 2, summary embed 2, unit embed 16;
  - append: summarize 1, distill 1, summary embed 1, unit embed 8;
  - whole canary: summarize 8, distill 8, summary embed 8, unit embed 64;
- immutable-prefix requirement: true;
- rollback pre-capture sentinel: 64 zeroes means only "not captured yet";
  it is not proof of a rollback capsule.

These constants constrain later packet completion. They do not substitute for
the required live bindings below.

## Blocked fields

No value in this section is inferred from the retired v1 packet. Each material
field remains absent until Ryan separately authorizes the exact read needed to
observe or derive it.

| Required v2 binding | Why it remains blocked |
|---|---|
| `expires_at`, `nonce` | A fresh one-shot identity and review window should be generated only when a complete candidate can be assembled; neither is issued here. |
| `resources` for all 11 roles | Current absolute paths for Chroma, incremental state, export, dedupe, processed state, four locks, attestations, and census were not authorized for inspection. |
| `resource_identities` | v2 requires role/path/UID/mode/device/inode/type identities for source, metadata, overlay, evidence, capsule, persistent config, and all 11 resource roles. Only source and metadata were observed. |
| `owner_uid` | UID 1000 was observed for source and metadata only; common ownership of every exact resource cannot be inferred. |
| `config_overlay.path`, `.digest`, overlay identity | Creating or inspecting a production overlay was explicitly prohibited. |
| `persistent_config.path`, `.digest`, identity and false/false proof | Live configuration access was explicitly prohibited. |
| `provider` exact model bindings | Model state was explicitly outside read authority. Short runtime compatibility constants are not installed-manifest proof. |
| `model_manifests` | Full installed model digests and exact manifest paths for summarize, embed, and distill were not observed. |
| `restic` | Snapshot ID, tag, data root, repository, and current-local-day proof require separately authorized backup inspection. |
| `rollback.capsule_path` and identity | No production capsule resource may be created or inspected under this authorization. |
| `evidence_dir` and identity | No production evidence resource may be created or inspected under this authorization. |
| `expected_pre_state` | Chroma rows, processed/state/export/dedupe absence, lock/writer/watcher state, and persistent configuration were all outside the authorized reads. |

The future complete grant must cover all 11 exact resource roles:
`chroma`, `incremental_state`, `export`, `dedupe`, `processed`, `writer_lock`,
`source_lock`, `export_lock`, `processed_lock`, `attestations`, and `census`.
Naming these schema roles does not freeze their paths or identities.

## Digest disposition

No complete grant JSON was produced, so no executable SHA-256 exists. The
runtime hashes the canonical full payload using sorted JSON keys and compact
separators; hashing an incomplete fragment would misrepresent it as executable
authority. This packet therefore records:

```text
grant_json: NOT_ISSUED
grant_sha256: NOT_ISSUED
reason: REQUIRED_V2_LIVE_BINDINGS_UNOBSERVED_AND_UNAUTHORIZED
```

The prior v1 candidate digest
`c002385ee2e72e319ddcce2ab5d024c29abbe0031b86cbb26468cb604ee8c621`
is retired, was not reused, and must never be authorized for this runtime.

## Exact next authority needed

After Kiro reviews this packet, Ryan may decide whether to authorize a second,
separately bounded **read-only binding pass**. Such an authorization would need
to name the permitted production resource paths, persistent configuration,
installed model manifests, and restic identification operation, plus whether
the intended overlay/evidence/capsule paths may be checked as absent. It must
also say whether packet preparation may create any non-production grant
artifact. Until then, all blocked fields remain blank.

Even that read authority would not authorize resource preparation, Gate 0,
nonce consumption, provider calls, P2, indexing, watcher operation,
configuration change, or activation.

## Negative confirmation

During this packet preparation Codex did **not**:

- read or mutate production Chroma, processed/state/export/dedupe/locks,
  persistent configuration, model storage, restic, systemd, or watcher state;
- make any provider, model, production-service, or other operational network
  call; the only network use is the separately authorized Git branch push;
- run `convmem index`, Gate 0, P2, a provider, or activation;
- create a production overlay, evidence directory, rollback capsule, nonce
  receipt, or executable grant;
- write, lock, chmod, rename, unlink, or otherwise mutate the source or
  metadata;
- reuse the retired digest; or
- open a PR.

The only live reads were the two exact authorized files. Repository reads and
documentation writes occurred in the isolated plan worktree created from the
already-present local `origin/main` identity; no network lookup was used to
remeasure or enrich live-resource fields.

## Jargon TL;DR

| Term | Meaning |
|---|---|
| P2 | The separately authorized one-source live canary; not an activation. |
| P2-T1 | The source-freeze and exact-resource grant-packet preparation step. |
| Gate 0 | The non-mutating twelve-check preflight that still requires separate exact-digest authorization. |
| Exact-resource v2 | The merged grant mode that binds paths, identities, models, configuration, backup, and stage receipts rather than accepting hermetic stand-ins. |
| Complete prefix | The parseable JSONL bytes ending at a record boundary; here it equals the 225091-byte file. |
| Source freeze | A read-only identity and content measurement; not permission to index the source. |
| Executable digest | SHA-256 of one complete canonical grant payload; none exists for this packet. |

## TL;DR

- Arc Codex source remeasurement PASSed: the closed, canonical source remains
  stable at 68 accepted messages, boundary/size 225091, with source prefix
  digest `dfea479e…a732741` and metadata digest `68ef7b75…c263c662`.
- The merged v2 runtime at `8983a6fc…` requires live resource, configuration,
  model, restic, ownership, pre-state, and artifact bindings that Ryan did not
  authorize Codex to inspect.
- No complete grant JSON or SHA-256 was legitimately issuable. Kiro should
  review this fail-closed packet; Ryan then decides whether to authorize the
  exact additional read-only bindings.
