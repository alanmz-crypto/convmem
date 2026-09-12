# Implementation Handoff: Make the P2 canary safe to run against exact resources

**Arc: Codex**

**Date:** 2026-09-12

**Author:** Codex planning lane

**For:** Kiro design review, then Cursor implementation only after a separate Ryan grant

**Authorization:** Ryan, 2026-09-12 — continue corrective documentation on a separate branch without changing the frozen review target

This packet authorizes review only. It does not authorize implementation, Gate
0, P2, source writes, Chroma access, providers, configuration changes, watcher
operation, indexing, a PR, or activation.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `BLOCKED_ON_KIRO_REVIEW` |
| **Branch** | `plan/2026-09-12-codex-p2-gate0-enforcement-corrective` |
| **Base** | merged `main` runtime `7360a04e1e8154eca76eddf72c492251ae830c0f` |
| **Review target** | exact pushed branch tip supplied in the Codex handoff; do not review a moving target |
| **Push status** | push each documentation commit immediately |
| **PR** | not opened; separate Ryan authorization required |
| **Ryan gate** | Kiro PASS on this exact documentation revision before Ryan decides whether to grant Cursor implementation |
| **Track A ingest** | prohibited by this task's explicit no-index boundary |

### Frozen-target firewall

The Claude-reviewed P2 corrective target and the separate P2-T1 grant-packet
branch are immutable inputs to this work. Do not amend, rebase, merge into, or
force-update either target. This plan is based on merged runtime `7360a04` and
lives only on the branch above.

The exact-resource P2-T1 candidate grant reviewed by Kiro remains a faithful
description of the runtime it binds. Kiro's packet PASS authorizes nothing.
Because this corrective changes the runtime and grant contract, candidate
digest `c002385ee2e72e319ddcce2ab5d024c29abbe0031b86cbb26468cb604ee8c621`
must never be authorized or reused. A fresh packet and digest may be prepared
only after this corrective is merged and the source is remeasured.

## Goal, role, system, next action

**Goal:** make repeated Kiro-session ingestion incremental and crash-replayable,
then measure it once through a safe exact-resource production canary before any
activation is considered.

**My role:** identify where merged P2 enforcement diverges from the already
accepted canary architecture and bind a corrective implementation target for
independent Kiro review.

**The system currently:** the default-off coordinator, hermetic P1 harness, and
positive exact-resource P2 transfer seam are on `main`. The reviewed grant is
internally consistent, but merged runtime defaults can mutate during the
nominally non-mutating Gate 0, can report stubbed backup/model checks as PASS,
and can run a hermetic source-rewriting/fake-provider orchestration under P2
commands.

**Next action:** Kiro reviews this exact documentation revision. After PASS,
Ryan may issue a separate bounded implementation grant to Cursor. Nothing live
may run from the current runtime or candidate grant.

## Consequence for Ryan

Withhold exact-digest authorization and Gate 0. A successful Gate 0 from the
current launcher is not evidence that production resources, backup, installed
models, configuration, network denial, or rollback readiness were actually
proved. The safe recovery path is to correct the runtime first, merge it, then
remeasure the source and prepare a new exact-resource grant.

## Normative authority

This is an enforcement corrective, not a new architecture:

- `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` remains normative;
- `docs/plans/EXECUTION-codex-jsonl-production-canary.md` remains normative;
- this packet resolves implementation deviations from their P2-T2 through
  P2-T6 contracts; and
- where this packet is more explicit, it narrows implementation freedom to
  make the existing safety requirements testable. It does not broaden live
  authority.

## Reproduced deviations at merged runtime `7360a04`

