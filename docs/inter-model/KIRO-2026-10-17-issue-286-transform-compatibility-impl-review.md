# [Arc Codex #286] Kiro implementation review — transform-compatibility (PR #399)

**Reviewer:** Kiro (design review / sign-off lane; review-only, no implementation)
**Date:** 2026-10-17
**Artifact under review:** PR #399, squash-merged to `main` as `9be0a4f`
("Keep paid incremental work valid across deploys that don't change transforms").
Reviewed against the merged state on `origin/main` tip; this review branched from
`origin/main` and grounds every finding at `9be0a4f` on files in the repo root.
**Baseline before the merge:** `9ef4ecd`.
**Prior design review:** `docs/inter-model/KIRO-2026-10-17-issue-286-transform-compatibility-review.md`
(PASS-with-conditions C1–C8).
**Scope:** review-only. This document authorizes no deploy, migration, grant,
quarantine release, config change, or runtime promotion. It did not touch
`.worktrees/runtime-main`.

---

## Consequence first (for Ryan)

**What this is:** the merged implementation of the fix my design review approved —
stop deploys that don't change transform behavior from invalidating paid Codex
checkpoints. Admitted Codex routes now key reuse on a versioned *semantic*
descriptor (transform contract **v2**); the R2b implementation identity is kept
only as provenance and live-writer authority. A hermetic one-shot converter
migrates the two legacy v1 checkpoints with zero provider calls.

**My verdict for DEPLOY: PASS.** Every condition C1–C8 from the design review is
met in merged code, grounded at file:line below. The real failure is fixed and
the negative controls fail as they should. I independently ran the three governing
test modules (25 tests) — all pass. The one open caveat (migrator vs. live
coordinator lock topology) is correctly judged harmless *for this hermetic slice*
because an admitted v2 runtime refuses a v1 checkpoint pre-build with
`migration_required`, and the migrator re-checks quiescence under the shared
locks before publishing. Taking the coordinator's own `SourceAdvisoryLock` is
rightly deferred to the real-data converter slice.

**Who / What / When / Why / How:**
- **Who:** Cursor implemented under Codex's design; Kiro (me) reviews the merged
  code; Ryan owns the deploy/migration grants.
- **What:** `implementation_revision` removed from the admitted-route reuse key;
  replaced by `transform_contract_version` + explicit semantic descriptor; v2
  checkpoint/transaction schemas, a recovery-protocol gate, and a hermetic
  converter added.
- **When:** merged to `main` as `9be0a4f` on 2026-10-17 (reviewed tip `f8140b1`
  pre-squash).
- **Why:** an unrelated `cpu_tripwire.py` change refused two admitted Codex
  sessions on 2026-10-16/17 by folding into the fingerprint.
- **How:** admitted Codex checkpoints are now deploy-durable across compatible
  changes; the two refused legacy checkpoints become converter candidates.

---

## Verification I performed

- Branched this review from `origin/main`; read the merged files in the repo
  root (not the `artifacts/hermetic-286-*` committed worktree copies, which are
  build artifacts, not the runtime).
- Ran `python -m pytest tests/test_incremental_transform_compatibility.py
  tests/test_incremental_index_contract_inventory.py
  tests/test_incremental_jsonl_canary_baseline.py -q` → **25 passed in 5.21s**.
- Confirmed `chroma_write_store.py` and
  `eval_corpus/r2b_v2/coverage/authority_manifest.py` are **untouched** by the
  merge (`git diff 9ef4ecd..9be0a4f --stat` empty for both) — writer authority
  and `WRITER_GATE_PROTOCOL_VERSION` unchanged.
- Confirmed both new modules parse clean.

This corroborates Claude's f8140b1 verification (CI green; real failure fixed;
cross-version migrate→continue; negative controls fail). I did not re-run full
CI; I ran the three governing modules directly.

---

## Per-condition findings (file:line on `main` / `9be0a4f`)

### C1 — contract-inventory check fails closed on template/settings drift — **MET**

