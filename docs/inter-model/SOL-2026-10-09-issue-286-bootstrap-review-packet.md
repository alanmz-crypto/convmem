# Sol Review Packet — Issue #286 One-Source Kiro Bootstrap

**Arc:** Codex
**Issue:** [#286 — Make changed-file indexing incremental at chunk/append level](https://github.com/alanmz-crypto/convmem/issues/286)
**Prepared:** 2026-10-09 by Sol
**Review lanes:** Kiro for route design and source/bootstrap assumptions; GitHub Copilot audit lane for safety and isolation
**Revision:** corrected after the same-revision Kiro/Copilot conflict on commit `f0895a20dd25722b46245aa4a0945c86d5fb741f`
**State:** review packet only; `NO-GO` for a live grant under the merged command;
no operational authority

## Sol-High conflict resolution

The first revision produced the required five-field conflict record:

- **Artifact:** packet commit
  `f0895a20dd25722b46245aa4a0945c86d5fb741f`, file
  `docs/inter-model/SOL-2026-10-09-issue-286-bootstrap-review-packet.md`,
  SHA-256 `3a044c2b54b2e2a96826584d8edccf1853c5bf4fe36271aa219a3cd5acbee3e1`.
- **GitHub Copilot audit-lane verdict:** `FAIL` — the packet expected the
  wrong committed mode and lacked sufficient recovery, provider/config
  binding, failure accounting, and exact unrelated-source isolation evidence.
- **Kiro verdict:** `PASS` — the source and existing-source route assumptions
  were coherent, with backup disposition and the missing hard cost cap treated
  as conditions for a later grant.
- **Material proposition in conflict:** whether the packet was safe and
  complete enough to support a live bootstrap grant under the merged command.
- **Negative confirmation:** this was the same artifact and revision with
  written opposing `PASS` and `FAIL` verdicts; it was not a single `FAIL`,
  deferral, abstention, silence, missing or incomplete review, or a
  different-revision comparison.

Sol resolves that proposition in Copilot's favor: revision `f0895a2` was not
safe or complete enough to support a live bootstrap grant.

Kiro's `PASS` remains evidence that the chosen source, existing-source route,
dimension, and later-grant questions were coherent. It does not answer the
objective mode mismatch or supply the missing failure recovery, effective
provider binding, and exact unrelated-source isolation evidence identified by
Copilot. The corrected packet therefore:

- requires committed mode `bootstrap_existing`, with `replay_forward` reserved
  for recovery of the same already-authorized transaction;
- makes failure state and the one supported recovery path explicit;
- freezes and verifies the effective provider/config inputs and disables
  silent local fallback;
- replaces global-count isolation with exact non-source inventories; and
- treats the lack of a hard request/token/dollar ceiling and failure receipt
  as current implementation limits, not conditions reviewers can waive into
  existence.

This adjudication does not authorize code changes or any live operation.

## Decision Ryan will make after review

Ryan may later decide whether to authorize one controlled bootstrap of the exact
Kiro transcript named below, but this revision recommends against doing so with
the merged command. This packet does not authorize that bootstrap. It also does
not authorize a runtime/config promotion, a watcher restart, an append test,
another source, or broader adapter coverage.

Ryan merged the guarded Kiro route in PR #365 on 2026-10-09 as `f3171fc`. That
merge put the default-off production boundary, exact-source gate, and one-shot
bootstrap command on `main`. It made no live configuration or data change. The
watcher remains inactive and disabled. Cursor JSONL and Crush SQLite remain on
the legacy route, so this one-source Kiro exercise cannot establish an overall
DeepSeek cost reduction.

## Exact source candidate

The candidate is the closed, idle Kiro session previously used as the Arc
Codex two-chunk canary source. Sol re-measured it read-only with the merged
adapter and route code at `origin/main` `1bcc682c63a6d4568c36022cc153c857aa9e1ecd`.

| Field | Frozen observation |
|---|---|
| Exact canonical source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Detected format | `jsonl_kiro_session` |
| Owner / mode | UID `1000`; mode `0600` |
| Device / inode | `66306` / `23609783` |
| File size | `225091` bytes |
| Complete-prefix boundary | `225091` bytes |
| Complete-prefix SHA-256 | `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741` |
| Accepted messages | `68` |
| Production chunking | size `60`, overlap `10` |
| Transform chunks | `2` |
| Session metadata | sibling `session.json`; session id `sess_2628159e-d039-4646-a208-0a10a1b3e450`; workspace `/home/lauer/Projects/convmem`; status `idle` |
| Metadata SHA-256 | `68ef7b750290655ef00438125e5b3d38bb3ea65d342372acce6e0369c263c662` |
| Path checks | source and parent components are canonical and non-symlinked; source is a regular file |

The source changed after its September canary freeze, so the older digest
`1d76d2cc...` is superseded. A later live grant must repeat these read-only
checks immediately before execution. Any change to the path, identity,
metadata, byte boundary, or digest invalidates this packet's source facts.

## Existing production coverage

The source is already represented through the legacy route:

- `processed.json` has one entry keyed by the current full-file digest and
  reports `2` chunks and `17` units.
- Read-only SQLite inspection of the Chroma metadata segments finds exactly
  `2` source-scoped rows in `conversation_summaries` and `17` in
  `knowledge_units`.
- Both Chroma collections declare dimension `768`.
- The source has no incremental state directory and no incremental checkpoint.
  Its source-state id would be
  `13c4c30c5c644a1771f0372e1b16fde35ab8cd283c26f594b96f800aad3976d2`.

This is therefore an existing-source rebuild, not zero-call adoption. The
bootstrap must replace the source's legacy projection with one complete,
checkpoint-governed generation while leaving unrelated sources unchanged.

## Required embedding dimension

The required grant value is `768`.

Evidence is independent in two places: the installed
`nomic-embed-text:latest` model reports embedding length `768`, and both live
Chroma collections declare dimension `768`. The historical coordinator default
of `8` is test-only and is not acceptable for this source.

## Backup coverage

`convmem doctor` completed successfully during packet preparation and reported
current-day complete-data-v2 coverage:

| Layer | Exact observation | Coverage |
|---|---|---|
| Local Restic snapshot | `e8bb7b66bd64a379a624cf29be1cfd959b2955535b9b5df649047cced2d577a8`, tag `convmem-data-v2` | `/home/lauer/.local/share/convmem`: Chroma, processed log, exported units, dedupe sidecars, locks, and the incremental state root if created there |
| Offsite Restic copy | `b86e6cad90dd7e5a9de63777ceb656265dbb4f7ff6188788b5845d8c073a8346` | Doctor reported it as the offsite copy of the local snapshot above |
| Read-only source | Outside `CONVMEM_DATA_ROOT`; not covered by these two snapshots | The bootstrap contract never writes the Kiro transcript. The exact prefix digest and live revalidation protect against using changed bytes, but they are not a source backup. |

The `backup_snapshot` grant field is descriptive only: the merged script echoes
the value into its receipt but does not query Restic or prove that the snapshot
exists or covers the mutation targets. A later operator would have to verify
that separately before invocation.

The offline copy of the Restic password is currently missing, as reported by
doctor. The primary password is available now, so local rollback is not blocked,
but machine-loss recovery remains weaker than the two snapshot ids alone imply.

Before any later bootstrap grant, Ryan must either accept that the recovery
snapshot covers every mutation target but not the read-only source, or require
a separately verified byte-for-byte source backup. The exact local snapshot id
must also be re-resolved on the execution day; the id above is packet evidence,
not durable authority for a later run.

## Candidate grant facts and paid-processing budget

The following are review facts, deliberately presented as prose rather than a
copyable authority artifact. No mode-0600 grant file has been created.

- `source`: the exact canonical path in **Exact source candidate**.
- `prefix_sha256`: `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741`.
- `complete_boundary`: `225091`.
- `max_chunks`: `2`.
- `embed_dimension`: `768`.
- `backup_snapshot`: the execution-day verified full local snapshot id; the
  packet-time observation was
  `e8bb7b66bd64a379a624cf29be1cfd959b2955535b9b5df649047cced2d577a8`.

For two chunks, the expected paid work is capped conceptually at:

- `2` DeepSeek summarizations;
- `2` DeepSeek distillations; and
- `4` completed paid generations total.

Summary and unit embeddings use local Ollama and do not add paid DeepSeek calls.
The one-shot receipt reports `summarize`, `distill`, `summary_embed`, and
`unit_embed` counters.

There is an accounting limitation reviewers must decide explicitly. The
bootstrap enforces `max_chunks=2`, but it has no separate HTTP-request, token,
or dollar ceiling. The transform counter increments before each outer provider
call. The DeepSeek client can make up to two HTTP attempts inside one such call,
and the transform layer can retry non-fatal failures up to three times. In the
worst connection/timeout path, four logical generations could therefore issue
up to `24` outbound HTTP attempts, while the receipt can report at most `12`
outer attempts. Failed or ambiguous provider requests may still affect billing.

Accordingly, the measurable logical budget is **2 chunks and 4 successful paid
generations**, with no dollar claim. The merged command cannot enforce a hard
HTTP-request, token, or dollar ceiling. One invocation can make up to `24`
outbound DeepSeek attempts, and a recovery invocation can multiply that upper
bound if transformation is repeated. The receipt is emitted only after a
successful commit, so a failed or interrupted invocation has no durable
receipt for its provider counters.

This does not satisfy the requested *capped* paid-processing budget. A live
grant remains `NO-GO` until either:

1. a separately authorized implementation correction enforces the chosen
   request/token/dollar bound and durably records failure accounting; or
2. Ryan explicitly chooses a named provider-side metering control that rejects
   spend beyond a stated final value and independently preserves request,
   token, and cost evidence.

An acknowledgement of risk is not itself a cap.

## Effective provider and transform binding

The grant schema does not bind the effective transform configuration. The
merged command loads live config for chunking, provider/model selection, host,
base URL, minimum confidence, and embedding. If the DeepSeek key is absent, the
generation client can silently use a local fallback unless
`CONVMEM_FAIL_ON_FALLBACK=1` is set.

A corrected live design must bind or independently freeze all of these values:

- summarize and distill provider: `deepseek`;
- summarize and distill model: `deepseek-v4-flash`;
- DeepSeek base URL: `https://api.deepseek.com`;
- embedding provider/model: local Ollama `nomic-embed-text:latest`, dimension
  `768`;
- production chunk size `60`, overlap `10`, and minimum confidence `0.6`;
- exact config-file SHA-256 and exact reviewed runtime revision;
- `CONVMEM_FAIL_ON_FALLBACK=1`; and
- a positive, non-secret proof that the DeepSeek credential is present.

The preflight must resolve the generation binding to `deepseek` with
`fallback=false`, without printing the credential. It must recheck the config
digest immediately after execution. Because the current grant and receipt do
not carry these bindings, the stronger solution is an implementation correction
that places them inside the validated grant and durable receipt.

## Measurement plan for a later authorized run

### Gate A — re-prove before any provider or corpus write

1. Re-fetch the reviewed runtime revision and confirm the one-shot command is
   the PR #365 implementation or a separately reviewed successor.
2. Confirm the watcher is still `inactive` and `disabled`, with `MainPID=0`.
   Inventory all processes capable of writing the ConvMem corpus, and require
   an explicit no-other-writer window through final post-state capture.
3. Re-capture source canonical path, device, inode, metadata digest, complete
   boundary, complete-prefix digest, accepted messages, and chunk count. Refuse
   on any difference from the eventual Ryan grant.
4. Resolve a current-day complete-data-v2 local snapshot by full id and verify
   its matching offsite lineage. Record the exact paths and tag. Resolve the
   source-backup disposition described above.
5. Require the entire source state directory to be absent, rather than checking
   only for a checkpoint. Capture the processed source entry and exact source
   ids and selected metadata from both Chroma collections, exported source
   lines, and every source-related dedupe sidecar entry.
6. Build exact unrelated-state evidence: sorted non-source ids and selected
   metadata for both collections; a byte-preserving inventory and digest of
   non-source export lines; canonical digests of all non-source processed
   entries; and file/content digests for dedupe sidecars. Global counts are
   secondary diagnostics only.
7. Freeze and prove the effective provider and transform binding above,
   including config digest, runtime revision, failure-on-fallback, and the
   provider-side hard metering control. Capture provider-side request, token,
   and cost telemetry immediately before the run.

### Gate B — one-shot bootstrap receipt

Run only the one-shot bootstrap command with the exact, Ryan-approved grant.
Preserve stdout and stderr. Require outcome `committed`, mode
`bootstrap_existing`, `chunks <= 2`, and the full provider counter map. Recheck
the watcher as inactive/disabled with `MainPID=0` immediately afterward.

Any refusal before mutation ends the operation. Any exception, interruption,
missing receipt, digest mismatch, source mutation, unexpected retry, or budget
event after work begins enters the recovery procedure below. It never
authorizes a watcher fallback, a modified grant, or a new source.

### Failure and recovery procedure

The merged coordinator persists an `APPLYING` transaction plus rollback
material before applying prepared state. A failure after paid generation can
therefore leave a transaction, snapshot, rollback directory, or partially
applied generation even when the command emits no receipt.

1. Keep all writers and the watcher stopped. Preserve stdout/stderr and capture
   the state directory, transaction phase, snapshot, rollback material, corpus
   inventories, config digest, and provider telemetry read-only.
2. Do not manually delete state, rerun ingestion through another route, or
   edit the grant. Inspect whether the exact `APPLYING` transaction is present.
3. The implementation-supported recovery is one invocation with the **same
   exact grant**, source prefix, runtime, and effective config. It may return
   outcome `committed`, mode `replay_forward`; it can also roll back and return
   a noncommitted recovery result. A later Ryan grant would have to explicitly
   include this single recovery invocation in the same named operation. Without
   that clause, execution must stop for new authority.
4. Reconcile provider telemetry across the initial and recovery invocations.
   Because the current command has no failure receipt, command-local counters
   alone cannot prove actual calls or cost.
5. A noncommitted recovery result, missing rollback evidence, changed source or
   config, exhausted metering cap, or second failure ends the operation and
   returns control to Ryan. No further invocation is implicit.

### Gate C — coverage and cost reconciliation

1. Re-read the checkpoint and require a complete state bound to the granted
   path, prefix digest, byte boundary, format, transform fingerprint, dimension,
   and active generation. Record `active_generation`, `exact_suppressed`, and
   `semantic_queued` explicitly.
2. Require the processed entry and both Chroma collections to describe one
   complete physical keep set for that generation. Reconcile the exact summary
   and unit ids with the checkpoint and export, not counts alone.
3. Recompute every unrelated-state artifact from Gate A and require exact
   equality: non-source collection ids and metadata, non-source export lines,
   non-source processed entries, and dedupe sidecars. Investigate any byte or
   semantic difference; global counts cannot clear an isolation finding.
4. Compare the receipt's logical counters with provider-side request, token,
   and cost deltas across all authorized invocations. Report successful logical
   generations, outer attempts, HTTP attempts, tokens, and cost separately. A
   missing or inconsistent provider record fails the actual-call measurement.
5. Re-run read-only retrieval spot checks for material represented by both
   chunks and record whether every accepted source message is covered.
6. Reconfirm the effective config digest and the no-other-writer inventory.
   Keep the watcher stopped. Bootstrap success does not authorize config
   promotion, restart, or an append test.

### Later, separately granted activation measurement

A later grant would promote an exact reviewed runtime/config and restart the
watcher for this source only. The first append measurement must compare its
paid-call counters with the two-chunk legacy baseline, prove stable historical
chunk reuse, reconcile complete source coverage, and report Kiro results
separately from Cursor and Crush. Without that later measurement, the bootstrap
proves adoption and recovery readiness but not production cost reduction.

## Review questions and verdict contract

Both reviewers must target the same packet commit and full-file SHA-256 supplied
in their review prompts. Each must return `PASS` or `FAIL`, followed by findings
that identify the affected section and distinguish blockers from advisory
notes. `DEFER` or an incomplete review is not a PASS and is not a Sol-High
conflict.

### Kiro design review

1. Is this idle two-chunk Kiro transcript an appropriate first existing-source
   bootstrap target, including the fact that only a later resumed append can
   demonstrate reuse?
2. Are the source freeze, bootstrap assumptions, dimension proof, legacy
   pre-state, and coverage reconciliation complete enough for Ryan's next gate?
3. Does the corrected `bootstrap_existing` / `replay_forward` lifecycle match
   the merged coordinator, including the one same-grant recovery boundary?
4. Are the source-backup decision, effective transform binding, and the
   implementation prerequisites for a genuinely capped budget stated clearly?

### GitHub Copilot safety and isolation audit

1. Does the packet preserve the exact-source, default-off, one-shot bootstrap,
   watcher-disabled, and no-fallback boundaries merged in PR #365?
2. Does it avoid creating authority through the example field map or through
   stale snapshot/digest evidence?
3. Are rollback capture, same-grant recovery, source revalidation, exact
   unrelated-source inventories, and post-run physical keep-set checks
   sufficient and faithful to the merged code?
4. Does the packet correctly conclude that the merged command cannot yet
   provide a hard paid-processing cap or durable failure accounting?

## Explicit non-authority

This packet and both reviews authorize none of the following:

- executing `scripts/bootstrap-incremental-jsonl.py --execute`;
- creating an executable grant file;
- changing `~/.config/convmem/config.toml` or any systemd unit/drop-in;
- promoting a runtime revision or changing the runtime pin;
- starting or enabling `convmem-watch.service`;
- indexing the source through either route;
- modifying the Kiro transcript, Chroma, processed state, exports, dedupe data,
  checkpoints, backup repositories, or provider account controls; or
- extending incremental routing to Cursor, Crush, Codex, or another source.

## Recommendation before independent review

Request review of this corrected packet, but do not request a live bootstrap
grant. The source, digest, pre-state, dimension, and mutation-target backup are
concrete. The merged command still cannot enforce a capped paid-processing
budget, preserve failure accounting, or bind all effective provider/config
inputs inside the grant and receipt.

Ryan's next decision should be whether to authorize a narrowly scoped
implementation correction for those controls. Only after that correction and
same-revision Kiro/Copilot review should Ryan consider a live grant naming the
exact source, then-current digest, verified backup, dimension, hard budget, and
single recovery allowance. The source-file backup disposition and offline
Restic-password weakness must also be decided explicitly.

## TL;DR

- Exact candidate: one idle Kiro transcript, 68 messages, 225091-byte complete
  prefix, digest `dfea479e...732741`, two chunks, dimension 768.
- The first-review conflict is resolved in Copilot's favor: the committed mode
  is `bootstrap_existing`, and same-grant `replay_forward` is the sole supported
  recovery path after an interrupted applying transaction.
- Legacy pre-state is 2 summaries and 17 units with no source state directory;
  exact non-source inventories replace global counts as isolation evidence.
- Four successful DeepSeek generations are expected, but the merged command
  lacks a hard request/token/dollar cap, durable failure accounting, and full
  provider/config binding. The corrected recommendation is `NO-GO` pending a
  separately authorized implementation correction or named provider-side cap.
- No live bootstrap, config/runtime promotion, or watcher action is authorized.
