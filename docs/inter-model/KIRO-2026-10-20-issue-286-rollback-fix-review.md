# [Arc Codex #286] Kiro design review — rollback empty-before-image fix brief

**Author: Kiro (design review / sign-off lane). Date: 2026-10-20 UTC. Arc: Codex.**
Read-only review from an isolated worktree. No production code, tests, config, or
live-state commands were run.

- **Reviewed documents** (branch `docs/2026-10-20-issue-286-rollback-empty-before-image`, commit `dd2ad2d`, one doc commit over `main` `686d50e`):
  - `docs/inter-model/ASTRA-2026-10-20-issue-286-rollback-empty-before-image.md` (investigation + §7 R-975 repair spec)
  - `docs/inter-model/ASTRA-2026-10-20-issue-286-rollback-fix-brief.md` (proposed Cursor scope + 10 hermetic tests)
  - `docs/inter-model/ASTRA-2026-10-20-issue-286-rollback-census.json` (evidence census)
- **Code verified against** `incremental_jsonl.py`, `purge_locks.py`, `ingest.py`, and
  `tests/test_incremental_jsonl_state.py` at the review worktree tip. The brief cites
  older line numbers (it examined `686d50e`); I verified by symbol/behavior, not line
  number. Content matches. This review doc is committed on `main` tip `a5405ad`
  (two commits over `686d50e`); the two extra commits do not touch the rollback paths.
- **This review is a design verdict only.** It is not an Execute grant. Cursor
  implementation still requires Ryan's authorization.

---

## Verdict: PASS-WITH-CHANGES

The investigation is sound and I independently reproduced its central code claims
(below). The proposed correction — fresh locked capture, fail-closed semantic
recovery validation, locked conditional merge, conservative legacy-journal policy,
and the explicit cross-surface concurrency limit — is the right shape and is correctly
scoped. The 10 hermetic tests are close to sufficient and test 1 correctly insists on
driving through the real route. The lock order (`source_flock` before C1, no processed
lock during Chroma/export) is consistent with the existing commit/purge order and does
not introduce a new deadlock, **provided** the required changes below are honored.

I am issuing PASS-WITH-CHANGES rather than a clean PASS because the brief leaves four
decidable gaps that a Cursor implementer could satisfy incorrectly while still passing
the stated tests (C-1 reentrancy proof, C-3 ownership-proof definition, C-5 the final-CAS
partial-recovery contract, and C-6 a test-level deadlock/lock-order assertion). These are
tightening requirements, not a redirect.

---

## Code claims I verified independently (read-only)

| Claim in report/brief | Verified in code | Status |
|---|---|---|
| `_processed()` returns `processed_override` even when `{}` (empty not reloaded) | `_processed()`: `if self.processed_override is not None: return self.processed_override` | CONFIRMED |
| Capture selects by `value.get("path") == self.path_key`, retains original keys | `_snapshot_before_images()` processed_preimage comprehension | CONFIRMED |
| `_restore_processed()` does unlocked load→filter→update→save | `_restore_processed()`: `load_processed → dict comp → restored.update → save_processed`, no `mutate_processed`/`_processed_lock` | CONFIRMED |
| Capture runs under `source_flock → index_write_flock` in commit | `_commit_generation`: `with source_flock(...)` then `with index_write_flock(...)` then `_snapshot_before_images` | CONFIRMED |
| Processed restore happens after Chroma/export restore | `_restore_before_images` order: rows → `_restore_export` → `_restore_processed` → state → prepared → dedupe | CONFIRMED |
| Recovery (`_restore_replay_before_images`) holds only C1, not `source_flock` | method wraps restore in `with index_write_flock(self.cfg)` only | CONFIRMED |
| `validate_rollback` checks only version/required/source/list-types, not processed/checkpoint consistency or ownership | `validate_rollback()` body | CONFIRMED |
| Commit publishes processed OUTSIDE source_flock/C1 (standalone processed critical section) | `_publish_processed` runs in `phase_span("processed")` after the `finally: c1_hold_seconds` closes the lock block | CONFIRMED |
| Existing test asserts unowned same-source edit is deleted | `test_restore_rewinds_processed_checkpoint_and_state` injects `processed["tampered"]={"path":source,...}` and asserts `"tampered" not in restored_processed`; calls `_restore_before_images` directly, not via route | CONFIRMED |
| Lock-order is enforced, not merely conventional | `purge_locks.assert_lock_ordering_ok(acquiring="source")` raises if `_index_write_depth() > 0` or export held | CONFIRMED — stronger than the brief states |
| C1 reentrant; `source_flock` not reentrant | `index_write_flock` is depth-counted (re-locks only at depth 0); `source_flock` takes a fresh `flock(LOCK_EX)` each call with only an advisory depth counter | CONFIRMED — see required change C-1 |

