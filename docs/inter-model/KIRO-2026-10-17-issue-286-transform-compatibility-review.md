# [Arc Codex #286] Kiro review — transform-compatibility design

**Reviewer:** Kiro (design review / sign-off lane; review-only, no implementation)
**Date:** 2026-10-17
**Artifact under review:** `docs/plans/DESIGN-issue-286-transform-compatibility.md`
at commit `1660c47` on `origin/docs/2026-10-17-issue-286-transform-compatibility`.
**Baseline reviewed against:** `origin/main` at `9ef4ecd` (the design's own stated base).
**Scope:** review-only. This document authorizes no implementation, migration,
grant, quarantine release, config change, or runtime promotion. It does not
touch `.worktrees/runtime-main`.

---

## Consequence first (for Ryan)

**What this is:** Codex's design to stop deploys from breaking checkpoint
continuity for admitted Codex sessions. Today the incremental transform
fingerprint folds in the R2b *implementation identity*, so any deploy that
changes a governed-or-import-reachable module invalidates every existing
checkpoint and the live route refuses with
`rebuild_required:transform_fingerprint_changed`.

**My verdict:** **PASS with conditions.** The design correctly identifies the
mechanism, proposes the right fix (bind reuse to a versioned semantic descriptor;
keep implementation identity as provenance and live-writer authority only), and
its migration/crash-safety reasoning is sound. The conditions are about making
the forgotten-epoch-bump risk enforceable rather than aspirational, and about
pinning down the net-new recovery-protocol field before implementation.

**On item 4 (the thing that actually unblocks you):** Yes — it is acceptable to
deploy the three waiting non-transform changes **during a window with no active
Codex session**, accepting refusal-only coverage loss for threads resumed later.
That is safe *today* because full rebuild is disabled, so a refusal costs nothing
but coverage, and the proposed converter is the planned recovery path. See item 4
for the two guardrails I attach.

**Who / What / When / Why / How:**
- **Who:** Codex authored the design; Kiro (me) reviews; Cursor would implement
  under a later Ryan grant; Ryan owns all runtime/migration/release grants.
- **What:** Replace `implementation_revision` in the continuity key with a
  declared `transform_contract_version` epoch + explicit semantic descriptor.
- **When:** Proposed 2026-10-17 against `9ef4ecd`; no Execute grant yet.
- **Why:** An unrelated health-check change (`cpu_tripwire.py`) was enough to
  refuse two admitted Codex sessions on 2026-10-16/17.
- **How:** If implemented, admitted Codex checkpoints become deploy-durable
  across compatible changes; a reviewed one-shot converter migrates the two
  refused legacy checkpoints with zero paid calls.

---

## Mechanism confirmed against code

I grounded the design's §2 claims against `9ef4ecd`. All confirmed:

- `compute_transform_fingerprint` (`incremental_jsonl.py:273-306`) hashes the
  semantic payload **plus** `implementation_revision` (field at line 304). The
  semantic payload *already* contains most of §3's proposed descriptor fields
  (adapter contract, chunk/overlap, prompt versions, temperatures, resolved
  models, embed dim/model, normalization/id/dedupe/envelope contracts,
  confidence threshold). So §3 is largely a *formalization + relocation* of
  existing inputs, with the real behavioral change being: drop
  `implementation_revision`, add an explicit `transform_contract_version`.
- `_continuity_reason` (`incremental_jsonl.py:456-476`) returns
  `transform_fingerprint_changed` on any fingerprint delta. With full rebuild
  disabled this is a live-route refusal — matching the evidence.
- `_prepared_key` (`:874-876`) and `_commit_generation` (generation hash at
  `:2161-2164`) both fold the full fingerprint in. So merely rewriting a
  checkpoint hash strands the prepared cache and the generation IDs — this is
  why §2/§5 are right that a comparison-only change is insufficient and the
  converter must re-key cache and preserve the generation.

**The crux — did an unrelated health check really cause the refusals? Yes.**
`current_implementation_revision()` (`chroma_write_store.py:218-222`) resolves
through `resolve_r2b_implementation_revision()` → `compute_implementation_revision()`
→ `build_authority_content_manifest()` (`authority_manifest.py:156-179`). The
manifest is a content hash over a **fail-closed dependency closure**, expanded
by `_dependency_closure()` using `ast.walk` (`authority_manifest.py:105-154`),
which captures **lazy / function-body imports**, not just top-level ones. The
closure reaches `cpu_tripwire.py` via:
`convmem.py` (route-entrypoint seed) → `from doctor import …` (lazy) →
`doctor.py:902 from cpu_tripwire import check` (lazy, inside `_check_cpu_tripwire`).

So a change confined to `cpu_tripwire.py` changes its content digest → manifest
→ `implementation_revision` → `transform_fingerprint` → refusal. The design's
problem statement and §2 mechanism are **confirmed accurate**, including the
subtlety that the identity is content-manifest-based, not raw git HEAD.

---

## §7 review items

### Item 1 — Semantic-descriptor inventory and epoch-bump discipline

**Verdict: PASS with conditions.**

The design is right that neither control alone is sufficient (a version is easy
to forget when a model/chunk size changes; a semantic-input hash misses a parser
or normalization correction whose named contract wasn't updated), and that
hashing the whole implementation is what causes the present over-invalidation.
The descriptor field list in §3 is thorough and correctly uses *resolved
effective settings* with fail-closed behavior on unresolved required inputs.
Preferring digests of actual prompt-template bytes over labels is the correct
instinct — the existing payload uses labels like `locked-summarize-prompt-v1`,
which can drift from the template without the label changing.

**Why conditions, not clean PASS:** the forgotten-bump risk is real and the
design acknowledges it ("no automated test can prove semantic equivalence of
arbitrary code"). The residual risk is **silent reuse of obsolete outputs** when
a reviewer changes transform behavior but forgets the epoch bump. The design
leans on a review obligation and a "hermetic contract-inventory check." That is
necessary but, as written, under-specified. Conditions to resolve before/within
implementation:

- **C1 — The contract-inventory check must fail closed on drift, not just
  exist.** Tie it to the *actual* prompt/template bytes and effective-settings
  sources (not labels), so that if any hashed template or settings source
  changes without a corresponding descriptor/epoch update, the test fails. This
  converts "remember to bump" into "the suite breaks until you bump or justify."
  There is prior art: `tests/test_incremental_index_contract_inventory.py`
  already guards a contract boundary; the new check should extend that pattern.
- **C2 — The check must NOT hash `incremental_jsonl.py` (or any module) wholesale
  into the runtime key.** The design states this explicitly; I am making it a
  hard condition because it is the exact failure mode being fixed. File-level or
  import-closure identity is what over-invalidates today.
- **C3 — Epoch semantics must be written as a reviewer rule in-repo** (what
  forces a bump vs. what does not — e.g. a new LLM sample does not, a prompt or
  chunk-boundary change does). The design's prose is correct; it needs to live
  next to the code as the normative checklist the §3 "Change discipline"
  paragraph describes, so reviewers apply a fixed list rather than judgment.

With C1–C3 the forgotten-bump risk is adequately controlled: automatic detection
for everything expressible as a hashed input, plus a fail-closed review gate for
genuine code-behavior changes that configuration cannot describe. Without C1
(a passive, non-failing inventory), I would downgrade this item to FAIL, because
"require a compatibility statement" with no enforcing gate reproduces the class
of human-omission bug in a quieter, more dangerous form (obsolete reuse instead
of loud refusal).

### Item 2 — Legacy migration feasibility + crash-safe publication boundary

**Verdict: PASS with conditions.**

**Preimage reconstruction feasibility:** feasible in principle and the design
handles it correctly. Because the legacy digest is a one-way SHA over the full
payload (semantic fields + `implementation_revision`), the only sound proof is
to **recompute** the legacy fingerprint from the producer's actual runtime,
effective settings, and R2b identity and require byte-equality with the stored
checkpoint digest (§5 "Preconditions and compatibility proof"). The design
correctly refuses the shortcut of "delete the field and accept the hash." It
also correctly requires including *all* producers of reused historical artifacts,
not just the latest deploy. The honest failure path —
`migration_compatibility_unproven`, leave the source untouched — is the right
default.

**One feasibility caveat Ryan should hear:** reconstruction requires the historic
producer's effective settings and R2b identity to be *recoverable*. For the two
refused sessions this is plausible because the identities are recent and
reconstructable from git history + config. But the design's own §5 admits that
if producer evidence is missing, the source stays refused and any rebuild needs
its own grant/budget. That is correct, not a defect — but it means migration is
**not guaranteed** for arbitrary legacy checkpoints, only for those whose
preimage can be exactly reproduced. The design should not be read as promising
universal migration.

**Crash-safe publication boundary — sound.** The checkpoint-as-sole-publication-
marker design is correct and matches how the code already treats the checkpoint
as processing/recovery authority (STATUS arc invariant: "checkpoint is
processing/recovery authority; Chroma and sidecars are derived projections").
The staged-namespace-then-atomic-checkpoint-swap sequence (§5 steps 1–5) gives a
clean before/after invariant: before step 4 only v1 is authoritative and a crash
leaves unreachable (garbage-collectable-later) staged copies; after step 4 only
the selected v2 namespace is authoritative. Idempotent retry keyed on the receipt
digest, refusal on unexpected checkpoint bytes/symlinks/incomplete staging, and
"do not GC old state as part of conversion" are all correct crash-safety
choices. Preserving boundary, prefix hash, record count, frontier, physical IDs,
projection fingerprint, processed lineage, and `active_generation` — and
explicitly *not* manufacturing a new generation without a real commit — is right
and consistent with `_commit_generation`'s current contract.

Conditions:

- **C4 — Quiescence gate must be enforced, not assumed.** The design requires "no
  pending transaction of any phase, no live rollback authority awaiting recovery,
  no other writer." I confirmed the code recovers a pending transaction *before*
  the checkpoint path (`run()` reads the transaction first at
  `incremental_jsonl.py:2684` and returns via `_roll_forward` at `:2701` before
  any continuity/checkpoint work). The converter must perform the same
  transaction/rollback presence check under the source + index writer locks
  immediately before publish, and refuse — not wait — if any journal exists. The
  design says this; make it a verified precondition with a test
  (§6 already lists it).
- **C5 — Staged-copy GC is explicitly deferred.** The design says "do not GC old
  state as part of conversion," which leaves orphaned staged namespaces after a
  pre-step-4 crash. That is the *safe* choice. Just confirm a later, separate
  reclamation path exists so these don't accumulate unbounded; it must key off
  receipt digests and never touch a published v2 namespace.

### Item 3 — Recovery-protocol compatibility across deploys (kept separate from transform compatibility)

**Verdict: PASS with conditions.**

The design's central correctness move here is sound and important: it keeps **two
independent questions** separate — (1) "is this paid transform reusable?"
(semantic descriptor) and (2) "can this runtime interpret and recover this
transaction safely?" (recovery protocol + current writer authority). An
incompatible recovery change must refuse **even if the semantic digest is
identical**. That is the right invariant and it prevents the fix from
accidentally widening what a new runtime will replay.

**However — this field does not exist today, so §4 is net-new design, not a
refinement.** I verified the current transaction record:

- PREPARING/APPLYING writes (`incremental_jsonl.py:2178-2196`, `:2786-2805`)
  persist `version = TRANSACTION_VERSION = 1` (a monotonic record-schema integer),
  `transaction_id`, `phase`, bootstrap binding, source/generation identity,
  boundaries, `prefix_sha256`, `session_meta_digest`, `prior_checkpoint_digest`,
  and (APPLYING) `generation`, `prepared_keys`, `rollback_authority_sha256`.
- It does **not** persist a recovery/protocol-capability field, an originating
  implementation identity, or the transform fingerprint. `_roll_forward`
  (`:2297-2460`) gates replay on phase ∈ {PREPARING, transform_failed, APPLYING}
  + rollback-authority sha256 + snapshot presence — **independent of the
  implementation identity that produced the pending transaction.**

So today a new deploy *will* replay a pending transaction authored by a different
runtime, with no protocol gate. The design proposes to add exactly the missing
gate (persist descriptor digest, recovery protocol, and originating
implementation identity for v2 transactions; recovery checks protocol support
before any provider call or write). This is a correct and desirable hardening.

Conditions:

- **C6 — The supported-recovery-protocol set must be declared explicitly.** The
  design says a non-transform deploy "may replay only when it supports that
  recovery protocol" but does not enumerate what defines protocol compatibility
  (transaction schema shape? rollback-authority format? the apply/roll-forward
  algorithm version?). Implementation must declare a concrete
  `recovery_protocol_version` with a documented compatibility matrix, and
  `_roll_forward` must refuse an unsupported value rather than best-effort replay.
- **C7 — v1 transactions have no protocol field; define their handling.** Since
  existing v1 transactions carry only `version=1` and no protocol field, the
  design must specify how a v2-capable runtime treats a pre-existing v1 pending
  transaction. The design already says the Oct-13 `recovery_unproven` APPLYING
  transaction is out of scope for the two-source conversion and stays untouched —
  good — but the general rule (v1 pending transaction → resolve under its original
  supported runtime first, never convert over a live journal) should be written
  as the normative recovery contract, consistent with C4.
- **C8 — Keep schema versions distinct, as the design states.** Fingerprint
  scheme, checkpoint schema, transaction schema, writer-gate protocol
  (`WRITER_GATE_PROTOCOL_VERSION` lives in `chroma_write_store.py`, separate), and
  the new recovery-protocol version must remain independent. A checkpoint-layout
  bump must not be read as transform incompatibility, and vice versa. The design
  asserts this; make it explicit in code constants and tests (§6 covers it).

### Item 4 — Interim deploy decision for Ryan (the unblocker)

**Verdict: PASS — deploying the three waiting non-transform changes is
acceptable, in a no-active-Codex-session window, with two guardrails.**

**The decision restated:** three finished changes are waiting on deploy — the
watcher forward-run-outcome PR, commit-cost slice 1, and #398. Each is a
*non-transform* change. The question is whether to deploy now (accepting that
Codex threads resumed later refuse with coverage loss) or hold deploys until this
compatibility design lands.

**Why deploy-now is safe today:** The cost of a refusal is currently *coverage
only*, not corruption or paid rebuild. Full rebuild is disabled, so
`transform_fingerprint_changed` becomes a terminal path-quarantine live refusal —
the session's prior checkpoint and paid work are untouched on disk, and the
proposed converter is the designed recovery path to reclaim them later with zero
paid calls. So the worst case of deploying now is: a later-resumed Codex thread
sits refused until this design lands and its source is migrated — exactly the
state the two Oct refusals are already in. Deploying adds at most *more entries to
the same recoverable backlog*, not a new class of loss.

**Why I confirmed these specific changes bump the fingerprint:** I checked the
authority manifest seeds (`authority_manifest.py:38-56`). `watch.py` is a declared
route-entrypoint seed, and `incremental_jsonl.py` is reachable from these
entrypoints. So:
- the **watcher forward-run-outcome PR** (touches `watch.py`) → manifest change →
  fingerprint bump → refusal for resumed Codex threads. Expected.
- **commit-cost slice 1** (touches `incremental_jsonl.py`, per the design's §2) →
  same. Expected.
- **#398** → bumps iff it changes a governed or import-reachable module; if it is
  fully outside the closure it will not refuse. Classify it before deploy.

This is precisely the over-invalidation this design exists to remove — so until
the design lands, these deploys *will* trip refusals, and that is the accepted,
recoverable cost.

**Guardrails (both required):**

- **G1 — Deploy only in a window with no active admitted Codex session**, as the
  prompt frames it. "No active session" means no in-flight APPLYING/PREPARING
  transaction and no session mid-append whose next index would land on the new
  runtime. This matters because of item 3: a pending-transaction *recovery* under
  a newly deployed runtime is governed by the recovery path, which today has **no
  protocol gate** (C6/C7). A refusal on a quiescent checkpoint is cheap; a
  cross-runtime replay of a live journal is a different and unreviewed risk. So
  the no-active-session window is not just about coverage — it also sidesteps the
  one genuinely unsafe interaction until the recovery-protocol field exists.
- **G2 — Record the refusal backlog as expected, not incidental.** Each session
  that refuses after these deploys becomes a converter candidate. Before/when this
  design's converter lands, these paths (plus today's two) are the migration set.
  Preserve their checkpoint + cache + refusal/hold evidence (the design's §5
  preconditions). Do not clear quarantine or `allow_full_rebuild` as a shortcut.

**Note on the clear interface (precision, not a blocker):** The design (§5) warns
that "clearing one alone may leave the path stuck" and that "the present clear
interface is broader than one refusal reason." Verified against code: there are
genuinely two independent state stores — the circuit-breaker quarantine
(`watch.py`) and per-source retry-state holds (`incremental_retry_state.py`,
`clear_incremental_retry_states_for_source`). The caution is therefore true *at
the subsystem level*. But the current CLI `convmem watch --clear-quarantine
<path>` (`convmem.py:701-708`) already clears **both** in one invocation
(`breaker.clear(resolved)` + `clear_incremental_retry_states_for_source(...)`),
so the single-reason framing slightly overstates present risk. Two real
follow-ups for implementation: (a) the `--clear-quarantine-all` help text says
only "circuit-breaker quarantine" but the handler also deletes all retry-state
files — a doc/behavior mismatch to fix; (b) there is a separate, stricter Chroma
write-guard `clear_quarantine()` (`chroma_write_guard.py`) that is a different
surface entirely — do not conflate it with the watch CLI. None of this blocks
item 4; it refines §5's operational language.

**If Ryan prefers zero backlog growth**, the alternative is to hold these three
deploys until the compatibility change lands, then deploy freely. That is also
valid — it trades "finished work waits" for "no new refusals." My recommendation:
**deploy now under G1+G2**, because the backlog is recoverable by the very
converter this arc is building, and holding three finished changes indefinitely
has its own cost (drift, merge risk, and the commit-cost burn these changes
reduce).

---

## Overall verdict

**PASS with conditions.**

The design correctly diagnoses the mechanism (confirmed against `9ef4ecd`:
`implementation_revision` folded into the fingerprint via a broad content
manifest that lazy-imports reach `cpu_tripwire.py`), proposes the correct fix
(versioned semantic descriptor + explicit epoch; implementation identity demoted
to provenance and live-writer authority), and its migration and crash-safety
reasoning is sound and consistent with the code's existing checkpoint-authority
model. It is appropriately conservative: no silent fingerprint acceptance, no
`allow_full_rebuild`, exact-source preimage proof required, converter does no
Chroma mutation and no provider calls, today's two refused sessions preserved
until separately authorized.

Conditions C1–C8 (consolidated):

1. **C1** — Contract-inventory check must **fail closed** on template/settings
   drift (hash actual bytes, not labels), extending the existing contract-
   inventory test pattern.
2. **C2** — Must not hash any module wholesale into the runtime key.
3. **C3** — Epoch-bump rules written in-repo as a normative reviewer checklist.
4. **C4** — Converter enforces quiescence (no transaction/rollback of any phase)
   under the writer locks immediately before publish; refuse, don't wait.
5. **C5** — A later, separate, receipt-keyed reclamation path for orphaned staged
   namespaces; never touches a published v2 namespace.
6. **C6** — Declare an explicit `recovery_protocol_version` + compatibility
   matrix; `_roll_forward` refuses unsupported values rather than best-effort
   replay.
7. **C7** — Define v1-pending-transaction handling under a v2-capable runtime
   (resolve under original supported runtime first; never convert over a live
   journal).
8. **C8** — Keep fingerprint/checkpoint/transaction/writer-gate/recovery versions
   as distinct constants with tests; a layout bump is not transform
   incompatibility.

These are refinements and enforceability conditions, not redesigns. The core
decision is correct and I recommend Ryan authorize Cursor implementation of the
**whole** compatibility change as one coherent unit (descriptor + provenance
split + versioned readers + converter dry-run + crash-safe publication + tests) —
the design is right that shipping only the removed hash field would be unsafe.

**Separation held:** this review does not grant implementation, migration, hold
release, config, or runtime promotion. Live migration of the two refused sessions
remains a later, separately authorized exact-source packet.

---

## Forward announcement

I finished: Kiro design review of the transform-compatibility proposal (item 1–4
verdicts + overall).
Next step:  Ryan decides (a) whether to authorize Cursor implementation under
C1–C8, and (b) the item-4 interim deploy question (my rec: deploy the three
non-transform changes now under guardrails G1+G2).
Next lane:  Ryan (decision); then Cursor (implementation) if granted.
See my work: `docs/inter-model/KIRO-2026-10-17-issue-286-transform-compatibility-review.md`
on branch `docs/2026-10-17-issue-286-transform-compatibility-review`.

**TL;DR:** [Arc Codex] PASS with conditions. Mechanism confirmed against
`9ef4ecd` — `implementation_revision` in the fingerprint, reached via a content
manifest whose lazy-import closure includes `cpu_tripwire.py`, is exactly why an
unrelated health check refused two Codex sessions. The fix (versioned semantic
descriptor + epoch; identity → provenance only) is correct; conditions C1–C8
make the forgotten-bump risk fail-closed and pin the net-new recovery-protocol
field (which does not exist today). Item 4: deploying the three waiting
non-transform changes now is acceptable in a no-active-session window (G1) with
the refusal backlog preserved for the converter (G2) — refusals cost only
recoverable coverage while full rebuild is disabled.

<!-- ref: ../plans/DESIGN-issue-286-transform-compatibility.md — the design this reviews -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex current-state brief -->
<!-- src: ../../incremental_jsonl.py, ../../chroma_write_store.py, ../../eval_corpus/r2b_v2/coverage/authority_manifest.py, ../../eval_corpus/r2b_v2/coverage/inventory.py, ../../incremental_retry_state.py, ../../convmem.py, ../../watch.py — baseline mechanism verified at 9ef4ecd -->