`contract_inventory_sources()` (`incremental_transform_contract.py:55-70`) hashes
**actual prompt-template bytes** via `prompt_template_digests()`
(`:48-52`, `_sha(SUMMARIZE_PROMPT)` / `_sha(DISTILL_PROMPT)`), plus the effective
settings sources (rendering limits, temperatures, contracts), **not labels**.
`assert_contract_inventory_matches()` (`:84-87`) raises `AssertionError` on any
drift, pointing at the epoch-bump checklist.

Enforced by tests in `tests/test_incremental_index_contract_inventory.py`:
`test_transform_contract_inventory_is_pinned_c1_c2` (pins the literal digest) and
`test_prompt_template_drift_fails_contract_inventory_c1` (mutates
`SUMMARIZE_PROMPT`, asserts the pinned check raises). This converts "remember to
bump" into "the suite breaks until you bump" — exactly what C1 demanded, and the
reason I made C1 a hard gate.

### C2 — no module hashed wholesale into the runtime key — **MET**

The v2 descriptor (`build_transform_descriptor`,
`incremental_transform_contract.py:107-171`) is built only from resolved semantic
inputs; the digest is over the canonical descriptor body
(`:160`), never over a module's source. `compute_transform_fingerprint` in
`incremental_jsonl.py` now delegates to `compute_legacy_v1_transform_fingerprint`
(the v1 path, used only for Kiro/non-admitted routes).
`test_transform_contract_inventory_is_pinned_c1_c2` asserts
`"incremental_jsonl.py" not in str(sources)`. The over-invalidating
`implementation_revision` input is gone from the admitted-route key
(`incremental_jsonl.py:638-657`: `transform_v2` route uses the descriptor digest;
`implementation_revision` is retained only as
`coordinator_implementation_revision` provenance).

### C3 — epoch-bump rules written in-repo as a normative reviewer checklist — **MET**

`docs/plans/incremental_transform_epoch_bump_checklist.md` exists with explicit
"Requires a bump" vs "Does not require a bump" lists (prompt bytes, chunk/overlap,
model identities, embed dim/normalization, parser/selection/rendering, id/dedupe/
envelope contracts → bump; new LLM sample, bookkeeping, `implementation_revision`
drift, deploy SHA → no bump), a 5-step process, and a C5 deferral note.
`incremental_transform_contract.py:76` references the checklist by relative path in
the drift message, so a failing C1 test routes the reviewer straight to it.

### C4 — converter enforces quiescence under writer locks immediately before publish — **MET**

`assert_quiescent_for_migration()`
(`incremental_checkpoint_migration.py:95-116`) refuses on any
`transaction.json` (`migration_blocked_pending_transaction`) or `rollback.json`
(`migration_blocked_pending_rollback`), and requires a v1 checkpoint.
`publish_migration()` (`:333-410`) acquires `source_flock(cfg, path_key)` then
`index_write_flock(cfg)` (`:343-345`), and **inside both locks** calls
`_assert_publish_preconditions()` (`:118-141`) which re-runs the quiescence check
*and* re-verifies the checkpoint digest/identity/prefix/boundary are byte-for-byte
unchanged since the dry run. This is "refuse, don't wait": a journal appearing
after the dry run aborts the publish.

Grounded by the two C4 tests: `test_quiescence_blocks_migration_c4` and
`test_publish_refuses_when_transaction_appears_after_dry_run_c4` (the latter
asserts the checkpoint stays at `CHECKPOINT_VERSION_V1` after refusal).

#### MigrationPlan / MigrationPublishContext (prompt-named check)

Kiro corrective 2 (commit `f8140b1`) replaced long kwargs lists with frozen
dataclasses: `MigrationPlan` (`incremental_checkpoint_migration.py:53-67`) carries
the full preimage inputs including `legacy_producer_implementation_revision` and
`converter_revision`; `MigrationPublishContext` (`:70-76`) carries the plan, cfg,
`path_key`, `coordinator_implementation_revision`, and the optional
`dry_run_report`. The pre-publish re-checks consume these frozen objects, so the
publish path cannot drift from the dry-run inputs — a sound hardening consistent
with C4.

### C5 — later, receipt-keyed reclamation path for orphaned staged namespaces — **DEFERRED AS DESIGNED (acceptable)**