The investigation did not overstate. Two of its claims are actually understated in a way
that helps the fix: (a) the `source`-under-C1 ordering is machine-enforced by
`assert_lock_ordering_ok`, so a mis-ordered implementation fails loudly instead of
deadlocking silently; (b) C1 is reentrant, so the Chroma `_session()` re-acquisition
inside a C1-held restore is safe.

---

## Rulings on the brief's three open decisions

### Decision 1 — Conservative refusal policy for old inconsistent/ambiguous rollback journals: **ACCEPT**

Accept the fail-closed policy as written in report §6 and brief §B. A rollback journal
that has a prior incremental checkpoint but an empty or wrong-key/wrong-lineage/wrong-path
processed preimage (the R-975 shape) must **refuse before any restore write** and preserve
the journal, transaction, snapshot, and prepared bytes byte-identically. `validate_rollback`
today proves only structural integrity and a bound SHA; a hash-valid journal is explicitly
*not* a semantically valid one. The policy correctly refuses to synthesize authority or
rewrite a bound SHA to make a bad journal pass.

One required tightening (C-2 below): the empty-preimage *exception* for a genuinely new
source and for checkpointless legacy bootstrap must be defined by a positive predicate
(no prior incremental checkpoint AND no prior rows AND no prior processed entry), not by
"the preimage happens to be `{}`." Otherwise the fix risks either banning legitimate first
generations or re-admitting the R-975 shape through the bootstrap door.

### Decision 2 — Narrow locked-merge scope, with cross-surface limit and global writer fence (E2) left out of scope: **ACCEPT**

Accept the narrow scope: fresh capture + recovery preflight + locked CAS merge, with the
stated cross-surface non-atomicity limit explicitly undelivered and the global writer fence
(E2) left out. This is the correct minimal correction. Two reasons it is safe to ship narrow:

1. The commit path already publishes processed state in a **standalone critical section
   outside** `source_flock`/C1 (verified). So the fix is not introducing a new concurrency
   model — it is making the *restore* side honor the same processed-sidecar discipline the
   commit side depends on. The brief's "do not hold the processed lock during Chroma/export"
   is consistent with how commit already behaves.
2. The brief is honest that preflight + final CAS is **not** a cross-surface atomic
   transaction. That honesty must survive implementation (see C-5): the fix must *refuse and
   preserve authority* on late conflict rather than paper over the gap by widening a lock.

Required tightening (C-4): the brief says "do not alter persisted schemas unless ownership
cannot be proven from current checkpoint/transaction/prepared evidence; a new authority
field requires a reviewed design decision." I accept that, and I am ruling that **adding a
new persisted authority field is out of scope for this corrective** — if the implementer
finds that transaction ownership of a changed same-source slice cannot be proven from the
existing checkpoint/transaction/prepared evidence, the correct outcome is **refusal**, not
a schema addition. A schema/version change returns to Kiro as a separate design decision.

### Decision 3 — Prepare a separately rehearsed R-975 one-entry repair packet (§7): **YES**

Prepare the packet, but keep it strictly separate from the Cursor code corrective and gate
it behind the code fix landing first. What the rehearsed packet must prove, before any live
write, in a rehearsal against a copy of the donor + current metadata:

1. **Donor integrity:** whole-file donor SHA-256 `56478757…e9b7d`; the exact one-key payload
   under key `02b3dafe…b20a` with `chunks:1, units:10, lineage 82756622…614b`. Never the
   current whole-file source hash and never the failed transaction's `1e608306…` key.
