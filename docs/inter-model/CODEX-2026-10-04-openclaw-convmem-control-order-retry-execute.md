# Execute Handoff: Switchboard V4 Receipt-Order Freeze Retry

**Arc:** ConvMem Switchboard
**Date:** 2026-10-04
**Author:** Codex supervision lane
**For:** Astra execution lane
**Authorization:** Ryan, 2026-10-04 — explicit `granted` response after PR `#358`
merged the post-review status snapshot

---

## Resume state

| Field | Value |
|---|---|
| **State** | `AUTHORIZED / NOT_STARTED` — exactly one synthetic retry |
| **Grant branch** | `plan/2026-10-04-openclaw-convmem-control-order-retry-grant` |
| **Authorization base** | merged main `2c22898b9974198fedfdf31459cb3efbcdfd08ea` |
| **Semantic parent** | `b279a5c9b1725157e663da610f7f66cb75773522` |
| **Reviewed overlay** | `e649da29108ec17165ec9c5fd129f5e41a183ac4` |
| **Reviewed plan merge** | PR `#357`, `c5cb7c7871354b97157f392123a658a1adab4210` |
| **Status merge** | PR `#358`, `2c22898b9974198fedfdf31459cb3efbcdfd08ea` |
| **Push status** | Grant branch must be read from its pushed origin tip before execution |
| **PR** | Not opened; execution does not authorize PR creation or merge |
| **Ryan GATE** | None for this exact one-shot synthetic retry; every deviation or second attempt requires a new Ryan grant |

## Authoritative two-SHA grant

```text
SEMANTIC_PARENT_SHA=b279a5c9b1725157e663da610f7f66cb75773522
REVIEWED_OVERLAY_SHA=e649da29108ec17165ec9c5fd129f5e41a183ac4
AUTHORIZED_ATTEMPTS=1
AUTHORIZED_PROCESS_COUNT=1
AUTHORIZED_MODE=synthetic-freeze
```

The two values above are the grant. The squash-merge and status SHAs are traceability
only and may not replace either governing SHA. The exact normative contract is:

1. `docs/plans/STATUS-openclaw-convmem-integration.md`
2. `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` §18.43, retaining
   §§18.31–18.42 unchanged
3. `docs/plans/EXECUTION-openclaw-convmem-integration.md` §10.41
4. `docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md` M11 and §7
5. this handoff

Any conflict, missing value or changed governing SHA is `PAUSE`; Astra does not choose
between readings.

## Exact fresh coordinates

At grant authoring time all three coordinates were absent:

```text
COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa
PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4.partial
FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4
```

They are single-assignment. Before any creation, Astra must recheck all three with
no-follow metadata operations. Pre-existence of any coordinate is `PAUSE`; do not
delete, rename, chmod, repair, resume or reuse it.

## Authorized operation

Execute exactly one reviewed shared-core v4 synthetic freeze:

1. Setup may create only the exact coordinate parent and `PARTIAL_ROOT`, then
   exclusive-create the plan-derived author as row zero. The author is written once,
   mode `0644`, file-`fsync`ed, closed, the partial directory is `fsync`ed, and row
   zero is reopened no-follow and revalidated before launch.
2. The new author must be derived from the two-SHA reviewed plan. It may not copy,
   patch, import, execute, source or claim acceptance from any rejected author/root.
3. Launch exactly one interpreter process using the frozen fourteen-member synthetic
   argv, literal `-S` at argv position 1, partial-root cwd, exact five-key environment
   and sole verb `synthetic-freeze`. No wrapper, shell pipeline, caller-side reader,
   extra process or subprocess is permitted.
4. The process independently revalidates and repeats row-zero file/directory
   durability before ledger event 1. It uses the exact phase-bound coordinate-parent
   directory capability once before and once after final rename with the frozen flags,
   ordering and four counters.
5. Run one clean full-cardinality synthetic baseline and exactly the unchanged 52
   controls: `W001`–`W042` and `F001`–`F010`. Control execution order is not receipt
   authority.
6. Build the expected receipt ID set exactly once as `F001`–`F010` plus
   `W001`–`W042`, sort the complete set by raw UTF-8 bytes, index the independently
   executed receipts uniquely by `control_id`, and emit rows only by iterating that
   expected list.
7. Reject missing, extra, duplicate, family-concatenated or unstable IDs. Bind every
   row's unchanged ID, mutation, expected/observed code, verdict, created flags and
   `passed` value. Run the same aggregate validator for the clean baseline and every
   control path.
8. After the at-most-sixteen-iteration size fixed point, canonicalize and parse the
   final receipt bytes with the production parser and require exact F-then-W array
   equality before the first governed output write. Any later reorder or serializer
   drift is existing `F010`/`PAUSE`; there is no `F011`.
9. Preserve the exact six freeze roles, 22-event ledger with two null digests,
   nonrecursive identities, canonical stdlib dependency reader, fourteen-/twenty-
   member no-site argv contract, `F002` slices, schemas, mappings and serializers.
10. On success, freeze the six members to mode `0444`, the final root to mode `0555`,
    prove staging/final byte and mode equality, and atomically rename once. No output
    is accepted merely because the process reports `PASS` or exits zero.

## Frozen ceilings and access boundary