The converter does **not** GC old state: staged artifacts live under
`prepared_staged/<receipt_digest>/` (`STAGED_PREPARED_DIRNAME`,
`incremental_checkpoint_migration.py:36`, `:300-319`), and the checklist's
"Deferred (C5)" section explicitly records that orphaned
`prepared_staged/<receipt>` directories may remain until a separate
receipt-keyed reclamation path is reviewed. This matches my C5 condition, which
asked for the deferral to be explicit and the reclamation to be a separate,
receipt-keyed path that never touches a published v2 namespace. No reclamation
code ships here (correct — it was never in scope).

### C6 — explicit recovery_protocol_version + compatibility matrix; _roll_forward refuses unsupported — **MET**

`RECOVERY_PROTOCOL_VERSION = 1` and
`SUPPORTED_RECOVERY_PROTOCOL_VERSIONS = frozenset({1})`
(`incremental_transform_contract.py:19-20`); `recovery_protocol_supported()`
(`:258-261`) is the matrix. `_roll_forward` (`incremental_jsonl.py:2389-2402`)
reads the transaction version first: for v2+ transactions it refuses
`recovery_unproven: unsupported recovery protocol version` when the persisted
`recovery_protocol_version` is unsupported — **before** phase handling and any
provider call or write. Grounded by `test_recovery_protocol_refused_c6` (injects
`recovery_protocol_version: 999`, expects the refusal).

### C7 — v1-pending-transaction handling under a v2-capable runtime — **MET**

`_roll_forward` (`incremental_jsonl.py:2399-2402`): when `tx_version ==
TRANSACTION_VERSION` (v1) **and** `self.transform_v2`, it refuses
`recovery_unproven: v1 transaction requires original runtime` — i.e. a v2-capable
runtime will not replay a v1 journal; it must be resolved under its authoring
runtime first. This is the normative rule C7 asked for, and it is consistent with
C4 (never convert over a live journal). The Oct-13 `recovery_unproven` APPLYING
transaction remains out of scope and untouched.

### C8 — distinct version constants with tests — **MET**

`incremental_transform_contract.py:14-21` declares `FINGERPRINT_SCHEME`,
`TRANSFORM_CONTRACT_VERSION`, `CHECKPOINT_VERSION_V1/V2`,
`TRANSACTION_VERSION_V1/V2`, and `RECOVERY_PROTOCOL_VERSION` as independent
constants. `WRITER_GATE_PROTOCOL_VERSION` stays in `chroma_write_store.py`
(untouched by this PR). `test_version_constants_are_distinct_c8` asserts
checkpoint/transaction schemes differ and the fingerprint scheme is not a version
integer. A checkpoint-layout bump is not read as transform incompatibility, and
vice versa.

---

## Crash matrix (crash-safe publication boundary)

The checkpoint swap is the sole publication marker, published **last** and
atomically. `publish_migration` ordering (`incremental_checkpoint_migration.py`):

1. staged prepared artifacts written to `prepared_staged/<receipt>/` via
   `_atomic_json` (`:300-331`),
2. receipt file `migration_receipt_<digest>.json` written (`:388-390`),
3. pre-publish preconditions re-asserted under the locks (`:391-396`),
4. v2 checkpoint written atomically **last** (`:405-407`).

Before step 4 only the v1 checkpoint is authoritative; a crash leaves
garbage-collectable staged copies and an unreferenced receipt — the source stays
recoverable as v1. `_v2_publication_if_complete()` (`:143-162`) makes retry
idempotent: a re-run that finds a complete v2 checkpoint (receipt digest present,
receipt file present, staged root present) returns `idempotent: True` and refuses
a different receipt (`migration_already_published_different_receipt`). An
incomplete v2 (missing receipt/staged root) raises
`migration_checkpoint_incomplete_v2` rather than silently continuing.

Grounded by the parametrized `test_migration_publish_crash_fault_matrix_is_safe_
and_idempotent` across all seven `MIGRATION_PUBLISH_FAULT_POINTS`
(`incremental_checkpoint_migration.py:28-36`): after an injected fault the
checkpoint is either still v1 or a complete v2 (never a torn v2 without its
receipt), and a subsequent clean publish always reaches v2. I ran this; it passes.