2. **Target consistency:** checkpoint hash `acddb732…dcdd3b`; source device/inode and SHA-256
   over exactly 1,113,106 bytes; checkpoint key/lineage; both collection manifests; projection
   hash; all 10 export units. Abort on any mismatch.
3. **One-key delta under `processed.json.lock`:** reload current state; abort if any canonical
   alias, exclusion, different same-source entry, or foreign owner of the donor key exists;
   idempotent no-op if the exact entry is already present; otherwise insert exactly one key and
   preserve every unrelated key/value byte-for-byte.
4. **Post-write verification:** re-read, confirm the exact one-key delta, and confirm all
   unrelated entries, the checkpoint, export, collections, and source are unchanged.
5. **Scoped reversal** of only that key if needed before any later generation publishes.
6. **Writer-free window:** the packet must name the approved no-writer window (E2 fence or an
   approved E3 equivalent) and a copy-first backup. The packet proves the *procedure*; it does
   not grant the window, the watcher restart, or the subsequent rebuild spend — those remain
   Ryan's.

**Is 914be526 (R-914) repairable on current evidence? No — not yet.** R-914 has a valid
checkpoint, matching projection (1 summary + 6 units), and all 6 export units, but there is
**no retained journal** attributing its missing processed entry to a rollback (vs. a failed
follower publish or a later edit), and its missing tail is 927,034 bytes. The census also
shows R-914 absent in all seven processed snapshots, with the earliest snapshots predating
its source — so its absence is not even evidenced as a *loss*. Repairing it now would require
inferring a donor entry that no retained evidence supports; that is exactly the inference the
report refuses for R-975's `1e608306…` key. **R-914 needs its own attribution first** (a
retained journal or an authoritative donor snapshot establishing the exact lineage/counts),
tracked as a separate evidence follow-up — never repaired by analogy to R-975.

---

## Are tests 1–10 sufficient to prove the fix?

**Mostly yes, with the required additions below.** The suite covers the two capture-staleness
variants (empty and nonempty), the R-975 refusal shape and its wrong-key/lineage/path/type
siblings, the legitimate-empty and legacy-bootstrap non-regressions, alias/collision handling,
the concurrent foreign processed writer, later-same-source/exclusion preflight refusal, the
post-preflight CAS race, crash boundaries with corrupt prepared artifacts, the other rollback
surfaces (Chroma/export/prepared), and a routing/lock-order check. That maps 1:1 onto the three
behavioral requirements (A capture, B validate-before-write, C locked merge) and the two policy
decisions.

**Test 1 must go through `maybe_route_incremental`, not a hand-built coordinator — I agree and
it is load-bearing.** I verified why: the stale-override bug lives in the *route*, which reads
`processed.json` from disk before acquiring the source lock and passes it as `processed_override`.
A directly constructed coordinator calling `_snapshot_before_images()` with `processed=None` (as
the existing `test_restore_rewinds_processed_checkpoint_and_state` does) **cannot reproduce the
defect at all**, because `_processed()` then reloads fresh disk. So any test that proves the fix
must exercise the override path end-to-end. Test 1's wording ("Exercise `maybe_route_incremental`,
not just a manually constructed coordinator with `processed=None`") is correct and must not be
softened.

### Required test additions / tightenings

- **C-6 (lock-order/deadlock assertion is required, not optional):** Test 10 must assert, at
  method level, that during recovery `source_flock` is acquired *before* C1 and that no code path
  acquires `source_flock` while `index_write_lock_depth() > 0`. This is directly checkable via
  `purge_locks.source_lock_depth()` / `index_write_lock_depth()`. It is cheap and it pins the one
  mistake that would otherwise surface only as a `RuntimeError` from `assert_lock_ordering_ok`
  under a specific interleaving. Add an explicit assertion that a second `source_flock` acquisition
  for the *same* path on the restore path does not occur (see C-1).

- **Nested/reentrant source-lock case (new):** add a focused test that the recovery path does not
  nest `source_flock` for the same canonical path. `source_flock` is **not** reentrant (fresh fd +
  `flock(LOCK_EX)` each call; the depth counter is advisory only), so a nested acquisition on the
  same path in the same process self-deadlocks. The brief says "check nested/reentrant acquisition
  and all entry paths" — that must become an executable assertion, not a review note.

