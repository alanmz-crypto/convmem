# Sol Successor Packet — Issue #286 Kiro Bootstrap

**Arc:** Kiro bootstrap  
**Issue:** #286 — changed-file indexing at chunk/append level  
**Prepared:** 2026-10-11 by Sol  
**Review lanes:** Kiro design review; GitHub Copilot safety/isolation audit  
**State:** corrected packet refreshed with a fresh backup pair; `NO-GO` absent
new same-revision review and a separate Ryan execution grant

## Decision consequence

PR #381 merged failed-operation supersession on `main` as
`e798bba284c96642fc31229e6375eadc26986493`. The implementation prerequisite
is therefore present. A live successor bootstrap still requires a new Ryan
grant naming the exact source, source measurements, backup disposition,
dimension, runtime, config, budget, and one recovery allowance.

This packet does not authorize an operation id, executable grant, provider
request, corpus mutation, config promotion, or watcher restart.

## Exact source measurement

Read-only measurement revalidated by the governed r3 backup preflight on
2026-10-11:

| Field | Exact value |
|---|---|
| Canonical source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Format | `jsonl_kiro_session` |
| Owner / mode | UID `1000`; mode `0600` |
| Device / inode | `66306` / `23609783` |
| Size / complete boundary | `225091` / `225091` bytes |
| Full-prefix SHA-256 | `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741` |
| Session metadata SHA-256 | `68ef7b750290655ef00438125e5b3d38bb3ea65d342372acce6e0369c263c662` |
| Accepted messages | `68` |
| Chunking | size `60`, overlap `10`; exactly `2` chunks |
| Source state id | `13c4c30c5c644a1771f0372e1b16fde35ab8cd283c26f594b96f800aad3976d2` |

These values remain identical to the failed operation. Execution preflight must
repeat every value after acquiring the source lock. Any mismatch voids the
later grant before provider transport or corpus mutation.

## Runtime, configuration, and dimension

- Reviewed merged implementation: `e798bba284c96642fc31229e6375eadc26986493`.
- Execution must use a clean checkout detached at that exact commit. Later
  `main` movement must not silently change the runtime binding.
- Config SHA-256:
  `be9be9e963eade2a095d61fbda48a79db7e9fad4305d4af6e9c0ee68d7ce9413`.
- Transform fingerprint after applying the one-shot command's in-memory route
  overlay (`enabled=true`, exact `live_sources`, `embed_dimension=768`,
  `allow_full_rebuild=false`):
  `d2ecd101c3537c8d17620e876206e83c416e05f17106c207e3e1ebe1624473f5`.
- Required existing embedding dimension: `768` in both
  `conversation_summaries` and `knowledge_units`.
- Generation binding: DeepSeek `deepseek-v4-flash` for summarize/distill,
  `https://api.deepseek.com`, redirects disabled, fallback disabled.
- Embedding binding: local Ollama `nomic-embed-text:latest`, dimension `768`,
  fallback disabled.

The clean runtime SHA, config bytes, transform fingerprint, provider bindings,
and both collection dimensions must be rechecked before transport.

## Refused first successor grant

Ryan authorized the prior reviewed packet, and Sol ran its exact preflight on
2026-10-10. The executable grant bound transform fingerprint
`7fda8eefd284c17a40579d3bda5ebd806ed30408f5ddae147bc32bccf46f8528`,
operation id
`3e4a85fbf7bd086b7d0d58b38ef1ab4f0d49d1b0e16f0705260f870ba3903c6d`,
and grant fingerprint
`b676709822efc120f378047ff217e8e944eb490303df6eca40e0ee3c09f530e5`.

The production command correctly applied its in-memory route overlay before
computing the effective binding and observed transform fingerprint
`d2ecd101c3537c8d17620e876206e83c416e05f17106c207e3e1ebe1624473f5`.
It refused the stale binding before supersession activation, operation-journal
creation, provider transport, or corpus mutation. The predecessor transaction
remains `transform_failed`; the successor operation directory and lineage are
absent; the carried paid count remains `2`; and the additional paid count is
`0`. That exact grant is void and must not be retried or edited.

## Retired replacement proposal

