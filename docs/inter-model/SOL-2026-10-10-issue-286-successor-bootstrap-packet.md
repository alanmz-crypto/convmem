# Sol Successor Packet — Issue #286 Kiro Bootstrap

**Arc:** Kiro bootstrap  
**Issue:** #286 — changed-file indexing at chunk/append level  
**Prepared:** 2026-10-10 by Sol  
**Review lanes:** Kiro design review; GitHub Copilot safety/isolation audit  
**State:** review packet only; `NO-GO` for execution

## Decision consequence

PR #381 merged failed-operation supersession on `main` as
`e798bba284c96642fc31229e6375eadc26986493`. The implementation prerequisite
is therefore present. A live successor bootstrap still requires a new Ryan
grant naming the exact source, source measurements, backup disposition,
dimension, runtime, config, budget, and one recovery allowance.

This packet does not authorize an operation id, executable grant, provider
request, corpus mutation, config promotion, or watcher restart.

## Exact source measurement

Read-only measurement on 2026-10-10:

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
- Transform fingerprint under the merged implementation and named config:
  `7fda8eefd284c17a40579d3bda5ebd806ed30408f5ddae147bc32bccf46f8528`.
- Required existing embedding dimension: `768` in both
  `conversation_summaries` and `knowledge_units`.
- Generation binding: DeepSeek `deepseek-v4-flash` for summarize/distill,
  `https://api.deepseek.com`, redirects disabled, fallback disabled.
- Embedding binding: local Ollama `nomic-embed-text:latest`, dimension `768`,
  fallback disabled.

The clean runtime SHA, config bytes, transform fingerprint, provider bindings,
and both collection dimensions must be rechecked before transport.

## Backup disposition

Local Restic snapshot
`ac1087c862cae7e43b72ca4978379d4c07a0550b9cf2964557dfed9601da3954`
still passes the complete-data-v2 gate and covers the mutable ConvMem corpus at
`/home/lauer/.local/share/convmem`.

The previously matching offsite snapshot was
`653a8198a8b5b540cb029801efd72ced0b9156daccbceb5c6f93ab732b4f7ac4`.
On 2026-10-10 the external repository could not be opened because its mounted
path was absent, so current offsite coverage is **not verified**.

The read-only Kiro source is outside both backup sets. The bootstrap must never
write it. Ryan's later live grant must choose one of these exact dispositions:

1. mount the offsite repository and verify the matching snapshot before grant;
   or
2. explicitly accept the valid local-only mutable-corpus backup and the absence
   of a source-file backup.

Until one disposition is named, backup preflight is `NO-GO`.

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

1. Freeze a fresh exact grant and supersession authority only after source,
   predecessor evidence, backup disposition, runtime, config, transform,
   provider, dimension, watcher, and writer-census checks all pass.
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
  supersession model, backup decision gate, budget, and measurement plan.
- **Copilot:** audit evidence preservation, filesystem containment, authority
  binding, budget carry-forward, fail-before-mutation ordering, and isolation.

Each reviewer returns written `PASS` or `FAIL`, with blockers separate from
advisories. A deferral or missing review is not a conflict.

## Recommendation

`NO-GO` for a live successor bootstrap now. After same-revision Kiro and
Copilot PASS, Ryan may issue a separate exact grant only if it names the backup
disposition and repeats all execution-day measurements. Runtime/config
promotion and watcher restart remain later, separate grants.

## TL;DR

The reviewed supersession implementation is merged and the exact Kiro source
is unchanged. A successor may spend at most six additional DeepSeek attempts,
eight lifetime, across one invocation and one recovery. The local corpus backup
is valid; current offsite availability is unverified and must be restored or
explicitly accepted before Ryan grants execution.