**The real failure is fixed (independently reasoned + test-backed):**
`test_deploy_identity_ab_unchanged_without_provider_calls` shows an
`implementation_revision` change (`"a"*64` → `"b"*64`) leaves the v2 fingerprint
unchanged and the second run returns `unchanged` with zero counters — the exact
over-invalidation that refused the two sessions. `test_production_codex_v1_
migrates_then_continues_without_rebuild` shows v1 → `migration_required` →
dry-run + publish → `unchanged` (0 build calls) → append → `committed` reusing
history (`build_calls` populated only for the new chunks). Negative controls:
the recovery-protocol test fails an unsupported protocol, and the C1 drift test
fails a prompt change.

---

## The open caveat — migrator locks vs. a live coordinator's SourceAdvisoryLock

**Caveat restated:** `publish_migration` holds `purge_locks.source_flock` +
`index_write_flock`, but a running coordinator holds its own `SourceAdvisoryLock`
(`incremental_jsonl_isolation.py:374-406`; coordinator acquires at
`incremental_jsonl.py:2585-2588`, held across `run()`), and only takes
`source_flock`/`index_write_flock` *inside* `_commit_generation`. These are
different inodes (coordinator lock = `state_dir/<source_id>/lock.flock`;
`source_flock` = `locks/source/<sha>.lock`), so the migrator and a live
coordinator do **not** mutually exclude on the outermost lock.

**My ruling: harmless for this hermetic slice; deferral of the coordinator lock
to the real-data converter slice is correct.** Reasoning, grounded in code:

1. On an admitted Codex route (`transform_v2 = bool(codex_admitted_live)`,
   `incremental_jsonl.py:638`), a live run against a **v1 checkpoint** refuses
   **pre-build** with `migration_required` in `_unchanged_prereturn_refusal`
   (`incremental_jsonl.py:2648-2649`) — before `_build_frontier` and before any
   provider call or commit. So a v2-capable coordinator never commits over a v1
   checkpoint; it cannot race the migrator into writing a v1 commit on top of a
   just-published v2 state.
2. The migrator publishes only under `source_flock` + `index_write_flock` and
   re-asserts quiescence + checkpoint-digest equality inside those locks
   (`incremental_checkpoint_migration.py:391-396`). If a coordinator did reach
   its own commit window (which takes the same two locks,
   `incremental_jsonl.py:2241-2242`) and wrote a journal, the migrator refuses
   rather than clobbering.
3. The converter is hermetic (`require_hermetic_migration_context()` gates on
   `CONVMEM_INCREMENTAL_ROOT`, `incremental_checkpoint_migration.py:90-92`), so
   it runs in a controlled window, not against a live watcher coordinator.

The residual gap — a coordinator that acquired `SourceAdvisoryLock` *before* the
migration but had not yet refused — is closed by (1): its refusal path is
pre-build and read-only, so the worst case is a wasted read, not a torn write.
Taking the coordinator `SourceAdvisoryLock` in the converter would make the
mutual exclusion total and is the right thing for the **real-data** slice (where
a live watcher may hold it); deferring it here is a sound scoping call, not a
defect. I agree with Claude's judgment and its deferral.

**One note for the real-data slice (not a DEPLOY blocker):** when the converter
runs against live state, it must additionally acquire the coordinator's
`SourceAdvisoryLock` (same path the coordinator uses) so a concurrently-launched
watcher child cannot begin a run mid-publish. The hermetic lock set is sufficient
only because no live coordinator is present. Record this as the converter slice's
first precondition.

---

## Kiro route and writer authority unchanged — confirmed

- `transform_v2 = bool(self.codex_admitted_live)` (`incremental_jsonl.py:638`):
  non-admitted (Kiro) routes keep the v1 fingerprint, v1 checkpoint/transaction
  schema, and `generation_id_v1`. No Kiro behavioral change.
- `chroma_write_store.py` and `authority_manifest.py` untouched by the merge
  (`git diff 9ef4ecd..9be0a4f --stat` empty) → `WRITER_GATE_PROTOCOL_VERSION`,
  `current_implementation_revision()`, and the live-writer authority path are
  unchanged. `implementation_revision` is still computed and persisted as
  provenance (`coordinator_implementation_revision`); it simply no longer gates
  reuse on the admitted route.