| ID | Runtime evidence | Why it blocks live P2 |
|---|---|---|
| C1 | `ProductionCanaryBoundary.from_p2_grant()` writes the root marker, creates resource parents/evidence directories, and changes mode (`incremental_jsonl_canary.py:657-708`). | Grant loading/boundary construction occurs before Gate 0 and violates the required no-mutation preflight. |
| C2 | `_default_service_launcher_denied()` invokes `systemctl --user start convmem-watch.service` (`:940-954`). | A denial probe may start the watcher it is supposed to prove absent. |
| C3 | `_default_writer_census()` opens lock files with `O_RDWR | O_CREAT` (`:1020-1046`). | A read-only census can create or mutate live lock resources. |
| C4 | Persistent config is derived from `config_overlay.parent`, while production config is selected independently by `config.CONFIG_PATH` (`:715-725`, `:1125-1128`; `config.py:17-19`). | Gate 0 can validate a nonexistent canary-relative file and miss the actual production setting. |
| C5 | Model validation compares grant values only with in-code constants, and restic returns `hermetic-stub-no-restore` (`:957-980`). | Neither installed local model bytes nor the required current backup identifier is proved. |
| C6 | The network probe merely fails to connect to one reserved address before child containment is established (`:969-976`, `:1151-1158`). | Ordinary connection failure does not prove that non-loopback network is denied for the process that will call models. |
| C7 | The process census searches launcher text without excluding the current process tree (`:919-937`). | It can false-fail on itself and does not provide a reliable foreign-writer/watcher census. |
| C8 | Capsule check is conditional on an existing file, accepts the all-zero digest sentinel, and always reports `readable` true (`:1159-1168`). | Gate 0 does not require the fresh, verified before-image mandated by architecture section 6 and Gate 0 item 11. |
| C9 | Zero-adoption uses writable `ChromaStore` (`:983-1017`) even though `chroma_readonly.py` provides SQLite `mode=ro` access. | A nominally read-only probe can initialize or alter projection files. |
| C10 | Metadata is checked with path predicates/digest parsing but lacks the source descriptor's no-follow, fstat, and stable-read binding (`:1049-1064`, `:1115-1120`). | Metadata identity can change across the check without a descriptor-bound proof. |
| C11 | P2 coordinator execution imports `pytest` and `tests.incremental_jsonl_helpers.install_fakes` (`:1571-1596`); the launcher delegates to `tests/incremental_jsonl_canary_worker.py`. | The purported production canary measures fake providers through a test-owned executable path. |
| C12 | `simulate_pure_append()` writes synthetic records and `reset_p2_baseline_source()` deletes/recreates resources and rewrites the source (`:1655-1681`, `:1703-1737`). | The runner performs source mutation that P2-T0/P2-T4/P2-T5 reserve exclusively for Ryan's external benign appends. |
| C13 | `run_p2_orchestration()` auto-runs all stages, appends `110 - 61` messages regardless of the measured baseline, and resets before every fault (`:1924-1985`). | At the reviewed 68-message baseline it would target 117 messages, bypass human pause gates, and rewrite exact resources. |
| C14 | The fault path raises an in-process exception, captures its capsule after the fault, restores that torn-state image, and accepts a missing unrelated-source manifest (`:1847-1897`). | It neither proves a crash boundary nor restores the pre-fault before-image or protects unrelated records. |
| C15 | Stage guards are recreated, append binding retains the old expected digest while the delegated worker reloads the original grant, and evidence is named/marked hermetic (`:1571-1596`, `:1802-1844`, `:1900-1985`). | Whole-run ceilings, stage authority, and evidence provenance are not durable or internally coherent across subprocesses. |

The line references above are review anchors for `7360a04`; implementers must
re-locate by symbol after rebasing rather than treating line numbers as stable.

## Design decision

Two approaches were considered:

1. **Patch only the default Gate 0 probes.** This is smaller, but it leaves the
   live command routed through a test worker, fake providers, automatic source
   writes/resets, post-fault capsule capture, and non-durable call budgets.
   Rejected because Gate 0 would lead directly into an unsafe P2 path.
2. **Separate pure preflight from a staged production-owned runner.** Keep P1
   hermetic injection for tests, but make live P2 use production modules,
   explicit human append receipts, durable stage authority, real local models,
   and pre-write rollback capture. Chosen because it matches the accepted
   architecture and makes the deep safety boundary visible in one module.

The production module owns policy and orchestration. Tests may inject probes
and provider doubles through production-defined interfaces; production code
must never import `tests`, `pytest`, or a test worker.

## Corrective implementation stages

### C0 — Baseline and immutable-behavior lock

Before editing code:

1. Rebase from the then-current `origin/main` and record the exact base.
2. Capture hashes/diffs for the default-off route and unrelated adapters.
3. Run focused P1/P2 hermetic tests and the repository's required regression
   checks without any live resource.
4. Add regression tests for every C1-C15 deviation before or alongside fixes.

P1 remains hermetic and provider-free. The normal CLI and watcher remain
unchanged and default-off.