The later non-executed replacement proposal had operation id
`c5fec18c2403c4038740050d414cdf2d309f399d56a0cb46eb5431139b779c81`,
grant fingerprint
`c860712f6e58066144ff5ad9e0ce1a80d33ceb8e54d69d9b985204b7b6e98fb1`,
and authority fingerprint
`c0ac7d2cbc190326ae13beac8f43e1b26a98f1f8ad3c82eef4213a63752f93d0`.
Its execution attempts stopped before supersession activation, provider
transport, or corpus mutation. A later inventory change made that proposal
stale. It remains unconsumed but is permanently retired and must never be
reused, edited, or regenerated under the same identifiers.

## Backup disposition

On 2026-10-11 Sol executed the Kiro/Copilot-PASSed one-shot r3 backup runner.
It paused all eight governed timers, required every governed service to be
`inactive` or `failed` with `MainPID=0`, acquired the exclusive ConvMem writer
gate, and created local Restic snapshot
`89aaf9ef40a1b07e95af09d0227382ce7333a4c897fd3f0da8c6382d62d63ecc`.
It covers the mutable ConvMem corpus at `/home/lauer/.local/share/convmem`.

The same runner mounted the designated `rxBUlauer-128Gfs` drive (UUID
`f1bd69b4-e567-4ef3-89ec-13faff0602e9`) at
`/run/media/lauer/rxBUlauer-128Gfs` and passed that exact returned local id once
to the governed offsite-copy API. Offsite snapshot
`995102108a10ad222f615e7cf130feb7c56ebceac19c5eeb0ebdd0562b31a4a8`
resolved with Restic `original` equal to the full local id. Both snapshots have
tree `de8888c7236881c81cfc16de67c51fe9f0168ce365f60079f0b6cb1280e524c6`,
timestamp `2026-10-11T15:39:52.327730-05:00`, path
`/home/lauer/.local/share/convmem`, and tags `convmem-data-v2`,
`convmem-2026-10-11`, and `kiro-successor-preflight`.

The predecessor mutation inventory remained
`0ecb33ea8a62be7fd4d0faeee30929cefbca04d001b59be8459b2a1616a9b27b`
before the local snapshot, after it, and after the offsite copy. Complete-data
evidence SHA-256 is
`347582c223bea6f16343a32145314a8eda3b495d6f50fde7f0d2936c926909c9`.
The mode-0600 PASS result is
`/tmp/convmem-kiro-replacement-backup-result-20261011-r3.json`, SHA-256
`61c71ccc23480bc1b37bd22d1cb29987db065566a9e628496ec940378259c5a9`.
All timers returned to their exact prior states, the watcher remained inactive
and disabled, and the drive was unmounted. The r3 backup grant is consumed and
must never be reused.

The backup disposition is therefore: fresh matching local and offsite coverage
for the mutable ConvMem corpus, with no backup of the read-only Kiro source.
Ryan has accepted that the source is outside the backup sets. The bootstrap
must never write it. Execution preflight must remount the designated drive,
revalidate both exact snapshots, and fail before provider transport or corpus
mutation if either is unavailable or does not match.

## Predecessor evidence and supersession

The durable predecessor remains unchanged:

- phase `transform_failed`;
- transaction id `18d83bf3246c4c19b823e2cd950fe8c0`;
- transaction SHA-256
  `5931be7c5faff4294b70e3c5f30da191e7906225f9b42369a714b26e922920ac`;
- operation id
  `732440c417fece9a36ac3d5381adf7b155be6a265576949f85823e3edce7e7c8`;
- grant fingerprint
  `dc56d5af9e5ed353da08527942f18fbc3856d482852554626ebfbbc22c3327ae`;
- predecessor runtime `3df86385b5dc19512c0140849ea147d8ed34dcc4`;
- predecessor transform fingerprint
  `dfc1b62523a988f39a917cec5ddb81ec04c08a8db80b13131dff2d4588f2050d`;
- two DeepSeek generation requests and six local Ollama embedding requests;
- `8574` observed DeepSeek tokens; and
- no checkpoint, rollback, prepared output, or projection apply.

An earlier operation with fingerprint
`f9c55ec0544105bd628ccabe78d54d487104fe988ca221ede2a1db137a54c4a3`
ended at preflight with zero provider attempts and no transaction. It is
retained evidence and contributes zero paid attempts.

