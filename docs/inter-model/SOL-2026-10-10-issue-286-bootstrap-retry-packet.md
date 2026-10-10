# Sol Review Packet — Issue #286 Kiro Bootstrap Retry

**Arc:** Kiro bootstrap  
**Issue:** [#286 — Make changed-file indexing incremental at chunk/append level](https://github.com/alanmz-crypto/convmem/issues/286)  
**Prepared:** 2026-10-10 by Sol  
**Review lanes:** Kiro for route design and source/bootstrap assumptions; GitHub Copilot audit lane for safety and isolation  
**State:** review packet only; `NO-GO` for a live retry; no operational authority

## Decision consequence

The paid-attempt accounting correction merged through PR #377, but the failed
production transaction cannot safely use it. The source state still contains a
`transform_failed` transaction bound to the old grant and old runtime. The old
grant's durable ledger is exhausted under the corrected runtime's conservative
legacy-row rule, while a new grant is rejected by the coordinator's exact
transaction-binding check.

Ryan should not grant a retry from this packet. The next safe step is a narrow,
hermetic implementation that can supersede this exact pre-apply failed
transaction without deleting its evidence, while carrying forward the two
DeepSeek attempts already spent. That correction needs its own review and merge
before a runnable exact-resource grant can be prepared.

This packet does not authorize code changes, a bootstrap, a recovery invocation,
a runtime or config promotion, or a watcher operation.

## Who / what / when / why / how

- **Who:** Sol prepared the packet; Kiro reviews route and bootstrap assumptions;
  GitHub Copilot audits safety and isolation; Ryan retains every live-operation
  grant.
- **What:** one exact Kiro transcript and its current failed bootstrap state.
- **When:** after PR #377 merged on 2026-10-10 as
  `d1c28f9f9781d4b704ff221a3938d8446edcc690` and all six checks passed.
- **Why:** the first paid run exposed shared DeepSeek/Ollama attempt accounting;
  the correction fixes future ledgers but does not make the existing failed
  transaction recoverable under a new runtime.
- **How:** preserve the exact source and old operation evidence, implement an
  explicit grant-bound supersession for this one pre-apply state, then prepare a
  new packet and obtain a separate Ryan grant.

## Exact source identity

Read-only measurements on 2026-10-10:

| Field | Exact observation |
|---|---|
| Canonical source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Format | `jsonl_kiro_session` |
| Owner / mode | UID `1000`; mode `0600` |
| Device / inode | `66306` / `23609783` |
| Size / complete boundary | `225091` bytes / `225091` bytes |
| Full-prefix SHA-256 | `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741` |
| Accepted messages | `68` |
| Chunking | size `60`, overlap `10`; exactly `2` chunks |
| Session metadata SHA-256 | `68ef7b750290655ef00438125e5b3d38bb3ea65d342372acce6e0369c263c662` |
| Source state id | `13c4c30c5c644a1771f0372e1b16fde35ab8cd283c26f594b96f800aad3976d2` |

The source digest, size, identity, and metadata digest are unchanged from the
failed run. Any later live packet must repeat these checks immediately before
execution. A changed path, device, inode, boundary, digest, metadata digest, or
chunk count invalidates these facts.

## Current corpus coverage

The failed transform did not replace the legacy projection:

- `processed.json` still records the source under digest
  `dfea479e...732741` with `2` chunks and `17` units;
- read-only Chroma SQLite inspection still finds exactly `2` source rows in
  `conversation_summaries` and `17` in `knowledge_units`;
- both collections declare dimension `768`; and
- no checkpoint exists for this source.

The required embedding dimension remains **768**. A retry must require dimension
768 before any provider request or projection write.

## Backup coverage and accepted limitation

The named rollback baseline is local Restic snapshot
`ac1087c862cae7e43b72ca4978379d4c07a0550b9cf2964557dfed9601da3954`,
created `2026-10-10T00:10:43.236381111-05:00`, tagged
`convmem-data-v2`, for `/home/lauer/.local/share/convmem`.

Read-only `restic snapshots --no-lock` confirmed the full snapshot id, tag,
timestamp, and covered path. It predates the failed invocation and covers the
mutable corpus: Chroma, `processed.json`, exports, dedupe sidecars, locks, and
the incremental-state root as it existed at snapshot time.

Ryan has explicitly accepted these limitations for this bootstrap:

- the local snapshot has no matching offsite copy; and
- the read-only Kiro source is outside the snapshot.

The bootstrap must never write the source. The prefix and metadata checks detect
source drift but do not replace a source backup. The `backup_snapshot` grant
field remains descriptive; execution preflight must independently confirm the
snapshot before any provider or corpus operation.

## Failed operation evidence

The durable failed state is:

| Field | Exact value |
|---|---|
| Transaction phase | `transform_failed` |
| Failure | `ProviderAttemptBudgetExceeded` / terminal `provider_http_budget_exhausted` |
| Transaction id | `18d83bf3246c4c19b823e2cd950fe8c0` |
| Transaction SHA-256 | `5931be7c5faff4294b70e3c5f30da191e7906225f9b42369a714b26e922920ac` |
| Old operation id | `732440c417fece9a36ac3d5381adf7b155be6a265576949f85823e3edce7e7c8` |
| Old grant fingerprint | `dc56d5af9e5ed353da08527942f18fbc3856d482852554626ebfbbc22c3327ae` |
| Old runtime | `3df86385b5dc19512c0140849ea147d8ed34dcc4` |
| Config SHA-256 | `be9be9e963eade2a095d61fbda48a79db7e9fad4305d4af6e9c0ee68d7ce9413` |
| Transform fingerprint | `dfc1b62523a988f39a917cec5ddb81ec04c08a8db80b13131dff2d4588f2050d` |
| Attempts observed | `8`: `2` DeepSeek generation requests and `6` local Ollama embedding requests |
| DeepSeek usage observed | `8574` total tokens (`2709` + `5865`) |
| Projection apply | none; transaction failed during transform |

The operation artifacts, transaction, and source snapshot remain in the source
state directory. They must remain immutable evidence.

## Why neither current recovery path is usable

### Old same-grant recovery

The old grant is bound to runtime `3df86385...`. Running the corrected code from
PR #377 changes the runtime binding and therefore cannot satisfy that grant.
Running the old code would repeat the accounting bug.

The old attempt rows also predate the new `paid_cap_consumed` field. The merged
correction deliberately counts legacy or malformed rows conservatively. All
eight old rows therefore consume the old ledger's ceiling, so another DeepSeek
request would be refused before transport even if the runtime mismatch were
ignored. Editing the append-only ledger or running corrected code in a dirty
worktree under the old Git SHA is forbidden.

### Fresh grant

A fresh grant produces a new operation id and fingerprint. The coordinator
reads the existing `transform_failed` transaction first and requires its grant,
operation, and binding fingerprints to match the new invocation. They do not,
so the run returns `bootstrap_replay_grant_mismatch` before it can progress.

PR #377 corrected future paid-cap accounting. It did not add failed-operation
supersession or change the exact transaction-binding invariant.

## Paid-processing budget for a future successor operation

The original Ryan grant allowed at most `8` DeepSeek HTTP attempts across the
bootstrap and one same-grant recovery. Two DeepSeek attempts were actually
spent. To preserve that lifetime ceiling, the recommended successor allowance
is:

- maximum `2` chunks;
- maximum **6 additional DeepSeek HTTP attempts**, cumulative across one
  successor invocation and at most one same-grant recovery;
- maximum lifetime total for this source bootstrap effort: **8 DeepSeek HTTP
  attempts**, including the two already recorded;
- local Ollama embedding requests remain durably observed but do not consume
  the paid DeepSeek cap; and
- no token or dollar guarantee is inferred from the HTTP-attempt ceiling.

Six remaining attempts permit four first-attempt generations plus two retries.
They do not cover the worst case of two HTTP attempts for each of four logical
generations. Raising the successor cap to eight additional attempts would make
the lifetime total ten and requires a new, explicit Ryan budget decision.

No operation id or executable grant is provided because no reviewed runtime can
currently supersede the existing transaction safely.

## Required supersession correction

A later Cursor implementation should be limited to this exact failure class and
must satisfy all of these conditions before reviewers consider a retry:

1. Accept supersession only for an exact `bootstrap_existing` transaction in
   phase `transform_failed`; never for `APPLYING` or an unknown phase.
2. Bind the old operation id, grant fingerprint, transaction id, transaction
   digest, source identity, prefix digest, config digest, and transform
   fingerprint in the successor authority.
3. Prove from phase and inventories that no Chroma, checkpoint, processed,
   export, or dedupe apply occurred.
4. Preserve the old transaction, attempt ledger, usage ledger, terminal receipt,
   and source snapshot as immutable predecessor evidence.
5. Create explicit predecessor/successor lineage; do not delete, overwrite, or
   reinterpret the old rows.
6. Carry forward the two recorded DeepSeek attempts when enforcing the lifetime
   cap. The six local Ollama rows remain observed evidence and do not become
   paid attempts.
7. Start the successor with no prepared-cache claim: the failed state contains
   no prepared chunk cache, so both chunks may require transformation again.
8. Keep the exact-source gate, dimension preflight, provider/config binding,
   redirect denial, watcher-disabled check, one-recovery limit, and durable
   terminal accounting intact.
9. Fail before provider transport or corpus mutation on any mismatch.

This is an implementation prerequisite, not authority to implement or execute
it.

## Measurement plan after a later reviewed correction and grant

### Before execution

1. Recheck the exact source identity, boundary, full-prefix digest, metadata
   digest, 68-message count, and two-chunk count.
2. Reconfirm local snapshot `ac1087...3954`, the accepted offsite/source
   limitations, dimension `768`, the exact reviewed runtime, config digest, and
   transform fingerprint.
3. Require the watcher to remain inactive and disabled with `MainPID=0`, and
   capture a no-other-writer census.
4. Capture the source-scoped and exact unrelated-state inventories for both
   Chroma collections, processed state, export bytes, dedupe sidecars, and the
   complete incremental state directory.
5. Capture the old operation's two DeepSeek attempts and 8574 tokens as the
   predecessor baseline.

### During the one authorized successor operation

1. Record every DeepSeek and Ollama transport attempt before transport.
2. Enforce no more than six additional DeepSeek attempts across the initial and
   one recovery invocation.
3. Record per-response DeepSeek usage, logical summarize/distill attempts and
   successes, observed local embedding calls, terminal outcome, transaction
   phase, and remaining recovery allowance.
4. Stop on any mismatch, budget exhaustion, unexpected retry, or second
   failure. Do not change the grant or switch routes.

### After execution

1. Reconcile predecessor plus successor DeepSeek attempts and require the
   lifetime total to be at most eight.
2. Reconcile provider usage records with any available provider-side request
   and token telemetry; report discrepancies rather than estimating them away.
3. Require a complete checkpoint bound to the exact path, prefix, boundary,
   dimension, transform fingerprint, active generation, and successor lineage.
4. Require exact agreement among checkpoint keep sets, the two Chroma
   collections, `processed.json`, and export rows. Verify coverage of all 68
   accepted messages across both chunks.
5. Recompute every unrelated-state inventory and require equality. Counts alone
   cannot clear isolation.
6. Keep the watcher disabled. A successful bootstrap still does not authorize
   config promotion, watcher restart, an append test, or another source.

## Review questions and verdict contract

Both reviewers must target the same branch-tip commit and this file's exact
SHA-256 supplied in their prompts. Each must return `PASS` or `FAIL`, identify
blockers separately from advisory findings, and evaluate this packet's `NO-GO`
recommendation. A missing review, deferral, or incomplete verdict is not a
Sol-High conflict.

### Kiro design review

1. Is the failed transaction analysis faithful to the bootstrap/replay design?
2. Is explicit pre-apply failed-operation supersession the correct prerequisite,
   and are its required bindings and lineage sufficient?
3. Are the exact source, backup disposition, dimension, remaining budget, and
   coverage/call measurement assumptions coherent?
4. Does the packet correctly withhold a live retry grant?

### GitHub Copilot safety and isolation audit

1. Can the old same-grant recovery or a fresh grant proceed safely under the
   merged code, or does exact transaction binding block both as stated?
2. Does the proposed supersession boundary prevent replay-authority laundering,
   evidence deletion, budget reset, and unrelated-source mutation?
3. Is the six-additional-attempt cap correctly derived from two already spent
   attempts under Ryan's original lifetime ceiling of eight?
4. Are the pre/post inventories and stop conditions sufficient for a later
   exact-resource retry packet?

## Recommendation to Ryan

**Do not authorize a live retry from this packet.** The source facts, local
backup, dimension, remaining budget, and measurement plan are concrete, but the
merged runtime has no safe path from the existing failed transaction into a new
corrected operation.

If both reviewers pass this packet, Ryan's next decision is whether to authorize
Cursor to implement the narrow failed-operation supersession contract above.
After that implementation is reviewed and merged, Sol should prepare a new
execution-day packet with an exact successor runtime, operation id, grant
fingerprint, revalidated source and backup, six-additional-attempt cap, and one
same-grant recovery allowance.

## Explicit non-authority

This packet and its reviews authorize none of the following:

- live bootstrap or recovery;
- editing, deleting, moving, or reclassifying the failed operation evidence;
- creating an executable grant;
- changing runtime or config;
- starting or enabling the watcher;
- modifying the Kiro source or corpus; or
- extending the route to another source or adapter.

## TL;DR

- The exact source remains unchanged: digest `dfea479e...732741`, two chunks,
  dimension 768, with local rollback snapshot `ac1087...3954` and Ryan's
  accepted offsite/source limitations.
- The first run spent two DeepSeek attempts and 8574 tokens, then left a
  `transform_failed` transaction bound to the old grant.
- The old recovery is budget/runtime blocked; a fresh grant is transaction-
  binding blocked. PR #377 fixed future accounting but did not add safe
  supersession.
- Recommendation: `NO-GO` for a live retry. Review and implement explicit
  predecessor-preserving supersession first, with at most six additional
  DeepSeek attempts so the lifetime total stays at eight.