```text
MAX_PROCESS_COUNT=1
MAX_TOTAL_WRITTEN_BYTES=1073741824
MAX_PEAK_RSS_BYTES=2147483648
REAL_INPUT_READ_BYTES=0
NETWORK_REQUESTS=0
RUNTIME_READS=0
RETAINED_SOURCE_READS=0
SUBPROCESSES=0
```

Synthetic inputs, disposable outputs, freeze members, temporary files and the setup-
created author stay inside the exact reviewed ledger. Forecast bytes must equal
observed bytes and remain within the cap. Sparse files, preallocation, compression,
hard links, reflinks, deduplication, unledgered writes, misplaced null digests or
unstable sizes are `PAUSE`.

## Immutable rejected evidence

The prior sealed tree `d399e3561740f9f9be5cd1eab0e69f7dd788b5c1398d3f38d9e37dd18af2c37e`,
receipt `8d3ecbe08de5047a5eee473cf64958479a4062f4cd235b0544cfb8a39474cb9a`,
its `816b713…` coordinate, every earlier rejected root/source and every prior grant
remain consumed and non-reusable. This grant authorizes no mutation, copying,
execution, import, acceptance transfer or in-place remedy for them.

## Stop conditions

Stop immediately with `PAUSE` on any pre-existing coordinate, SHA mismatch, plan
ambiguity, root/path drift, author/source mismatch, extra process, external access,
counter mismatch, missing/extra/duplicate receipt ID, non-F-then-W final array,
control/schema/role change, ceiling breach, durability-order failure, ledger mismatch,
unstable metadata, write error, parse/equality failure or unexpected exception.

On failure, preserve the exact partial or final state where it stopped. Do not repair,
delete, retry, resume, roll back, widen scope or run a second process. Return the
failure stage, exception, coordinate state and all counters to Codex.

## Required return packet

Return in chat, without creating a repository log:

- process exit status and reported status;
- accepted/not-accepted disposition kept separate from process status;
- coordinate parent, partial and final presence/modes;
- all six member paths, sizes, modes and SHA-256 values;
- canonical tree hash and total bytes;
- clean-baseline count and all 52 control results;
- actual first ID, family boundary and last ID;
- expected first ID, family boundary and last ID;
- write-ledger hash, forecast/observed bytes and peak RSS;
- row-zero setup/governed durability counters;
- coordinate-parent pre-/post-rename counters;
- real-input/network/runtime/retained-source/subprocess counters; and
- exact stop stage if any value is not accepted.

Codex then records the returned identities in a plan-only overlay. Kiro reviews that
exact overlay before any real-author grant. Astra does not claim capability acceptance,
read the real packet/disposition or proceed to authoring.

## Explicit exclusions

This grant authorizes no real packet/disposition/repository/runtime/retained-source
read, network request, acquisition, ownership or license choice, binary repair, build,
publication, CI admission, product/test/config/inventory/R2b edit, PR `#342` update,
PR creation, merge, deployment, real OpenClaw, live data, watch activation, promotion
or Gate D/W/D-V/E/F action.

## Copy-paste Astra launch prompt

```text
You are Astra, the sole execution lane for one bounded synthetic operation in
Arc ConvMem Switchboard.

Ryan authorized exactly one v4 receipt-order freeze retry:
SEMANTIC_PARENT_SHA=b279a5c9b1725157e663da610f7f66cb75773522
REVIEWED_OVERLAY_SHA=e649da29108ec17165ec9c5fd129f5e41a183ac4
AUTHORIZATION_BASE_MAIN_SHA=2c22898b9974198fedfdf31459cb3efbcdfd08ea

Read the Switchboard STATUS, Architecture §18.43, Execution §10.41, milestone
M11/§7 and this handoff completely. Recheck that the exact 946b469… coordinate
parent, v4.partial and v4 roots are all absent. If any exists, PAUSE without
mutation.

Create and run only the one reviewed shared-core synthetic-freeze transaction at
those exact roots. Preserve §§18.31–18.42, use one process, stay below 1 GiB
written and 2 GiB peak RSS, and perform zero real-input/network/runtime/retained-
source reads and zero subprocesses. The final parsed receipt array must be exactly
F001–F010 then W001–W042 before output acceptance. Any failure preserves the
stopped coordinate and grants no repair, deletion, resume or retry.

Return the complete required packet from this handoff and stop. Do not read real
inputs, create a work-item packet, edit the repository, open a PR or continue to
another gate.
```

## Leaving / picking up checklist

**Codex:**

- [x] PR `#357` merge and Kiro exact-main PASS recorded.
- [x] PR `#358` status merge confirmed at `2c22898…`.
- [x] Ryan's exact one-shot grant recorded.
- [x] Fresh coordinate parent/partial/final rechecked absent before handoff authoring.
- [x] Commit and push this handoff with STATUS and LATEST routing.

**Astra:**

- [ ] Run the session-start protocol and state Goal/role/system/next plus the arc.
- [ ] Resolve and read the pushed grant-branch tip.
- [ ] Verify the two governing SHAs and all three absent coordinates.
- [ ] Execute at most one process under the exact ceilings and exclusions.
- [ ] Return the complete result packet and stop.

## TL;DR

- Ryan authorized one synthetic retry governed by `b279a5c9…` + `e649da29…`.
- Only the absent `946b469…` coordinate may be created; receipt order must be exact
  F001–F010 then W001–W042.
- One process, at most 1 GiB written and 2 GiB RSS, with zero real/external access.
- Any discrepancy is `PAUSE`; no repair, second attempt, real authoring, PR or merge.