The successor must use the merged `supersede_failed_bootstrap` authority,
preserve all predecessor evidence, publish deterministic lineage, and refuse
ordinary-grant admission while supersession evidence exists.

## One-time paid-processing budget

- Maximum source chunks: `2`.
- Predecessor paid DeepSeek attempts carried forward: `2`.
- Maximum additional DeepSeek HTTP attempts: `6` across the initial successor
  invocation and one same-grant recovery.
- Maximum lifetime DeepSeek HTTP attempts: `8`.
- Maximum recovery invocations: `1`.
- Local Ollama embedding attempts remain durably observed but do not consume
  the paid DeepSeek cap.
- No token or dollar ceiling is inferred from the HTTP-attempt ceiling.

Every attempt must be durably recorded before transport. Budget exhaustion or
a second recovery request stops the operation without changing the grant.

## Measurement and isolation plan

### Before execution

1. Prepare a fresh proposal and supersession authority bound to this packet
   revision, the exact backup pair, and current mutation inventory. Materialize
   an executable grant only after Ryan separately authorizes the reviewed
   proposal and only after source, predecessor evidence, backup disposition,
   runtime, config, transform, provider, dimension, watcher, and writer-census
   checks all pass.
2. Require watcher state `inactive`, `disabled`, `MainPID=0`.
3. Capture byte/digest inventories for the source-scoped rows in both Chroma
   collections, `processed.json`, export rows, dedupe sidecars, checkpoint,
   prepared cache, and the complete incremental source-state directory.
4. Capture exact unrelated-state inventories; counts alone are insufficient.
5. Reconcile the predecessor ledgers to exactly two paid DeepSeek attempts,
   six observed Ollama attempts, and 8574 observed DeepSeek tokens.

### During execution

1. Record DeepSeek and Ollama permits before transport and response usage after
   transport.
2. Enforce six additional and eight lifetime DeepSeek attempts across the
   initial invocation plus at most one recovery.
3. Stop on any source, evidence, binding, dimension, writer, redirect, budget,
   lineage, or isolation mismatch.
4. Do not alter the source, switch providers, change the grant, start the
   watcher, or attempt another source.

### After execution

1. Reconcile predecessor and successor attempt/usage ledgers and report actual
   DeepSeek requests and tokens, logical summarize/distill calls, local Ollama
   requests, terminal state, and unused recovery allowance.
2. Require a complete checkpoint bound to the exact source, boundary,
   dimension, transform fingerprint, active generation, and lineage.
3. Require agreement among the checkpoint keep sets, both Chroma collections,
   processed state, and export rows, covering all 68 accepted messages across
   both chunks.
4. Require exact equality for every unrelated-state inventory.
5. Keep the watcher disabled. Success does not authorize config promotion,
   watcher restart, append testing, or another transcript source.

## Review contract

Kiro and GitHub Copilot must review this same file revision and digest.

- **Kiro:** confirm the source/bootstrap assumptions, detached merged runtime,
  corrected post-overlay transform fingerprint, supersession model, verified
  backup disposition, budget, and measurement plan.
- **Copilot:** audit evidence preservation, filesystem containment, authority
  binding, the zero-call refusal claim, budget carry-forward,
  fail-before-mutation ordering, and isolation.

Each reviewer returns written `PASS` or `FAIL`, with blockers separate from
advisories. A deferral or missing review is not a conflict.

## Recommendation

`NO-GO` for a live successor bootstrap. Kiro and Copilot must first PASS this
fresh-backup exact revision. Sol may then seal the already-authorized
non-executed successor proposal against this reviewed packet. Ryan may later
issue a new exact execution grant naming the corrected post-overlay transform
fingerprint and verified backup disposition, with all execution-day
measurements repeated. Runtime/config promotion and watcher restart remain
later, separate grants.

## TL;DR

The reviewed supersession implementation is merged and the exact Kiro source
is unchanged. The fresh backup-only preflight created local snapshot
`89aaf9ef…3ecc` and exact offsite copy `99510210…4a8`, sharing tree
`de8888c7…24c6`, while inventory `0ecb33ea…9b27b` stayed exact. The two carried
paid attempts, six-additional/eight-lifetime cap, and accepted read-only source
disposition remain explicit. Execution is `NO-GO` until same-revision review,
a newly sealed proposal, and a separate exact Ryan grant.