### C1 — Versioned grant and real read-only bindings

Introduce a new capability version; do not reinterpret
`p2-exact-resource-v1` under unchanged bytes. The new grant must bind:

- the actual persistent config path and exact digest or explicit absent-state
  identity, independently from the canary overlay;
- full installed model-manifest identities for every named local model, not a
  shortened in-code alias alone;
- exact full restic snapshot ID, required tag, data-root coverage, repository
  identity without credentials, and current-local-day requirement;
- expected owner UID plus existing mode, device, inode, type, and symlink
  constraints for source, metadata, and all authority-bearing resources;
- an initially absent rollback-capsule path plus the required post-capture
  receipt contract, rather than an all-zero digest treated as a verified
  capsule; and
- existing source, metadata, 11 resource roles, code revision, nonce, append
  envelope, five selectors, rollback scope, and per-stage/whole-run ceilings.

Canonical JSON and digest behavior must remain deterministic. The runtime must
fail closed on v1 for live P2 after the new version exists; v1 can remain only
as an explicitly hermetic test fixture if tests need it.

### C2 — Pure Gate 0

Split validation into a strictly read-only preflight context. Constructing it
must not call `mkdir`, `chmod`, `write_text`, `write_bytes`, `unlink`,
`rmtree`, `O_CREAT`, a writable Chroma client, or a service-start operation.
Gate 0 may write nothing, including evidence; the caller renders the returned
report to stdout until a later separately granted evidence-write stage.

The twelve checks must prove:

1. exact grant digest, version, revision, expiry, nonce availability, and
   resource-role completeness;
2. descriptor-bound source complete-prefix identity and accepted count;
3. descriptor-bound, no-follow, stable metadata identity and closed/idle
   status;
4. zero source adoption across both Chroma collections and followers using
   SQLite `mode=ro` plus ordinary read-only file access;
5. the actual grant-bound persistent config remains false/false;
6. watcher and foreign canary/index processes are absent, excluding the
   current launcher and descendants by PID ancestry, and service state is
   queried without starting/stopping/enabling/disabling it;
7. writer/source/export/processed locks are absent or provably unheld without
   creating them; inability to inspect is FAIL, not PASS;
8. exact resource identities, ownership, modes, types, and no-symlink paths;
9. installed local model manifests match the full reviewed identities without
   pulling or loading a model;
10. credentials are absent from the child allowlist and network denial is
    installed before a contained child proves loopback allowed and at least
    one non-loopback connect denied;
11. the rollback target is absent and safely creatable later, while no capsule
    is reported captured or readable yet; and
12. existing read-only backup resolver logic proves the exact grant-bound full
    snapshot ID, tag, data-root coverage, repository, and current local day;
    no backup or restore is invoked.

Reuse `restic_snapshot.resolve_snapshot(..., requested_id=...,
required_tag=..., require_current_local_day=True)` and the established backup
health semantics rather than adding a second resolver. Reuse or extend
`chroma_readonly.py`; do not instantiate `PersistentClient` or `ChromaStore`
inside Gate 0.

### C3 — Separately authorized pre-write preparation

After Gate 0 PASS and only under a later exact Ryan execution grant, a
production-owned preparation command may create the exact allowlisted canary
directories, overlay, nonce/stage receipt, evidence directory, and rollback
capsule. It must:

1. revalidate the grant and all source/config/resource bindings immediately
   before its first write;
2. acquire the governed writer and source locks through existing production
   primitives;
3. capture a source-scoped before-image of summaries, units, processed entry,
   export entries, dedupe, checkpoint, transaction, rollback, prepared state,
   and complete unrelated-source manifests;
4. fsync the capsule and parent directory, reopen it read-only, verify its
   digest and scope, then persist a signed-by-digest stage receipt; and
5. stop before model calls or coordinator writes if any proof changes.

The pre-write receipt binds the new grant digest, capsule digest, source
identity, unrelated manifest digest, and next permitted stage. A zero sentinel
can mean only "not captured yet"; it can never satisfy readiness for T3/T4/T5.

### C4 — Production-owned worker and real local provider path

Move all live P2 commands to a production module/script. It must install
service and non-loopback network denial before importing provider-capable
modules. Live mode uses the grant-bound loopback Ollama endpoint and exact
installed models. It must not import `tests`, `pytest`, fake adapters, or test
fixtures.