- `validate_checkpoint` (`incremental_jsonl.py:360-382`) accepts both v1 and v2;
  for v2 it requires the descriptor fields and validates the descriptor digest,
  so a v2 reader cannot accept a malformed/forged descriptor.

---

## Overall verdict

**PASS for DEPLOY.**

The merged implementation satisfies C1–C8 as written, with each condition
grounded at file:line on `9be0a4f` and backed by hermetic tests I ran (25
passing). The real deploy-invalidation failure is fixed; cross-version migrate→
continue works with zero provider calls on the unchanged path; negative controls
(recovery protocol, C1 drift, deploy A/B with `implementation_revision` change)
fail or no-op exactly as they must. The crash matrix is crash-safe and idempotent
with the checkpoint swap as the sole, last, atomic publication marker. The Kiro
route and writer authority are untouched. The one open caveat is correctly judged
harmless for this hermetic slice and its coordinator-lock follow-up is correctly
deferred to the real-data converter slice.

**What DEPLOY does and does not cover:** this PASS is for deploying the merged
code (contract v2 wiring + hermetic converter + tests). It is **not** a grant to
run the converter against the two live refused sessions — that remains a separate,
exact-source, Ryan-authorized migration packet, and the real-data run must first
acquire the coordinator `SourceAdvisoryLock` as noted above.

**Separation held:** this review grants no deploy, migration, hold release,
config, or runtime promotion. It did not touch `.worktrees/runtime-main`.

---

## Forward announcement

I finished: Kiro implementation review of PR #399 (transform compatibility),
per-condition C1–C8 verdicts, crash matrix, Kiro-route/writer-authority check,
and a ruling on the migrator-vs-coordinator lock caveat.
Next step:  Ryan decides whether to deploy the merged code; the live migration of
the two refused sessions remains a separate exact-source packet whose real-data
converter run must take the coordinator `SourceAdvisoryLock`.
Next lane:  Ryan (deploy decision); then whoever is granted the real-data
converter slice.
See my work: `docs/inter-model/KIRO-2026-10-17-issue-286-transform-compatibility-impl-review.md`
on branch `kiro/2026-10-17-issue-286-transform-compatibility-impl-review`.

**TL;DR:** [Arc Codex #286] **DEPLOY verdict: PASS.** PR #399 (merged `9be0a4f`)
meets all of C1–C8 in merged code with file:line grounding and 25 passing
hermetic tests I ran independently: C1 contract inventory fails closed on prompt/
settings-byte drift; C2 no module hashed into the key; C3 epoch checklist in
repo; C4 converter re-checks quiescence + checkpoint equality under source+index
locks and refuses; C5 reclamation explicitly deferred; C6 `recovery_protocol_
version` gate refuses unsupported in `_roll_forward` pre-write; C7 v2 runtime
refuses a v1 journal; C8 distinct version constants with a test. Crash matrix is
crash-safe/idempotent (checkpoint swap published last, atomic). Kiro route and
`chroma_write_store`/writer authority untouched. The migrator-vs-coordinator lock
caveat is harmless here because an admitted v2 run refuses a v1 checkpoint pre-
build (`migration_required`) and the migrator re-checks quiescence under the
shared locks; taking the coordinator `SourceAdvisoryLock` is correctly deferred to
the real-data converter slice (and must be its first precondition). PASS covers
deploying the code, not running the live migration.

<!-- ref: ./KIRO-2026-10-17-issue-286-transform-compatibility-review.md — the design review (C1–C8) this implementation review checks against -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex current-state brief -->
<!-- ref: ../plans/incremental_transform_epoch_bump_checklist.md — C3 reviewer checklist shipped by the PR -->
<!-- src: ../../incremental_transform_contract.py, ../../incremental_checkpoint_migration.py, ../../incremental_jsonl.py, ../../tests/test_incremental_transform_compatibility.py, ../../tests/test_incremental_index_contract_inventory.py — merged at 9be0a4f; verdicts grounded here -->