- **Test 6 must assert the restore path actually holds the processed sidecar lock** (the brief says
  "Assert the stable sidecar is held by the restore path"). Keep that; additionally assert the same
  sidecar namespace is used by commit's `mutate_processed`, so the fix cannot silently introduce a
  second lock file (brief §A: "avoid a read helper that creates a second, different lock namespace").

- **Converting the existing test (required, with a guard):** `test_restore_rewinds_processed_
  checkpoint_and_state` currently asserts the unsafe deletion of an unowned same-source edit
  (`processed["tampered"]`). It must be inverted to assert refusal + preservation, and a *separate*
  positive test must prove that a genuinely transaction-owned changed slice **is** restored. The
  guard: do not keep the old assertion alive by routing it through a path that bypasses the new
  safety gate. The replacement must prove the gate fired.

- **"Fails on 686d50e, passes on the fix" is mandatory evidence.** The brief already requires this;
  I am making it a sign-off condition. Cursor must show each new regression test (1, 2, 3, 6, 7, 9)
  failing on the pre-fix baseline and passing on the correction, with zero attempted provider
  connections and no live-path writes.

### Gaps worth an explicit test, currently only implied

- A test that **export** restore refuses a later valid same-source export it cannot prove it owns
  (report §4 lists export replacement as a live risk; test 9 bundles it with Chroma/prepared but
  should assert the export line case specifically).
- A test that a **foreign-key collision** (preimage hash now owned by a *different* source) causes
  refusal and leaves the foreign entry intact (test 5 names it; make the unrelated-map equality
  assertion explicit for the foreign owner, not just "a key").

---

## Does the lock order introduce a deadlock or a new burn path?

**No new deadlock, and no new provider-burn path, given the required changes.** Analysis:

1. **`source_flock` before C1 is the existing order.** Commit acquires `source_flock` then
   `index_write_flock`; purge (per report §4) marks exclusion under `source_flock` before C1.
   Recovery today holds only C1. Adding `source_flock` *outside* C1 in `_restore_replay_before_
   images` matches commit/purge and does not invert anything.

2. **The order is machine-enforced.** `assert_lock_ordering_ok(acquiring="source")` raises if the
   caller already holds C1 or the export lock. So the dangerous mistake (acquiring source *inside*
   C1) cannot silently deadlock — it raises immediately and loudly. This is a strong safety net and
   it is why I accept the narrow scope.

3. **C1 reentrancy makes the nested Chroma session safe.** `index_write_flock` is depth-counted and
   only takes the OS lock at depth 0. The restore holds C1, and `_session()` re-enters C1 for the
   Chroma row restore — safe because of reentrancy. No change needed there.

4. **The one real hazard is nested `source_flock` on the same path.** `source_flock` is not
   reentrant. If the implementer adds `source_flock` at the top of `_restore_replay_before_images`
   and any inner helper (now or later) also opens `source_flock` for the same path, the process
   self-deadlocks on its own `flock(LOCK_EX)`. This is covered by required changes C-1 and C-6:
   acquire `source_flock` exactly once at the recovery boundary, and assert non-nesting in tests.

5. **No provider under write scope.** `reject_provider_under_write_scope()` already forbids provider
   calls while C1 or a Chroma session is held, and the brief forbids holding the processed lock over
   model/Chroma/export work. The fix must not move any transform/provider call inside the new
   `source_flock`/C1 span. Test 10 already requires "no provider call under write scopes" — keep it.

6. **Export lock ordering unchanged.** `export_flock` requires C1 to be held (`assert_lock_ordering_
   ok(acquiring="export")` raises if `_index_write_depth()==0`), and the restore does export work
   inside C1 already. The fix must not pull export work outside C1.