Keep testability through explicit production-owned interfaces for probes,
clock, subprocess launch, model invocation, and faults. Hermetic tests supply
doubles to those interfaces. The P1 worker may remain test-only, but the live
launcher must not resolve or execute a file under `tests/`.

### C5 — Staged, replayable P2 state machine

Remove or hard-refuse `p2-all` for live-capability grants. Expose only one
stage transition per invocation:

```text
gate0-pass
  -> prepared(capsule + baseline receipt)
  -> t3-initial-complete
  -> waiting-for-external-append-1
  -> t4-append-complete
  -> waiting-for-external-append-2
  -> t5-fault-1-complete
  -> ...
  -> t5-fault-5-complete
  -> t6-evidence-frozen
```

Every append stage begins only after Ryan changes the source outside the
runner. The next invocation stable-reads the source, proves immutable-prefix
continuity, accepted count `<= 110`, byte/epoch envelope, metadata continuity,
and a previously unseen append identity, then binds that identity into a
durable append receipt. Runtime code must never synthesize, append, truncate,
restore, reset, or otherwise write the source/session files.

Persist cumulative call counters before and after each provider call. Enforce
both stage and whole-run ceilings before the call; a restart must recover the
same counters and cannot reset budget. Each delegated worker consumes the
exact current stage receipt and its digest, not an in-memory grant variant.

For every selected fault:

1. capture and verify a fresh pre-fault capsule after the external append and
   before the fault worker can write;
2. start a distinct contained process group;
3. terminate at the reviewed fault point with the required crash exit, then
   prove all descendants absent;
4. measure the production read probe through apply/fault/recovery;
5. either replay the fsynced prepared output with zero transform calls or
   restore the pre-fault capsule; and
6. re-prove source identity, both collections, followers, persistent config,
   and unrelated-source manifests.

Unknown, repeated, out-of-order, or digest-mismatched transitions fail before
mutation. A failed stage never silently advances the nonce receipt.

### C6 — Honest, self-contained evidence

Separate `hermetic` and `exact-resource-live` evidence schemas. Live evidence
must not use a `p2-hermetic-evidence.json` label or claim. The append-only bundle
must include all identities and receipts needed to reconstruct the transition
chain: grant/revision; Gate 0 report; capsule and unrelated manifests; append
receipts; process/lock/fault/read timelines; stage and cumulative provider
counters; source/config/resource pre/post identities; recovery disposition;
and explicit negative proofs for providers, network, watcher, descendants, and
unrelated changes.

Evidence generation must not convert an incomplete or ambiguous observation
to PASS. Any absent proof produces `INCOMPLETE` or `FAIL` and stops.

### C7 — Verification and review stop

Cursor's implementation evidence must include:

- focused tests for C1-C15 and all twelve Gate 0 checks;
- syscall/fixture assertions that Gate 0 creates or changes no files and never
  invokes a mutating service verb or writable Chroma client;
- tests proving live mode cannot import test fakes and hermetic mode cannot
  select real providers;
- tests that the 68-message case never appends 49 messages and that no live
  code path can write a session source;
- crash-process, descendant-containment, pre-fault-capsule, unrelated-source,
  visibility, stage-order, restart, cumulative-budget, cap+1, and receipt
  tamper cases;
- unchanged default-off route and P1 regression evidence; and
- the repo's required pytest, pylint, CodeQL/security, and diff checks.

Then stop for exact-tip Kiro review. Do not prepare a replacement grant, run
Gate 0/P2, or open a PR until separately authorized.

## Acceptance criteria

- [ ] Gate 0 is mechanically side-effect-free and returns evidence only to stdout.
- [ ] Every default Gate 0 probe validates the real grant-bound resource; no stub can PASS.
- [ ] Actual config, installed model, backup, ownership, source/metadata, process, lock, network, capsule-target, and zero-adoption proofs fail closed.
- [ ] Live P2 contains no import or executable dependency on `tests`/`pytest`/fakes.
- [ ] Live code cannot write, reset, truncate, or synthesize the source/session files.
- [ ] Live P2 has no all-stages command and requires a fresh human append receipt between epochs.
- [ ] Pre-write and pre-fault capsules are captured, fsynced, reopened, digested, and scope-verified before mutation.
- [ ] Faults occur in contained child processes; descendants and serving visibility are measured.
- [ ] Stage receipts and aggregate call ceilings survive restarts and reject replay/tampering/out-of-order use.
- [ ] Unrelated-source and persistent-config identities are proved unchanged after every stage.
- [ ] Evidence distinguishes hermetic from exact-resource-live execution without overclaiming.
- [ ] P1, default-off routing, watcher behavior, other adapters, and production config are unchanged.
- [ ] No grant/digest, Gate 0, P2, production mutation, provider/network call, indexing, PR, or activation occurs during implementation/review.

