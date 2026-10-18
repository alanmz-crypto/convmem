# [Arc Codex #286] Kiro review — transform-compatibility implementation, DEPLOY gate

**Arc: Codex.**
**Reviewer:** Kiro (design review / sign-off lane; review-only, no implementation).
**Date:** 2026-10-18.
**Verdict for DEPLOY: PASS with conditions.**

## Artifacts under review

1. **#399 (transform compatibility)** — squash-merged to `main` as `9be0a4f`;
   reviewed tip `f8140b1` is byte-identical to `9be0a4f` (empty diff, confirmed).
   Current `main` tip is `c2ca17d`; the only commits above `9be0a4f`
   (`a00a152` #400, `c2ca17d` #401) are a watcher-journal change and a Claude
   adapter fix — both outside the #286 transform/admission closure, so this
   review of the arc code holds at the live `main` tip.
2. **Follow-up branch** `fix/2026-10-17-issue-286-v1-rebuild-when-allowed` at
   `b3dccb9` (two commits: `ee6df2b`, `b3dccb9`), PR to follow.

**Baseline grounded against:** the merged code on `main` (`9be0a4f`) and the
follow-up branch tip `b3dccb9`, both read directly. 423 arc tests run and pass
locally on `b3dccb9` (see Verification). Prior design review:
`KIRO-2026-10-17-issue-286-transform-compatibility-review.md` (C1–C8 + G1/G2).

**Scope:** review-only. This document authorizes no implementation, migration,
grant, quarantine release, config change, or runtime promotion. It does not
touch `.worktrees/runtime-main`.

---

## Consequence first (for Ryan)

**What this gates:** whether the merged transform-compatibility code (#399) plus
the small v1-rebuild follow-up are safe to carry into the runtime deploy that is
otherwise waiting. The deploy's whole point is that an unrelated code change no
longer strands admitted-Codex checkpoints.

**My verdict: PASS with conditions.** Every C1–C4 and C6–C8 condition from the
design review is present in the merged code at the file:line I cite below, and
the behaviors Claude described (v1 + rebuild → v2, unchanged → 0 calls, append
reuses, rebuild-off → `migration_required`; #399 converter dry-run + publish →
0-call continuation with working negative controls) match what the code and
tests actually do. The follow-up's choice to let `allow_full_rebuild` bypass
`migration_required` is **acceptable and correctly bounded** by the admission
chunk cap, which refuses before any paid call.

**The one thing to carry out of this review (not a blocker):** the live config
currently has `allow_full_rebuild = true` **and** `live_sources = []`. The empty
`live_sources` is what makes the forgotten-flag risk near-zero *today* — nothing
is routed to the incremental coordinator, so no rebuild can fire. The risk
becomes real the moment a source is added to `live_sources` while the flag is
still on and billing has resumed. My conditions D1–D3 make that transition safe
rather than silent.

**Who / What / When / Why / How:**
- **Who:** Cursor implemented #399 and the follow-up (co-authored commits);
  Kiro (me) reviews; Ryan owns the deploy, config revert, and any live grant.
- **What:** #399 replaced `implementation_revision` in the continuity key with a
  versioned semantic descriptor and added a hermetic v1→v2 converter; the
  follow-up lets `allow_full_rebuild=true` rebuild admitted v1 checkpoints
  instead of refusing, and fixes a `frontier_violation` on multi-chunk rebuilds.
- **When:** #399 on `main` since `9be0a4f`; follow-up on branch at `b3dccb9`,
  2026-10-18.
- **Why:** to unblock the deploy without stranding paid Codex work, and to let
  production roll a v1 checkpoint forward during the temporary free-provider
  window without running the converter by hand.
- **How:** descriptor digest drives reuse; identity is provenance only; the
  converter migrates on demand; `allow_full_rebuild` is the escape hatch while
  providers are free.


---

## Conditions C1–C4, C6–C8 ruled on `main` (file:line)

I confirmed each design-review condition against the merged code. All are
present. (C5 — staged-copy GC — was explicitly deferred by the design and is
restated as deferred in the epoch checklist; nothing to rule on at deploy.)

### C1 — contract-inventory check fails closed on template/settings drift

**PASS.** The runtime semantic inputs are hashed as *bytes/values*, not module
text, in `contract_inventory_sources()` and digested by
`contract_inventory_digest()` (`incremental_transform_contract.py:52-78`). The
test pins the digest and asserts fail-closed drift:
`tests/test_incremental_index_contract_inventory.py:160-199` —
`test_transform_contract_inventory_is_pinned_c1_c2` pins
`9f40605f…f2b3` and `test_prompt_template_drift_fails_contract_inventory_c1`
mutates `SUMMARIZE_PROMPT` and asserts `assert_contract_inventory_matches`
raises, with the error message pointing at the epoch-bump checklist
(`incremental_transform_contract.py:84-96`). This is the fail-closed behavior C1
required: a prompt/settings change without a descriptor/epoch update breaks the
suite.

### C2 — no module hashed wholesale into the runtime key

**PASS.** `contract_inventory_sources()` contains only scheme/version strings,
prompt-template SHA-256s, and named contract labels — no module source. The test
explicitly asserts `"incremental_jsonl.py" not in str(sources)`
(`tests/test_incremental_index_contract_inventory.py:171`). The v2 descriptor
(`build_transform_descriptor`, `incremental_transform_contract.py:112-172`)
likewise hashes only semantic fields. The over-invalidating
`implementation_revision` is gone from the v2 continuity key: a v2 coordinator's
`transform_fingerprint` is `self.transform_descriptor.digest`
(`incremental_jsonl.py:650`), independent of `implementation_revision`. Proven
behaviorally by `test_deploy_identity_ab_unchanged_without_provider_calls`
(`tests/test_incremental_transform_compatibility.py:230-287`): swapping the
implementation revision from all-`a` to all-`b` leaves the fingerprint equal and
the second run returns `unchanged` with `counters.total == 0`.

### C3 — epoch-bump rules written in-repo as a normative checklist

**PASS.** `docs/plans/incremental_transform_epoch_bump_checklist.md` exists with
a "Requires bump / Does not require a bump / Process" structure, is referenced
by constant `EPOCH_BUMP_CHECKLIST_REL` and surfaced in the drift error message
(`incremental_transform_contract.py:81-96`), and the C1 drift test asserts that
message names the checklist file.

### C4 — converter enforces quiescence under the writer locks; refuse, don't wait

**PASS.** `assert_quiescent_for_migration`
(`incremental_checkpoint_migration.py:92-108`) refuses on any
`transaction.json` (`migration_blocked_pending_transaction`) or `rollback.json`
(`migration_blocked_pending_rollback`) and requires a v1 checkpoint. It is
re-checked *inside* the publish critical section under both locks immediately
before the checkpoint swap: `publish_migration` opens
`source_flock` + `index_write_flock` (`incremental_checkpoint_migration.py:303-305`),
then `_assert_publish_preconditions` re-runs the quiescence check and re-reads
the checkpoint digest/identity/prefix/boundary
(`incremental_checkpoint_migration.py:114-137`), raising
`migration_checkpoint_changed` etc. on any drift. This closes the
dry-run→publish TOCTOU. Tests:
`test_quiescence_blocks_migration_c4`,
`test_publish_refuses_when_transaction_appears_after_dry_run_c4`
(`tests/test_incremental_transform_compatibility.py:401-451`) — the second
proves a transaction appearing after the dry-run forces refusal and leaves the
checkpoint at v1.

### C6 — explicit `recovery_protocol_version`; `_roll_forward` refuses unsupported

**PASS.** `RECOVERY_PROTOCOL_VERSION = 1` and
`SUPPORTED_RECOVERY_PROTOCOL_VERSIONS = frozenset({1})` with
`recovery_protocol_supported()` (`incremental_transform_contract.py:20-21,
254-257`). `_roll_forward` refuses an unsupported protocol *before* any replay:
`incremental_jsonl.py:2389-2398` — a v2 transaction (`version >=
TRANSACTION_VERSION_V2`) with an unsupported `recovery_protocol_version` raises
`recovery_unproven: unsupported recovery protocol version`. v2 commits persist
the field (`incremental_jsonl.py:2277-2278`, `:1348-1349`). Test:
`test_recovery_protocol_refused_c6`
(`tests/test_incremental_transform_compatibility.py:453-473`) injects protocol
`999` and asserts the raise.

### C7 — v1 pending transaction under a v2-capable runtime

**PASS.** `_roll_forward` refuses a v1 transaction when the current runtime is v2
rather than best-effort replaying it:
`incremental_jsonl.py:2399-2403` — `tx_version == TRANSACTION_VERSION and
self.transform_v2` raises `recovery_unproven: v1 transaction requires original
runtime`. This matches the design's rule that a pre-existing v1 journal is
resolved under its authoring runtime, never converted over a live journal.

### C8 — distinct version constants, used distinctly

**PASS.** `FINGERPRINT_SCHEME="incremental-transform-v2"`,
`CHECKPOINT_VERSION_V1=1`, `CHECKPOINT_VERSION_V2=2`, `TRANSACTION_VERSION_V1=1`,
`TRANSACTION_VERSION_V2=2`, `RECOVERY_PROTOCOL_VERSION=1`
(`incremental_transform_contract.py:14-21`) are separate constants.
`validate_checkpoint` accepts both checkpoint versions and only demands the v2
descriptor fields when `version == CHECKPOINT_VERSION_V2`
(`incremental_jsonl.py:364-379`). The generation scheme is versioned separately
(`GENERATION_SCHEME_V1/V2`). Test: `test_version_constants_are_distinct_c8`
(`tests/test_incremental_transform_compatibility.py:154-162`).

---

## The converter-lock caveat — ruled harmless, deferral accepted

**Claude's framing:** `publish_migration` holds `source_flock` + the C1
contract-inventory relationship, but **not** the coordinator's
`SourceAdvisoryLock`; Claude judged it harmless and deferred. I agree, and here
is the exact lock topology I verified so the deferral is grounded, not assumed.

There are two distinct source locks in the normal commit path:

1. **`SourceAdvisoryLock`** — the coordinator's own per-source flock on
   `state_dir/<source_id>/lock` (`incremental_jsonl.py:614-619, 665`; acquired
   via `_acquire_source_lock`, `incremental_jsonl.py:2583-2588`; class at
   `incremental_jsonl_isolation.py:374-404`).
2. **`source_flock(cfg, path_key)`** — a global purge/source flock on
   `source_lock_dir(cfg)/<path_hash>.lock` (`purge_locks.py:166-178`,
   `source_lock_path` at `:134-136`), taken *together with* `index_write_flock`
   around the checkpoint-mutating critical section
   (`incremental_jsonl.py:2241-2242`).

`publish_migration` takes **the same `source_flock` + `index_write_flock` on the
same `cfg`/`path_key`** (`incremental_checkpoint_migration.py:303-305`). So the
one window that matters — mutating the checkpoint — is **mutually exclusive**
between a live commit and the converter via `source_flock`, even though the
converter does not take the coordinator's `SourceAdvisoryLock`. The missing lock
is the coordinator's *own* intra-run advisory lock, which guards a live
coordinator against a second live coordinator on the same source; it does not
guard the checkpoint file against the converter, because `source_flock` already
does.

Two further facts make the gap unreachable in practice:

- **Migration is hermetic-only.** `publish_migration` and `dry_run_migration`
  call `require_hermetic_migration_context()`, which refuses unless
  `CONVMEM_INCREMENTAL_ROOT` is set (`incremental_checkpoint_migration.py:85-87`).
  The converter cannot run in the production route at all; it runs in the
  isolated bootstrap/migration context, so a live production coordinator and the
  converter are not racing on the same checkpoint in the first place.
- **C4 re-validation under the locks** re-reads the checkpoint digest and
  refuses on any change between dry-run and publish
  (`incremental_checkpoint_migration.py:114-137`). Even if a writer slipped in,
  the publish refuses rather than corrupts.

**Ruling:** harmless; deferral accepted. The converter's lock set is sufficient
for the only shared mutation (the checkpoint), and the hermetic gate plus the
C4 re-check remove the residual race. If a later slice ever lets the converter
run in-process alongside a live coordinator (it must not, per the hermetic
gate), it should additionally take `SourceAdvisoryLock` — I note this only as a
guardrail on a future change, not a deploy blocker.

---

## Letting `allow_full_rebuild` bypass `migration_required` — acceptable, bounded

**What the follow-up changes.** On `main`, an admitted-Codex v1 checkpoint
returns `migration_required` unconditionally
(`incremental_jsonl.py:2645-2649`): the check fires before the
`allow_full_rebuild` branch at `:2686`. The follow-up `ee6df2b` adds
`and not self.settings.allow_full_rebuild` to that guard, so with the flag on a
v1 checkpoint falls through to the normal full-rebuild path
(`transform_fingerprint_changed` → `full_rebuild_fallback`) and re-transforms to
a v2 checkpoint, instead of refusing. `b3dccb9` then fixes the admission math so
a *multi-chunk* rebuild is admitted: `_codex_admission_prior_record_count`
(`incremental_jsonl.py:1200-1212`) resets `prior_count` to 0 when
`allow_full_rebuild and continuity`, so the planned full-history chunk starts are
a subset of `allowed` and no longer trip `frontier_violation`.

**Is the bypass acceptable?** Yes, for three reasons:

1. **It is the same path a fingerprint change already takes.** A full rebuild on
   `transform_fingerprint_changed` was already allowed under `allow_full_rebuild`
   on `main`. The follow-up merely routes a v1 checkpoint through that same,
   already-reviewed `full_rebuild_fallback` path instead of a hard
   `migration_required`. It does not invent a new mutation path; the rebuilt
   checkpoint is a normal v2 commit carrying the descriptor
   (`incremental_jsonl.py:2294, 2302`; test asserts
   `v2_checkpoint.get("transform_descriptor")`).
2. **The cost is bounded before any paid call.** The admission guard runs and can
   refuse with `transform_chunk_cap` *before* the PREPARING transaction and
   before `_build_frontier` (where provider calls happen):
   `incremental_jsonl.py:2878-2892` returns `self._refusal(guard_code, …)` ahead
   of any transform. With the live `max_transform_chunks_per_run = 20`, a rebuild
   whose frontier exceeds 20 chunks refuses with zero paid calls. So the escape
   hatch cannot silently burn an unbounded full-history rebuild — it is capped
   per run and terminal above the cap.
3. **It is correct and tested.** `b3dccb9` adds
   `test_legacy_v1_checkpoint_rebuilds_when_full_rebuild_allowed` (multi-chunk
   source; v1 → `full_rebuild_fallback`/`transform_fingerprint_changed` → v2;
   then `unchanged` with 0 calls and no build; then append → committed reuse),
   `test_multi_chunk_fingerprint_rebuild_allowed_respects_frontier`, and
   `test_full_rebuild_chunk_cap_refuses_multi_chunk_v1` (confirms the cap still
   refuses). The migration-off path is still covered by
   `test_legacy_v1_checkpoint_refuses_migration_required` on `main`
   (`tests/test_incremental_transform_compatibility.py:289-331`).

**Caveat worth stating plainly:** the bypass makes `allow_full_rebuild` a *paid*
operation when a v1 checkpoint is encountered with providers billing — it
re-transforms history (up to the cap per run) rather than reusing it via the
free converter. During the stated free-provider window the marginal cost is
zero. The converter remains the zero-paid-call recovery path and is unaffected;
the bypass is an operational shortcut, not a replacement for it.

---

## The risk a forgotten flag later causes paid full rebuilds

**The scenario:** billing resumes, `allow_full_rebuild = true` is left in the
live config, a v1 Codex checkpoint is encountered, and instead of refusing with
`migration_required` the runtime silently re-transforms history for real money.

**Why it is small today (but not nil):** the live config has
`live_sources = []` (`~/.config/convmem/config.toml`, `[index.incremental_jsonl]`).
With no routed sources, the incremental coordinator does not run against any
production source, so no rebuild — paid or free — can fire regardless of the
flag. The flag is armed but has nothing to shoot. The exposure appears only when
a source is added to `live_sources`.

**Why the blast radius is capped even then:** `max_transform_chunks_per_run = 20`
makes any single rebuild run refuse (`transform_chunk_cap`, zero paid calls)
above 20 frontier chunks. The uncapped worst case is therefore "up to ~20
chunks' worth of summarize/distill/embed calls per encountered v1 source per
run," not an unbounded full-corpus rebuild. That is a real but bounded cost.

**Residual risk I am flagging (not a deploy blocker):** nothing in the code ties
`allow_full_rebuild` to provider-billing state. The revert is a human action
("revert when billing resumes," per the prompt). A forgotten revert plus a new
`live_sources` entry is the only path to surprise paid rebuilds. My conditions
D1–D3 below convert that from a silent risk into an explicit, owned step. I am
**not** requiring a code change before deploy, because today's `live_sources = []`
removes the live exposure and the chunk cap bounds the worst case.

---

## Deploy-gate conditions (D1–D3) — operational, Ryan-owned

These attach to the deploy; they are not implementation redesigns.

- **D1 — Treat the free-provider window as the only sanctioned time for the
  bypass.** `allow_full_rebuild = true` is acceptable *while providers are free*.
  The revert to `false` must happen as part of the "billing resumes" change, in
  the same edit that re-enables paid providers — not as a later cleanup. Record
  the revert as a required step of resuming billing.
- **D2 — Do not add any source to `live_sources` while `allow_full_rebuild =
  true` and providers are billing.** The near-zero risk today rests on
  `live_sources = []`. If a Codex source is routed live during a billing period,
  flip `allow_full_rebuild` to `false` first (so a v1 checkpoint refuses with
  `migration_required` and is migrated by the free converter), then route the
  source. This keeps the paid-rebuild path unreachable in production.
- **D3 — Keep `max_transform_chunks_per_run` as the cost ceiling and review it
  before any live routing.** The cap is the backstop that bounds a forgotten-flag
  rebuild to a terminal per-run refusal above the limit. Do not raise it as part
  of enabling a live source without separately accounting for the paid-call
  ceiling it implies.

None of D1–D3 blocks the deploy of the merged #399 code or the follow-up; they
govern the *config state* carried alongside it and the later live-routing step.

---

## Verification

- **Reviewed-tip identity:** `git diff f8140b1 9be0a4f` is empty — the reviewed
  tip is exactly what landed on `main`.
- **Main-tip relevance:** commits above `9be0a4f` on `main` (`a00a152` #400,
  `c2ca17d` #401) touch the watcher journal and the Claude adapter only; neither
  is in the #286 transform/admission closure, so the arc review holds at the live
  `main` tip.
- **Tests on the follow-up tip `b3dccb9`:** I ran the arc-focused suite in a
  throwaway worktree (Python 3.13, pytest 9.1.1):
  `test_incremental_*`, `test_codex_*`, `test_kiro_session_jsonl`,
  `test_claude_session_jsonl`, `test_copilot_session_jsonl`,
  `test_incremental_transform_compatibility`,
  `test_incremental_index_contract_inventory` — **423 passed**. The C1/C4/C6/C8
  and v1-rebuild/frontier/chunk-cap tests cited above are in that set.
  I did not reproduce the full "497 tests" figure from the prompt: that is
  Claude's broader selection (adds the slower canary-operations/grant/serving/P2
  and scratch-Chroma modules I excluded as environment-dependent, plus
  Python-3.12 CI collection). The arc-behavioral evidence I verified is
  sufficient for the DEPLOY gate; the full 3.12 suite remains CI's to confirm.
- **Lint:** `pylint -E` on `incremental_transform_contract.py` and
  `incremental_checkpoint_migration.py` → 10.00/10, no errors.
- **Live config state confirmed:** `allow_full_rebuild = true`, `enabled = true`,
  `live_sources = []`, `max_transform_chunks_per_run = 20`,
  `admitted_after = 2026-10-12T04:04:00Z`.
- **Not run / not verified:** the live deploy itself, any migration of real
  checkpoints, Claude's cross-version probes against the live runtime (`633f1d1`)
  — I reviewed the code and tests, not the live-runtime probe runs. The
  cross-collection two-write atomicity seam remains the arc's known, separately
  tracked open item and is not re-adjudicated here.

---

## Overall verdict — DEPLOY: PASS with conditions

The merged transform-compatibility code (#399 at `9be0a4f` = reviewed `f8140b1`)
implements every design condition I set — C1 fail-closed inventory, C2 no module
hashing, C3 in-repo epoch checklist, C4 quiescence under locks with a
re-validated publish, C6 explicit recovery-protocol refusal, C7 v1-journal
refusal under a v2 runtime, C8 distinct version constants — each confirmed at the
file:line cited. The follow-up (`b3dccb9`) correctly and safely lets
`allow_full_rebuild` roll a v1 checkpoint forward through the already-reviewed
full-rebuild path, with the frontier fix and the chunk-cap backstop that refuses
before any paid call. The converter-lock caveat is harmless because the converter
shares the one lock that matters (`source_flock`), is hermetic-only, and
re-validates under the locks before publishing; Claude's deferral is accepted.

The only live exposure is operational, not code: `allow_full_rebuild = true` with
providers billing *and* a routed `live_sources` entry would allow bounded paid
rebuilds. Today's `live_sources = []` removes that exposure; conditions D1–D3
keep it removed across the billing transition. On that basis I pass the deploy.

**Separation held:** this review grants no implementation, migration, config
change, hold release, or runtime promotion. The config revert (D1), the
live-routing ordering (D2), and the cap review (D3) are Ryan-owned.

---

## Forward announcement

I finished: Kiro DEPLOY-gate review of #286 transform-compatibility (#399 on
`main`) and the v1-rebuild follow-up (`b3dccb9`).
Next step:  Ryan decides the deploy and carries D1–D3 across the billing
transition; the follow-up branch's PR can proceed.
Next lane:  Ryan (deploy + config revert ownership); Cursor (open the follow-up
PR if desired).
See my work:
`docs/inter-model/KIRO-2026-10-18-issue-286-deploy-gate-review.md` on branch
`kiro/2026-10-18-issue-286-deploy-gate-review`.

**TL;DR:** [Arc Codex] **DEPLOY: PASS with conditions.** C1–C4 and C6–C8 are all
present in the merged #399 code at the file:line cited (reviewed tip `f8140b1` ==
`main` `9be0a4f`); the follow-up `b3dccb9` safely lets `allow_full_rebuild` roll
a v1 checkpoint through the existing full-rebuild path, bounded by the
`max_transform_chunks_per_run=20` cap that refuses before any paid call. The
converter-lock caveat is harmless — the converter shares `source_flock` (the only
lock guarding the checkpoint), is hermetic-only, and re-validates under the locks
before publish — so Claude's deferral is accepted. Letting `allow_full_rebuild`
bypass `migration_required` is acceptable. The forgotten-flag paid-rebuild risk
is near-zero today because live `live_sources = []`; conditions D1–D3 (revert the
flag when billing resumes; don't route a live source while the flag is on and
billing; keep the chunk cap as the ceiling) keep it that way. 423 arc tests pass
on the follow-up tip; the full 3.12 suite remains CI's to confirm.

<!-- ref: ./KIRO-2026-10-17-issue-286-transform-compatibility-review.md — the design review whose C1-C8/G1-G2 this gates against -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex current-state brief -->
<!-- ref: ../plans/incremental_transform_epoch_bump_checklist.md — C3 normative epoch-bump checklist -->
<!-- src: ../../incremental_jsonl.py, ../../incremental_transform_contract.py, ../../incremental_checkpoint_migration.py, ../../purge_locks.py, ../../incremental_jsonl_isolation.py, ../../tests/test_incremental_transform_compatibility.py, ../../tests/test_incremental_index_contract_inventory.py — verified at main 9be0a4f and follow-up b3dccb9 -->

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Codex | The #286 arc making Kiro/Codex JSONL ingestion incremental and crash-replayable; see `STATUS-codex-jsonl-production-integration.md`. |
| C1–C8 | The eight conditions Kiro attached to the transform-compatibility design in the 2026-10-17 review. |
| D1–D3 | The three deploy-gate (config/operational) conditions this review attaches. |
| G1/G2 | The two interim-deploy guardrails from the prior design review (no-active-session window; preserve refusal backlog). |
| transform fingerprint | Hash that keys reuse of paid transform work; in v2 it is the semantic descriptor digest, no longer the implementation revision. |
| transform descriptor | The versioned set of semantic inputs (prompts, chunk size, models, dims, contracts) whose digest is the v2 fingerprint. |
| `implementation_revision` | R2b content-manifest hash of the code closure; folded into the v1 fingerprint (the over-invalidation cause), now provenance/live-writer-authority only. |
| continuity reason | `_continuity_reason` output describing why a checkpoint can't be reused as-is (e.g. `transform_fingerprint_changed`, `initial_full`). |
| `migration_required` | Refusal returned for an admitted-Codex v1 checkpoint, directing it to the converter (unless `allow_full_rebuild` bypasses it). |
| `allow_full_rebuild` | Config flag that lets a non-reusable checkpoint be re-transformed (paid when providers bill) instead of refusing. |
| full_rebuild_fallback | Run mode where history is re-transformed because continuity could not be preserved. |
| `frontier_violation` / `transform_chunk_cap` | Codex admission refusals: planned chunk starts outside the allowed frontier / run exceeds `max_transform_chunks_per_run`. |
| converter | Hermetic-only v1→v2 checkpoint/cache migration in `incremental_checkpoint_migration.py`; no provider calls, no Chroma mutation. |
| `source_flock` / `index_write_flock` | Global purge/source and index-write flocks from `purge_locks.py` taken around the checkpoint-mutating critical section. |
| `SourceAdvisoryLock` | The coordinator's own per-source state-dir flock (distinct from `source_flock`). |
| recovery_protocol_version | Versioned gate (`=1`) that `_roll_forward` checks before replaying a v2 transaction; unsupported values refuse. |
| hermetic | Tokenized, network-denied, provider-free test/migration boundary gated by `CONVMEM_INCREMENTAL_ROOT`. |
| `live_sources` | Config list of sources actually routed to the incremental coordinator; currently empty. |
| Track A | Indexing this session's chat transcript into convmem at handoff. |