**Burn path:** the only way this corrective could create a *new* burn (repeated expensive
transforms) is if a refusal path re-enters the route and re-transforms. The brief's "retain recovery
authority and report partial recovery rather than cleaning up" prevents that: a refused recovery
preserves the journal/snapshot so the next attempt replays prepared artifacts with zero calls
(`clear_incremental_retry_state` only runs on committed/unchanged). Test 8's "retrying a successful
scoped restore is idempotent; a crash never converts an unknown state into deletion authority" pins
this. No new burn path, provided refusals preserve rather than clean up (C-5).

---

## Required changes to the brief (numbered)

1. **C-1 — `source_flock` acquired exactly once; prove non-nesting.** State explicitly that recovery
   acquires `source_flock` once at the `_restore_replay_before_images` boundary, *outside* C1, and
   that no inner helper re-acquires `source_flock` for the same canonical path. Add that
   `source_flock` is non-reentrant and nesting self-deadlocks. (Enforced by `assert_lock_ordering_ok`
   for the source-under-C1 case; nesting on the same path is not caught by that guard and must be
   prevented by construction.)

2. **C-2 — Define the empty-preimage exception by a positive predicate.** Replace "allow a genuinely
   empty initial generation" with: an empty processed preimage is permitted only when there is no
   prior incremental checkpoint AND no prior same-source rows AND no prior processed entry (new
   source), or under the existing checkpointless legacy-bootstrap grant semantics. The R-975 shape
   (prior checkpoint present, preimage empty) must refuse. Forbid admitting R-975 through the
   bootstrap path.

3. **C-3 — Define "transaction-owned" precisely.** "Positively proven to be this transaction's
   published state" must be defined as: the changed same-source slice matches the transaction's
   recorded written row ids / prepared keys / checkpoint lineage from the *transaction and prepared*
   evidence — not a matching `path` and not a merely plausible lineage string. If that evidence is
   absent or corrupt, the outcome is refusal. (`_transaction_written_row_ids` already exists and is
   the kind of evidence to use; name the authoritative source of ownership explicitly.)

4. **C-4 — No persisted-schema change in this corrective.** If transaction ownership of a changed
   same-source slice cannot be proven from existing checkpoint/transaction/prepared evidence, refuse.
   Adding a new persisted authority field/version is out of scope and returns to Kiro as a separate
   design decision.

5. **C-5 — Final-CAS partial-recovery contract.** The final locked merge must re-check the source
   slice even after preflight; on a late conflict it must leave the other writer's state intact,
   retain recovery authority, and report partial recovery honestly — never call `_cleanup()` or
   return `rolled_back` as if whole-recovery succeeded, and never re-enter a path that re-transforms.
   Make "refusal preserves evidence so replay is zero-call" an explicit acceptance criterion.

6. **C-6 — Make the lock-order and non-nesting checks executable.** Test 10 must assert (via
   `purge_locks.source_lock_depth()` / `index_write_lock_depth()`) that `source_flock` precedes C1,
   is never acquired under C1, and is never nested for the same path on the restore path, plus no
   provider call and no global processed lock held during Chroma/export.

7. **C-7 — Scope R-914 as attribution-first.** State in the brief (not only the report) that R-914
   is not repairable on current evidence and must not be repaired by analogy to R-975; it requires
   its own retained-journal or authoritative-donor attribution first, tracked separately.

8. **C-8 — Keep the R-975 repair packet gated behind the landed code fix.** The rehearsed packet
   (Decision 3) must be prepared and reviewed separately, must not execute any live write, and must
   not be bundled into the Cursor code PR. Its rehearsal evidence returns to Kiro before Ryan's
   window/spend decision.

None of these changes alter the brief's architecture; they remove the degrees of freedom that would
let a passing implementation still be wrong.

---

## What I did NOT verify (limits of this review)

- I did not run any test, build, linter, or live-state command (read-only grant). "Fails on
  `686d50e`, passes on the fix" is required of Cursor; I verified the *mechanism* that makes those
  tests meaningful, not their execution.
- I did not re-run the census or any projection/Chroma/restic check; I relied on the report's and
  census's evidence for the R-975/R-914 metadata facts and verified only the code behavior they
  depend on.
