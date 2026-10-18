# [Arc Codex #286] Kiro deploy-gate review — PR #402 (v1 full-rebuild when allowed)

**Reviewer:** Kiro (design review / sign-off lane; review-only, no implementation)
**Date:** 2026-10-18
**Artifact under review:** PR #402, branch `fix/2026-10-17-issue-286-v1-rebuild-when-allowed`,
tip `b3dccb9` ("fix: admit full Codex rebuilds across multi-chunk frontiers").
**Base of the branch:** `a00a152` (#400, which includes #399 `9be0a4f`).
**Deploy target under gate:** `main` (`c2ca17d`, #401) **+ #402**.
**Prior reviews this builds on:**
- `docs/inter-model/KIRO-2026-10-17-issue-286-transform-compatibility-review.md` (design, C1–C8)
- `docs/inter-model/KIRO-2026-10-17-issue-286-transform-compatibility-impl-review.md` (PR #399 DEPLOY PASS)
**Scope:** review-only. This document authorizes no deploy, migration, grant, quarantine
release, config change, or runtime promotion. It did not touch `.worktrees/runtime-main`.

---

## Consequence first (for Ryan)

**What this is:** the companion fix that must ship *with* #399. #399 made admitted Codex
checkpoints deploy-durable and added the v1→v2 migration path, but it left a live-route
hole: when `allow_full_rebuild` is on, a v1 checkpoint still refused with
`migration_required`, and a *multi-chunk* v1 history that reached the full-rebuild path was
rejected by the frontier-admission guard with `frontier_violation`. Net effect without #402:
~40 live v1 checkpoints cannot migrate or rebuild, and Codex indexing stalls on them.

**My verdict for DEPLOY of `main` + #402: PASS with conditions.** The two code changes are
correct, minimal, confined to the admitted-Codex route, and backed by tests I ran
independently (33 governing + 81 focused, all green). The conditions are **not** blockers on
the code — they are operational guardrails Ryan must hold at deploy/activation time, because
this PR deliberately turns a cheap refusal into a *paid rebuild* when the flag is on. They
restate the migration precondition my #399 review relied on (which this PR changes) and pin
the billing risk.

**Who / What / When / Why / How:**
- **Who:** Claude authored/evidenced #402 under Codex's arc; Cursor-style implementation on
  `incremental_jsonl.py`; Kiro (me) reviews; Ryan owns deploy/flag/billing grants.
- **What:** (1) `_unchanged_prereturn_refusal` returns `migration_required` for a v1
  checkpoint **only when `allow_full_rebuild` is false**; when true the v1 checkpoint takes
  the existing full-rebuild path to v2. (2) `_codex_admission_prior_record_count` makes a
  full rebuild under `allow_full_rebuild` compute admission as `initial_full`
  (`prior_count = 0`), so multi-chunk rebuilds stop hitting `frontier_violation`.
- **When:** branch tip `b3dccb9`, 2026-10-17; proposed to deploy alongside #399.
- **Why:** without it ~40 live v1 checkpoints refuse `migration_required`/`frontier_violation`
  and Codex indexing halts.
- **How:** with the flag on, a v1 checkpoint rebuilds to v2 in place; `max_transform_chunks_
  per_run` still caps the work (`transform_chunk_cap`); with the flag off, behavior is
  byte-identical to #399 (`migration_required`).

---

## The change, grounded at `b3dccb9`

Two edits to `incremental_jsonl.py`, both inside the `codex_admitted_live` route; the Kiro
and non-admitted routes are untouched.

### (1) `_unchanged_prereturn_refusal` (~:2656)

```python
if self.codex_admitted_live:
    if (
        checkpoint is not None
        and int(checkpoint.get("version") or 0) == CHECKPOINT_VERSION
        and not self.settings.allow_full_rebuild
    ):
        return "migration_required"
```

`CHECKPOINT_VERSION = 1` (`incremental_jsonl.py:103`) is the legacy/v1 schema
(`CHECKPOINT_VERSION_V1 = 1` in `incremental_transform_contract.py:16`). Before #402 this
returned `migration_required` for any v1 checkpoint on the admitted route unconditionally.
After #402 the refusal is suppressed when `allow_full_rebuild` is true, so control falls
through. The very next guard in the same function already handled the fall-through correctly
for #399:

```python
continuity = _continuity_reason(checkpoint, snapshot, self.transform_fingerprint)
if continuity and continuity != "initial_full" and not self.settings.allow_full_rebuild:
    return f"rebuild_required:{continuity}"
return None
```

So with the flag on, both the `migration_required` gate and the `rebuild_required:continuity`
gate are skipped, the function returns `None`, and the run proceeds to the full-rebuild path
(`mode="full_rebuild_fallback"`, `fallback_reason="transform_fingerprint_changed"`). This is
internally consistent — the flag relaxes both quiescent-refusal gates together, not one in
isolation.

### (2) `_codex_admission_prior_record_count` (~:1200)

```python
def _codex_admission_prior_record_count(self, checkpoint, continuity) -> int:
    if checkpoint is None:
        return 0
    prior_count = int(checkpoint.get("record_count") or 0)
    if continuity == "initial_full":
        return 0
    if self.settings.allow_full_rebuild and continuity:
        return 0
    return prior_count
```

This feeds `_codex_admission_guard_code`, which computes `allowed =
_allowed_transform_starts(messages, prior_count)` and `planned =
_planned_transform_starts(...)`, then refuses `frontier_violation` if `planned` is not a
subset of `allowed`. In `_allowed_transform_starts` (`:1085`), `prior_count <= 0` admits
**every** chunk start; `prior_count > 0` admits only starts at/after
`frontier_start(prior_count, ...)`. 

**Why the old code was broken for multi-chunk v1 rebuilds:** a v1 checkpoint with
`record_count > 0` (e.g. a 2-chunk history) gave `prior_count > 0`, so `allowed` excluded
chunk 0. But a full rebuild (fingerprint changed) *plans* all chunks, including chunk 0 —
`planned` was not a subset of `allowed` → `frontier_violation`. The fix: when
`allow_full_rebuild` is on **and** there is a continuity reason (i.e. this is a rebuild, not a
pure append), treat admission as initial ingest (`prior_count = 0`) so all chunk starts are
allowed and the rebuild is admitted. `max_transform_chunks_per_run` is unchanged, so an
over-cap rebuild still refuses `transform_chunk_cap`.

The guard early-returns `None` when `not self.codex_admitted_live`, so this helper has no
effect on the Kiro or any non-admitted route.

---

## Verification I performed

- Fetched the branch; confirmed tip `b3dccb9` and that it branches from `a00a152` (#400),
  which has `9be0a4f` (#399) as an ancestor. Confirmed `main` is `c2ca17d` (#401) and #399 is
  on `main`. #401 touches only `adapters/claude_session_jsonl.py` + its test — **no overlap**
  with #402's `incremental_jsonl.py`, so `main` + #402 is a clean combination.
- Created a detached scratch worktree at `b3dccb9` (removed after; `.worktrees/runtime-main`
  never touched) and ran:
  - `test_incremental_transform_compatibility.py`,
    `test_incremental_jsonl_codex_rollout_route.py`,
    `test_incremental_index_contract_inventory.py`,
    `test_incremental_jsonl_canary_baseline.py` → **33 passed**.
  - The five PR-specific behavioral tests by name → **5 passed**.
  - A focused non-subprocess codex/transform surface (admission, admission-predicate-extra,
    rollout route, route corrective, config, contract inventory, codex incremental route,
    codex rollout jsonl, transform compatibility) → **81 passed**.
- I did not re-run full CI. Two unrelated modules (`test_governed_recovery_matrix_admitted.py`,
  `test_safe_harbor_*`, `test_zz_codex_audit*`) abort collection with `SystemExit(5)` from
  `require_t3_bootstrap()` — that is a Safe Harbor T3 environment gate, not a #402 regression.
  The "497 tests pass" figure is Claude's full-suite evidence; my targeted runs corroborate
  the behavioral surface #402 changes.

**New tests reviewed (all map to a claim):**
- `test_legacy_v1_checkpoint_refuses_migration_required` — **retained**, now also asserts 0
  counters and no build calls with the flag off (negative control: flag-off path unchanged).
- `test_legacy_v1_checkpoint_rebuilds_when_full_rebuild_allowed` — v1 commit → flag-on second
  run → `full_rebuild_fallback`/`committed`, checkpoint becomes v2 → third run `unchanged`
  with 0 counters and no builds → append → `committed` reusing history. This is the exact
  "4 calls, then 0, then append reuses" evidence.
- `test_multi_chunk_fingerprint_rebuild_allowed_respects_frontier` — stale fingerprint forces
  a multi-chunk rebuild that now commits instead of `frontier_violation`, then `unchanged`.
- `test_full_rebuild_chunk_cap_refuses_multi_chunk_v1` — with `max_transform_chunks_per_run=1`
  the rebuild refuses `transform_chunk_cap`, 0 counters, no builds, checkpoint stays v1. **The
  cap still bounds paid work.**
- `test_pending_v1_transaction_refused_when_full_rebuild_allowed_c7` — **key safety test:**
  even with the flag on, a pending v1 `transaction.json` still raises `v1 transaction requires
  original runtime`. The full-rebuild bypass does **not** weaken the C7 recovery-protocol gate.

**Collateral diffs (benign):**
- `tests/test_incremental_jsonl_canary_baseline.py`: `incremental_jsonl.py` baseline hash
  refreshed with a documenting comment (expected when the file changes).
- `tests/test_incremental_jsonl_codex_rollout_route.py`: test helpers gain an
  `allow_full_rebuild` parameter defaulting to `false`.
- `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json`: `code_revision` + `inventory_digest`
  re-stamped for the new `incremental_jsonl.py` content; every route keeps
  `coverage_status: "gated"` and the same `gate_path`. No writer-boundary change.

**Production flag default (confirmed in `config.py`):** `allow_full_rebuild` parses to
`False` by default (`config.py:495`, `:509`) and is validated to be a boolean, fail-closed
(`:512-513`). So on `main` + #402 with no config change, the live route behaves exactly as
#399: v1 checkpoints refuse `migration_required`. The new rebuild path is reachable only when
someone explicitly sets `index.incremental_jsonl.allow_full_rebuild = true`.

---

## Rulings requested

### (a) Is letting `allow_full_rebuild` bypass `migration_required` acceptable?

**Yes — acceptable, PASS.** Three reasons, grounded in code and the arc's authority model:

1. **It unifies two refusals that already share one meaning.** Before #402, the admitted
   route had an asymmetry: `allow_full_rebuild` already suppressed the
   `rebuild_required:transform_fingerprint_changed` refusal (the `continuity` gate below),
   but the *earlier* `migration_required` gate ignored the flag, so a v1 checkpoint refused
   before the full-rebuild path could ever run. #402 makes the two gates agree: when a full
   rebuild is authorized, a v1 checkpoint rebuilds like any fingerprint-incompatible v2
   checkpoint. `migration_required` was never meant to override an explicit rebuild
   authorization — it is the signal "you must either migrate or rebuild," and the flag selects
   rebuild. The bypass restores the intended semantics rather than widening them.

2. **It does not weaken any safety gate.** The bypass is confined to the *quiescent
   pre-build* refusal. Every stronger gate survives with the flag on: identity
   (`verify_session_meta_identity`), projection-mismatch (`rebuild_required:<reason>`),
   bootstrap-required, the chunk cap (`transform_chunk_cap`), and — critically — the C7
   recovery-protocol gate (`_roll_forward` still refuses a pending v1 journal with
   `v1 transaction requires original runtime`, proven by the new C7 test). So the flag changes
   *what happens to a clean v1 checkpoint*, not *what happens to a v1 journal mid-flight*.

3. **The result is a loud, bounded, re-runnable rebuild, not silent reuse.** The rebuild
   emits `mode="full_rebuild_fallback"`, writes a fresh v2 checkpoint, and a subsequent run
   returns `unchanged` with zero calls. There is no path here that reuses stale v2 outputs
   under a changed contract — the C1–C8 contract machinery from #399 is untouched (I confirmed
   the admitted key is still the semantic descriptor, not a module hash).

This is acceptable **as code**. The acceptability of *operating* it is governed by rulings
(b) and (c) and the conditions below.

### (b) Restated precondition for the future real-data converter

My #399 implementation review leaned on this precondition when I ruled the migrator-vs-
coordinator lock caveat harmless:

> "an admitted v2 run refuses a v1 checkpoint pre-build with `migration_required` … so a
> v2-capable coordinator never commits over a v1 checkpoint."

**#402 changes that assumption whenever `allow_full_rebuild` is on.** With the flag on, an
admitted v2 coordinator no longer refuses a v1 checkpoint pre-build — it **rebuilds it in
place to v2**. That removes the exact property that made the hermetic converter's lock set
(source + index write flocks, no coordinator `SourceAdvisoryLock`) sufficient. If a real-data
converter and a flag-on coordinator run against the same source, the converter could stage and
publish a migrated v2 checkpoint while the coordinator independently rebuilds the same v1
checkpoint to v2 — two writers racing to publish v2 state, no longer mutually excluded by the
"coordinator refuses v1" invariant.

**Restated precondition for the real-data converter slice (both required, pick at least one;
I recommend both):**

- **P1 — The real-data converter must acquire the coordinator's own `SourceAdvisoryLock`**
  (the same inode the coordinator takes at `incremental_jsonl.py:2585-2588`,
  `state_dir/<source_id>/lock.flock`), not only `source_flock` + `index_write_flock`. This was
  already noted as the converter's first precondition in my #399 review; **#402 upgrades it
  from "belt-and-braces" to load-bearing**, because the pre-build refusal can no longer be
  relied on to keep a flag-on coordinator off a v1 checkpoint.
- **P2 — The converter must refuse to run while `allow_full_rebuild` is on for its source**
  (or the operator must disable the flag for the migration window). Converting and
  flag-on-rebuilding are two different routes to v2 for the same checkpoint; running both
  concurrently is the race. The clean operational rule is: *either* migrate via the reviewed
  converter *or* rebuild via the flag — never both on the same source at once.

Either P1 or P2 closes the race; together they are defense-in-depth. This is a **precondition
on the future converter slice**, not a defect in #402 — #402 is hermetic and its own tests run
with no live coordinator present. But the #399 lock ruling must now be read with this
amendment, and the converter slice's handoff must carry P1+P2 as its first preconditions.

### (c) Paid-rebuild risk if the flag is left on after billing resumes

**This is the real operational risk and the reason my verdict is PASS *with conditions*.**

With the flag **off** (the production default), a v1 checkpoint refuses `migration_required`
and costs nothing — zero provider calls, as the retained negative-control test proves. With
the flag **on**, that same v1 checkpoint triggers a full rebuild: every chunk is re-transformed
(summaries + embeddings), which is **paid DeepSeek work** (Ollama embeds are observed but
cap-exempt, per the arc's paid-accounting model). The chunk cap bounds a *single run*
(`max_transform_chunks_per_run`, `transform_chunk_cap` over the cap), but it does **not** bound
the aggregate: ~40 live v1 checkpoints each rebuilt is ~40 full rebuilds, and the largest live
new-route session is 4 chunks. Left on indefinitely, the flag also means any *future*
fingerprint-incompatible deploy silently re-bills a full rebuild for every admitted source
instead of refusing cheaply.

The danger window is specifically **"flag left on after billing resumes."** The migration
backlog is the one-time reason to turn it on; once the backlog is drained, leaving it on
converts the arc's cheap-refusal safety property into standing paid-rebuild exposure on every
incompatible deploy.

**Conditions (operational; Ryan/operator-owned, not code blockers):**

- **D1 — Keep `allow_full_rebuild` off by default and treat "on" as a bounded, logged
  window.** Enable it only for an explicit migration/rebuild window, with a known source set
  and a cost expectation, then turn it back off. Do not ship it on in the standing live config.
- **D2 — Do not enable the flag while provider billing is live unless the rebuild cost for the
  target source set has been estimated and authorized.** The chunk cap limits per-run work, not
  the fleet-wide total; ~40 rebuilds is a real paid number that should be sized before, not
  discovered after.
- **D3 — Prefer the reviewed converter over the flag for the two (and the ~40) legacy
  checkpoints when a zero-paid-call migration is the goal.** The #399 converter migrates v1→v2
  with **zero** provider calls by reusing the existing artifacts; the flag *rebuilds from
  scratch* and **pays**. The flag is the right tool when artifacts can't be reused (genuine
  contract change) or the converter isn't yet authorized for real data; it is the wrong tool
  if the only goal is to clear `migration_required` on checkpoints whose outputs are still
  valid. Choose per source, not fleet-wide.
- **D4 — Pair D1 with the #399 G2 backlog discipline:** sources that refuse under a flag-off
  deploy remain converter candidates; do not reach for `allow_full_rebuild` as a blanket
  "unstick everything" switch, because that is the paid path.

---

## Deploy decision — `main` + #402

**PASS with conditions.**

**On the code:** the two changes are correct, minimal, and confined to the admitted-Codex
route. They make the full-rebuild path reachable for v1 checkpoints when explicitly
authorized, fix the multi-chunk `frontier_violation`, and preserve every safety gate
(identity, projection, bootstrap, chunk cap, and the C7 pending-journal refusal). The
flag-off path is byte-identical to #399. `chroma_write_store.py`, `authority_manifest.py`,
and `WRITER_GATE_PROTOCOL_VERSION` are untouched; the writer-coverage inventory change is a
mechanical re-stamp with no boundary change. Tests I ran (33 governing + 81 focused + 5
named) are green, corroborating Claude's 497-test/CI evidence on the surface that matters.

**Why "with conditions" and not clean PASS:** the conditions are **operational**, not code
fixes. #402 is safe to *ship* in the default-off state and should ship together with #399 —
without it the ~40 live v1 checkpoints have no non-refusing path. But two things must travel
with the deploy:

1. **The #399 migrator-vs-coordinator lock ruling is now amended** (ruling b): the "admitted
   v2 run refuses a v1 checkpoint pre-build" invariant no longer holds with the flag on, so
   the real-data converter slice must take the coordinator `SourceAdvisoryLock` (P1) and/or
   refuse while the flag is on (P2). This is a precondition on a *future* slice, recorded here
   so it is not lost.
2. **The flag is a paid-rebuild switch** (ruling c): keep it off by default (D1), size and
   authorize cost before enabling with live billing (D2), prefer the zero-paid-call converter
   where artifacts are reusable (D3), and don't use it as a blanket unstick (D4).

**What this PASS does and does not cover:** it covers deploying the merged code of #399 + #402
to `main`. It does **not** authorize enabling `allow_full_rebuild` in the live config, running
the converter against real sessions, or any watcher/runtime promotion — each remains a
separate Ryan grant, consistent with the arc's hard stops (§7 of
`STATUS-codex-jsonl-production-integration.md`).

**Separation held:** this review grants no deploy, flag enablement, migration, hold release,
config, or runtime promotion. It did not touch `.worktrees/runtime-main`.

---

## Forward announcement

I finished: Kiro deploy-gate review of PR #402 (`b3dccb9`) for deploying `main` + #402 —
code rulings (a) full-rebuild bypass of `migration_required`, (b) amended converter
precondition, (c) paid-rebuild risk; independent tests run; verdict PASS with conditions.
Next step:  Ryan decides whether to deploy `main` + #402 together (my rec: yes, flag off),
and carries P1+P2 to the real-data converter slice and D1–D4 to any flag-on window.
Next lane:  Ryan (deploy + flag/billing decisions); then whoever is granted the real-data
converter slice (must honor P1+P2).
See my work: `docs/inter-model/KIRO-2026-10-18-issue-286-deploy-gate-review.md` on branch
`kiro/2026-10-18-issue-286-deploy-gate-review`.

**TL;DR:** [Arc Codex #286] **DEPLOY verdict for `main` + #402: PASS with conditions.** The
two edits are correct and confined to the admitted-Codex route: (1) `migration_required` is
suppressed for a v1 checkpoint only when `allow_full_rebuild` is true, falling through to the
existing full-rebuild path; (2) full rebuilds compute admission as `initial_full`
(`prior_count=0`) so multi-chunk v1 histories stop hitting `frontier_violation`. The chunk cap
and the C7 pending-v1-journal refusal both survive the flag; the flag-off path is identical to
#399; config default is off and fail-closed. I ran 33 governing + 81 focused + 5 named tests —
all green. **(a)** The bypass is acceptable — it unifies two refusals that already share one
meaning and weakens no safety gate. **(b)** It invalidates my #399 assumption that a v2 run
refuses a v1 checkpoint pre-build, so the real-data converter must take the coordinator
`SourceAdvisoryLock` (P1) and/or refuse while the flag is on (P2). **(c)** With the flag on, a
v1 checkpoint rebuilds and *pays* (DeepSeek) instead of refusing free; keep it off by default,
size/authorize cost before any flag-on window with live billing, and prefer the zero-paid-call
#399 converter where artifacts are reusable (D1–D4). PASS covers deploying the code, not
enabling the flag or running live migration.

<!-- ref: ./KIRO-2026-10-17-issue-286-transform-compatibility-impl-review.md — #399 DEPLOY PASS; its migrator/coordinator lock ruling is amended here -->
<!-- ref: ./KIRO-2026-10-17-issue-286-transform-compatibility-review.md — #399 design review (C1–C8) -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex current-state brief and hard stops -->
<!-- src: ../../incremental_jsonl.py, ../../config.py, ../../incremental_transform_contract.py, ../../tests/test_incremental_transform_compatibility.py, ../../tests/test_incremental_jsonl_codex_rollout_route.py — reviewed at PR #402 tip b3dccb9 -->