## What not to build or do

- Do not change chunking, overlap, retrieval, pruning, UUID, coordinator, or
  source-authority semantics beyond what is needed to enforce the accepted
  canary contract.
- Do not add a second backup resolver or writable Chroma inspection path.
- Do not auto-create source content, auto-run all P2 stages, or infer a human
  append from elapsed time.
- Do not rotate credentials inside this slice. The previously exposed local
  provider credential must be rotated separately before any future live run;
  never copy it into code, docs, evidence, tests, or output.
- Do not modify the Claude-reviewed target or P2-T1 grant-packet branch.
- Do not issue a replacement grant/digest or operate live resources.
- Do not open a PR without Ryan's separate authorization.

## Kiro review questions

1. Does this corrective fully restore the already accepted non-mutating Gate 0
   and staged human-append P2 contract?
2. Is versioning the grant preferable to silently changing
   `p2-exact-resource-v1` semantics?
3. Is the boundary between pure Gate 0, separately authorized preparation,
   and model/write stages explicit enough to prevent authority smuggling?
4. Are pre-write/pre-fault capsule timing and durable stage/call receipts
   sufficient for crash replay and exact restore?
5. Does production ownership of live orchestration, with injectable test
   interfaces below it, eliminate the test/runtime boundary violation?
6. Are the acceptance tests sufficient to prove source immutability,
   unrelated-source isolation, network/provider containment, and honest
   serving-visibility evidence?

## Related files

| What | Path |
|---|---|
| Normative canary architecture | `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` |
| Normative canary execution plan | `docs/plans/EXECUTION-codex-jsonl-production-canary.md` |
| Arc current-state brief | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Merged canary runtime under review | `incremental_jsonl_canary.py` |
| Current launcher | `scripts/run-jsonl-production-canary.py` |
| Test-owned worker that must not serve live P2 | `tests/incremental_jsonl_canary_worker.py` |
| Existing read-only Chroma access | `chroma_readonly.py` |
| Existing exact restic resolver | `restic_snapshot.py`, `backup_workflows.py` |

## Leaving / picking up checklist

**Codex (leaving):**

- [ ] packet committed and pushed on its isolated plan branch;
- [ ] `LATEST.md`, cross-arc `STATUS.md`, and Arc Codex STATUS route to it;
- [ ] frozen review targets unchanged;
- [ ] no live operation, indexing, grant, digest, or PR; and
- [ ] exact pushed tip supplied to Kiro/Ryan.

**Kiro (reviewing):**

- [ ] verify this exact revision against merged runtime `7360a04` and the two normative plan files;
- [ ] return written PASS/FAIL with finding IDs; and
- [ ] authorize nothing operationally.

**Cursor (only after later Ryan grant):**

- [ ] start a fresh implementation branch from then-current `origin/main`;
- [ ] implement C0-C7 without touching frozen documentation targets;
- [ ] push every commit and stop for exact-tip Kiro review; and
- [ ] do not run live Gate 0/P2 or prepare a replacement grant.

## TL;DR

- [Arc Codex] Kiro's grant-packet PASS established transcription integrity, not
  runtime readiness; Ryan should not authorize digest
  `c002385ee2e72e319ddcce2ab5d024c29abbe0031b86cbb26468cb604ee8c621`
  or Gate 0.
- Merged runtime `7360a04` can mutate during nominal preflight, report stubbed
  resource checks as PASS, import test fakes for live P2, rewrite the source,
  and restore a post-fault rather than pre-fault image.
- The corrective makes Gate 0 pure, versions the grant, separates live runtime
  from hermetic tests, requires human append receipts and durable budgets, and
  captures verified rollback state before writes/faults.
- This packet is review-only; implementation and every live action remain
  separately Ryan-gated.