- I reviewed `incremental_jsonl.py` / `purge_locks.py` / `ingest.py` on the review-branch tip
  (`a5405ad`), two commits past the `686d50e` the brief examined; the two extra commits
  (`#409` expand CLI registration, `#410` Crush doctor concurrency) do not touch the capture,
  restore, or lock paths, so the behavioral claims hold on both tips.
- I did not inspect the historical authoring runtime (`8a7cdab`); the report's identity proof for
  it is outside this review's read-only code scope and I take it as given.

---

## Forward announcement

I finished: Kiro design review of the Arc Codex #286 rollback fix brief.
Next step:  Ryan's Cursor Execute decision; if granted, Cursor implements with C-1…C-8 folded in.
Next lane:  Ryan (grant), then Cursor (implement), then Kiro + independent review of the exact tip.
See my work: `docs/inter-model/KIRO-2026-10-20-issue-286-rollback-fix-review.md` on branch
             `docs/2026-10-20-issue-286-rollback-fix-review`.

## TL;DR

- **Verdict: PASS-WITH-CHANGES.** The investigation is accurate — I independently reproduced its
  central code claims (stale-override capture, unlocked restore, SHA-only `validate_rollback`,
  commit's standalone processed critical section, the misleading existing test). The correction's
  shape is right and correctly scoped.
- **Decisions:** (1) ACCEPT the conservative refusal policy; (2) ACCEPT the narrow locked-merge
  scope with the cross-surface limit and E2 left out; (3) YES, prepare a separately rehearsed R-975
  one-entry packet gated behind the landed code fix. **914be526 is NOT repairable on current
  evidence** — it needs its own attribution first and must not be repaired by analogy.
- **Tests 1–10 are nearly sufficient; test 1 correctly requires the real route** (a hand-built
  coordinator cannot reproduce the override bug). Added required checks: executable lock-order /
  non-nesting assertions, sidecar-held assertion, inverted-with-guard conversion of the existing
  test, and explicit export/foreign-collision cases.
- **No new deadlock or burn path:** `source_flock` before C1 matches commit/purge and is
  machine-enforced; C1 is reentrant (safe Chroma re-entry); the only hazard is nested same-path
  `source_flock`, pinned by required changes C-1/C-6; provider-under-write-scope is already blocked.
- **8 required changes (C-1…C-8)** tighten the brief without changing its architecture.

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Codex #286 | The incremental Kiro/Codex JSONL ingestion arc; see `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| R-975 | The incident source `975fc327…` whose rollback bound an empty processed before-image, erasing a valid entry |
| R-914 | A second source `914be526…` missing its processed entry, with no proven rollback cause |
| before-image | The pre-mutation snapshot (rows/export/processed/checkpoint) a rollback journal captures to restore on failure |
| capture | `_snapshot_before_images()` — builds the before-image at the mutation boundary |
| processed override | A caller-supplied processed-state dict passed into the coordinator; `_processed()` prefers it over disk |
| C1 | The store-wide index write lock (`index_write_flock`); reentrant/depth-counted |
| `source_flock` | The per-source advisory file lock; non-reentrant; must be acquired before C1 |
| CAS merge | Compare-and-set locked merge of processed state: reload under lock, compare slice, update only owned entries |
| preflight | Validation of current state vs. authority *before* any restore write |
| E2 / E3 | Writer-fence options for a no-writer repair window (E2 global fence; E3 an approved equivalent) |
| burn path | A code path that incurs repeated expensive provider/transform calls |
| route / `maybe_route_incremental` | The real ingest entry that reads processed state and dispatches the coordinator |
| lineage | `incremental_jsonl_lineage` / projection fingerprint tying a processed entry to a checkpoint |
| Track A | Indexing this session's chat transcript into convmem (handoff requirement) |

<!-- src: ./ASTRA-2026-10-20-issue-286-rollback-empty-before-image.md, ./ASTRA-2026-10-20-issue-286-rollback-fix-brief.md, ./ASTRA-2026-10-20-issue-286-rollback-census.json — reviewed investigation, brief, and census -->
<!-- src: ../../incremental_jsonl.py, ../../purge_locks.py, ../../ingest.py, ../../tests/test_incremental_jsonl_state.py — code claims verified read-only at review tip -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex current state and next lane -->
