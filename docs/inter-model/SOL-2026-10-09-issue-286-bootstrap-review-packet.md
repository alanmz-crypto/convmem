# Sol Review Packet — Issue #286 One-Source Kiro Bootstrap

**Arc:** Codex  
**Issue:** [#286 — Make changed-file indexing incremental at chunk/append level](https://github.com/alanmz-crypto/convmem/issues/286)  
**Prepared:** 2026-10-09 by Sol  
**Review lanes:** Kiro for route design and source/bootstrap assumptions; GitHub Copilot audit lane for safety and isolation  
**State:** review packet only; no live grant and no operational authority

## Decision Ryan will make after review

Ryan may later decide whether to authorize one controlled bootstrap of the exact
Kiro transcript named below. This packet does not authorize that bootstrap. It
also does not authorize a runtime/config promotion, a watcher restart, an
append test, another source, or broader adapter coverage.

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

The offline copy of the Restic password is currently missing, as reported by
doctor. The primary password is available now, so local rollback is not blocked,
but machine-loss recovery remains weaker than the two snapshot ids alone imply.

Before any later bootstrap grant, Ryan must either accept that the recovery
snapshot covers every mutation target but not the read-only source, or require
a separately verified byte-for-byte source backup. The exact local snapshot id
must also be re-resolved on the execution day; the id above is packet evidence,
not durable authority for a later run.

## Proposed one-time paid-processing budget

The proposed grant values are:

```json
{
  "source": "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl",
  "prefix_sha256": "dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741",
  "complete_boundary": 225091,
  "max_chunks": 2,
  "embed_dimension": 768,
  "backup_snapshot": "e8bb7b66bd64a379a624cf29be1cfd959b2955535b9b5df649047cced2d577a8"
}
```

This is a field map for review, not a grant file. No mode-0600 JSON authority
artifact has been created.

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

Accordingly, this packet asks Ryan to consider a budget of **2 chunks and 4
successful paid generations**, with no dollar claim. A hard request or dollar
cap is not enforceable by the merged bootstrap command. If either reviewer
requires that stronger cap, the recommendation must remain `NO-GO` until a
separately authorized implementation correction or provider-side metering
control exists.

## Measurement plan for a later authorized run

### Gate A — re-prove before any provider or corpus write

1. Re-fetch the reviewed runtime revision and confirm the one-shot command is
   the PR #365 implementation or a separately reviewed successor.
2. Confirm the watcher is still `inactive` and `disabled`, with `MainPID=0`.
3. Re-capture source canonical path, device, inode, metadata digest, complete
   boundary, complete-prefix digest, accepted messages, and chunk count. Refuse
   on any difference from the eventual Ryan grant.
4. Resolve a current-day complete-data-v2 local snapshot by full id and verify
   its matching offsite lineage. Record the exact paths and tag. Resolve the
   source-backup disposition described above.
5. Capture source-scoped pre-state ids and counts from both Chroma collections,
   the processed entry, exported units, dedupe sidecars, and the absence of an
   incremental checkpoint. Capture global counts so unrelated deltas are
   detectable.
6. Capture provider-side usage immediately before the run if DeepSeek exposes
   request/token/cost telemetry. If no independent telemetry is available,
   state before execution that HTTP-attempt and dollar claims will be
   unverified.

### Gate B — one-shot bootstrap receipt

Run only the one-shot bootstrap command with the exact, Ryan-approved grant.
Preserve stdout and stderr. Require outcome `committed`, mode
`initial_full`, `chunks <= 2`, and the full provider counter map. Any refusal,
digest mismatch, source mutation, unexpected retry, or budget overrun stops the
operation; it does not authorize a watcher fallback or a second grant.

### Gate C — coverage and cost reconciliation

1. Re-read the checkpoint and require a complete state bound to the granted
   path, prefix digest, byte boundary, format, transform fingerprint, dimension,
   and active generation.
2. Require the processed entry and both Chroma collections to describe one
   complete physical keep set for that generation. Reconcile the exact summary
   and unit ids with the checkpoint and export, not counts alone.
3. Confirm no unrelated source ids changed. Record before/after global and
   source-scoped counts and any source replacement delta.
4. Compare the receipt's paid logical counters with provider-side request,
   token, and cost deltas. Report all layers separately. If provider telemetry
   is absent or inconsistent, make no actual-cost claim.
5. Re-run read-only retrieval spot checks for material represented by both
   chunks and record whether every accepted source message is covered.
6. Keep the watcher stopped. Bootstrap success does not authorize config
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
3. Is mutation-target Restic coverage sufficient when the read-only source is
   outside the snapshot, or must a source copy be mandatory?
4. Is the 2-chunk / 4-successful-generation budget acceptable despite the
   nested retry and independent-metering limitation?

### GitHub Copilot safety and isolation audit

1. Does the packet preserve the exact-source, default-off, one-shot bootstrap,
   watcher-disabled, and no-fallback boundaries merged in PR #365?
2. Does it avoid creating authority through the example field map or through
   stale snapshot/digest evidence?
3. Are rollback coverage, source revalidation, unrelated-source isolation, and
   post-run physical keep-set checks sufficient?
4. Does the paid-call accounting limitation create a safety blocker for a
   capped live grant?

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

Proceed to review, but do not request a live bootstrap grant yet. The source,
digest, pre-state, dimension, and mutation-target backup are concrete. The
reviewers must decide whether lack of source-file backup and lack of a hard
HTTP/token/dollar ceiling are acceptable for the next Ryan-controlled gate.

## TL;DR

- Exact candidate: one idle Kiro transcript, 68 messages, 225091-byte complete
  prefix, digest `dfea479e...732741`, two chunks, dimension 768.
- Legacy pre-state is 2 summaries and 17 units with no incremental checkpoint;
  current local/offsite Restic coverage protects mutation targets but not the
  read-only source.
- Expected paid bootstrap work is four successful DeepSeek generations. The
  merged command does not hard-cap nested HTTP retries, tokens, or dollars, so
  reviewers must treat that accounting limitation explicitly.
- No live bootstrap, config/runtime promotion, or watcher action is authorized.
