# Crush Evidence/Failure Review — CG-2 Production Activation Architecture

**Date:** 2026-08-14
**Author:** Crush (evidence/failure review lane)
**For:** Ryan (Architecture HITL decision) and the CG-2 review chain
**Target revision (locked):** `1222b1ede2d6cc5da582388768f06d60b36c5e50` on `plan/2026-08-14-cg2-production-activation`
**Reviewed against:** `HANDOFF-CG1-DEPENDABILITY-2026-08-10.md`, `CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md`, `CURSOR-2026-08-10-cg1-literature-verification-handoff.md`, `STATUS-chroma-reconcile-tier-l.md`, `query.py`, `watch.py`, `chroma_store.py`, `file_generation_store.py`, CG-1 test suite, installed watchdog version, upstream Chroma `#7463` / PR `#7469`.

> **Supersession (2026-08-15):** Architecture locked at `e680ce8`. N1–N3 dispositions address
> several gaps named here. Authoritative rollup:
> [`CURSOR-2026-08-15-cg2-delta-confirmation.md`](CURSOR-2026-08-15-cg2-delta-confirmation.md).
> This file preserves the `1222b1e` evidence record only.

---

## 1. Verdict

**PASS WITH RISKS** against SHA `1222b1ede2d6cc5da582388768f06d60b36c5e50`.

The architecture's safety claims are grounded in real operational behavior and
CG-1 evidence, not aspiration. The Chroma `#7463` characterization is accurate
to the reporter's words. The failure-mode taxonomy is substantially complete and
honest about what is and is not claimed (notably the CG-1 durability bar). Three
evidence gaps are named below; none invalidates the architecture direction, but
each must be resolved in the §13 evidence packet before a first canary:

1. **`query.py` broad-exception fallback** is an unmediated legacy read that
   would violate the architecture's own fail-closed §5.3 rule if a
   generation-authority failure ever routed through it. The architecture says
   this must not happen but does not yet name the structural mechanism that
   prevents it.
2. **The watcher cannot expose `IN_Q_OVERFLOW`** through the watchdog
   `Observer` API `watch.py` uses today. The §7.1 "overflow marks
   reconciliation-required" hedge is correct but underspecified: it cannot rely
   on the event stream, so the reconciliation-required trigger and the §13.9
   forced-overflow gate need a concrete non-watchdog mechanism.
3. **No crash test asserts the active+previous retention invariant across one
   real process kill during promotion.** The CG-1 suite proves process-death
   mid-staging recovery and promotion-window fault semantics separately, but
   not the combined invariant §10.1/§2.7 and §13.11 require.

Details per review area below.

---

## 2. Per-section findings

### 2.1 Review area 1 — Failure-mode table (§11) completeness and honesty

**Finding: no issue found on honesty; one correctness defense is incomplete.**

- **`query.py` fail-closed problem (named, medium).** The architecture's §3 and
  §5.3 require that a generation-authority failure **must not** silently become
  an unmediated legacy read. But the current production query path catches broad
  failures and falls back regardless of cause:
  - `query()` at `query.py` wraps the Chroma read in `try: ... except Exception:`
    and unconditional `_fallback_query_rows(...)` (broad catch at ~line 428).
  - `query_raw()` does the same at ~line 523 (`conversation_summaries`).
  - `_fallback_query_rows`, in `query.py`, re-reads **raw metadata rows** via
    `collection_metadata_rows(chroma_dir, collection_name)` and applies only
    `is_superseded` / site / domain / `_keyword_score` filters. It applies **no
    owner, fence, pointer, or authority filtering**. It is a genuine serving
    bypass today.
  - The architecture is fully aware of this (it is listed as a §3 fact and §5.3
    refuses fallback for authority failures), but **it does not name the
    structural mechanism** by which a legacy `query()` broad `except Exception`
    stops being the escape hatch for a generation-authority failure. Since the
    serving repository is not yet built, this is more truthfully a Cursor
    feasibility question, but from an evidence standpoint the **failure path the
    architecture promises to eliminate exists today with no named guard**, only a
    stated intention. §13.3 (all four bypass classifications to zero) would cover
    this, but the direct `--raw`, MCP `related`, MCP `stats` bypasses are only
    classified; the *fallback* bypass is not in that list.
- **Every §11 row has a plausible mechanism in current code.** Rows map to real
  CG-1 paths: stale-generation check (`insert`/`promote` CAS), source-hash guard
  (new, §7), recovery-no-complete (`recover_active_pointer`), pointer/manifest
  mismatch quarantine (`GenerationQualificationError`), GC crash (pin protocol,
  future). No row is fabricated or merely literary.
- **G4b/activation-blocker coverage is complete** (see area 6). The five blockers
  recorded in the CG-1 closure (doctor `index_drift`, `projection_parity`
  logical_id, queue growth, legacy path aliases, direct read bypasses) each have
  a §3/§8/§10.2/§13 home.
- **A failure mode the table omits (low, informational):** the current watcher's
  unbounded in-memory `_batch` list under high-frequency writes (see area 4) is
  not itself a §11 row. It feeds event loss, which §11 handles ("Watch event is
  lost/coalesced/overflow"), so this is subsumed rather than omitted.

**Verdict per area 1:** PASS, with the `query.py` fallback guard mechanism
named as a required §13 evidence/design item.

### 2.2 Review area 2 — Chroma evidence (§3, §13, §15), `#7463` disposition

**Finding: the `#7463` characterization is accurate; the evidence gates are well-scoped; one additional local proof already exists.**

- **`#7463` is correctly characterized.** The architecture calls it "an
  operational replay-cost/missing-flush-primitive report, not data loss." This
  matches the reporter verbatim ("**this is not a data-loss report**"); the
  reporter built a hard-kill repro that *disproved* data loss. Sub-threshold
  writes are committed to the SQLite `embeddings_queue` before `upsert()` returns
  and survive a SIGKILL via **WAL replay on open**, while the HNSW VECTOR segment
  (`data_level0.bin`) persists only after the write counter crosses
  `sync_threshold` (default **1000**). The architecture's phrasing
  "sub-threshold writes recovered ... through WAL replay while HNSW persistence
  lagged" is a faithful summary. Version 1.5.9, `PersistentClient` — correct.
  (Source: `#7463` body; PR `#7469`, open, adopts the requested `flush()`.)
- **§13 item 15 gates are the right ones and one is already empirically backed.**
  The listed items (WAL/backlog, vector persistence lag, cold-reopen replay,
  churn, delete, physical amplification) map directly to the `#7463` behaviors.
  Better: **ConvMem already reproduces the crash-replay-tail behavior locally**
  in `test_known_queue_vector_replay_tail_recovers_exact_expected_set`
  (`tests/test_file_generation_durability.py`), which asserts
  `queue_max_seq_id > vector_position` (queue ahead of persisted HNSW), then
  proves reopen replays and returns only the active generation. So the "pinned
  1.5.9 tests must bound WAL replay" gate is not speculative; the machinery
  already exists and needs only the backlog/amplification bounds.
- **No contradiction from Tier-L.** `STATUS-chroma-reconcile-tier-l.md` closed
  GREEN that HNSW↔METADATA orphan parity is achievable at tier S (0 orphans)
  after rebuild, and that the `_flatten` P0-A guard is deployed. The 646-orphan
  incident is a **different inconsistency axis** (HNSW rows with missing
  METADATA) than `#7463` (METADATA durable, HNSW lags). The architecture
  correctly treats Tier-L as foundation, not as proof of `#7463`-style
  persistence lag. No §3/§13 assumption contradicts the Tier-L record.
- **A subtle reservation (low):** `#7463` ran on macOS ARM64. The architecture
  correctly restricts to "pinned-version behavior on ConvMem's Linux filesystem
  remains an empirical gate." This is honest and is the right disposition; it is
  a gate, not a defect.

**Verdict per area 2:** PASS. `#7463` characterization accurate; §13.15 gates
are appropriate and partially pre-proven.

### 2.3 Review area 3 — Authority-resolution linearization (§5.1) failure plausibility

**Finding: the pattern is sound, but the retry is unbounded and §13.10 does not assert termination.**

- **Convergence under realistic workloads is plausible but unproven.** The
  seqlock-like read/copy/verify/retry is over per-owner durable evidence
  (fence, pointer, manifest, retirement). Under steady state these objects are
  quiescent, so retry converges on the first pass. The plausible non-convergence
  (livelock) case is **rapid pointer republication during a batch promotion or a
  rename migration** (which touches ordered owner locks per §8): if evidence
  bytes keep changing every attempt (e.g., a pointer republished by a concurrent
  event loop or a previous generation rotating), the resolver could retry
  indefinitely.
- **The architecture names no retry limit, no bounded-iteration terminator, and
  no distinct livelock error state.** It honestly labels the pattern and
  explicitly disclaims kernel-seqlock completeness, but from an *evidence*
  standpoint §13.10 ("Concurrent fence/pointer/retirement changes force
  authority-resolution retry") asserts retries *happen*; it does **not** assert
  a retry **terminates** under adversarial churn. A livelock would manifest as a
  request that never serves — arguably fail-closed (safe) but not converged. The
  distinction matters for a latency/backlog budget (§13.17).
- **Mitigation is within reach:** order the evidence reads (e.g., verify the
  pointer last, since pointer publication is the final monotonic step), and bind
  retries to a measured cap with an observable QUARANTINED/refusal on cap
  exhaustion. This is an execution/design detail but should be recorded in the
  formal model step (§13.18) and a §13.10 sub-property.

**Verdict per area 3:** PASS WITH RISK. Livelock is a realistic-but-narrow
failure; terminate-and-refuse behavior must be made explicit.

### 2.4 Review area 4 — Source reconciliation (§7.1) operational cost and watchdog overflow

**Finding: cost is plausible but unmeasured; the overflow signal genuinely does not exist in today's watcher.**

- **Operational cost is feasible.** Corpus is ~21k units, 2591 summaries, 1363
  indexed sources (doctor/brief, 2026-08-15). Periodic reconciliation is
  "secure open + SHA-256 each canonical source and compare to the manifest/
  recorded source hash." Hashing 1363 files even at 1 MB average is only ~1.3 GB
  of reads total — sub-second to a few seconds on SSD, streamed one file at a
  time. The memory budget is bounded by a single file's bytes (plus Chroma's
  already-observed ~0.11 G RSS resident). This is not a CPU/IO/latency
  in-feasibility; the heavier cost would be the *parse/embed* work that only
  happens when a mismatch is found, which is already the normal indexing cost.
  The open item is that **no average source size or measured scan cadence exists
  yet** — the architecture defers cadence ratification to execution planning,
  which is correct. Severity: low (measurement gap, not an obstacle).
- **`IN_Q_OVERFLOW` confirms a real gap.** Today's `watch.py` uses the high-level
  `watchdog.Observer` + `FileSystemEventHandler` (with a debounce scheduler and
  an **unbounded in-memory `_batch` list** that the handler appends to on every
  event). I traced the installed watchdog (`inotify.py`, `inotify_buffer.py`,
  `inotify_c.py`):
  - `IN_Q_OVERFLOW = 0x00004000` is **defined** in `inotify_c.py:53` but is
    referenced **nowhere else** in the package.
  - `InotifyEvent` exposes accessors (`is_modify`, `is_close_write`, `is_create`,
    ..., `is_ignored`, `is_delete_self`) but **no `is_overflow`** accessor.
  - `InotifyBuffer.run()` filters events only by `is_ignored`/`is_delete_self`;
    it does not test for overflow, and an `IN_Q_OVERFLOW` event (wd=-1,
    mask=0x4000, name=b'') would match **no** `is_*` accessor and be effectively
    dropped/silently swallowed before reaching any handler.
  - `watch.py`'s own handler records only `event.src_path`; even a distinguishable
    overflow event would be invisible to its logic.
  - **Conclusion:** the architecture's hedge "If the watch library cannot expose
    a trustworthy overflow signal, observer failure/restart marks the watched
    scope reconciliation-required" is accurate — but the observer does **not**
    fail or restart on overflow (the low-level event is swallowed), so the hedge
    does **not** automatically fire. The §13.9 forced-overflow gate therefore
    cannot be satisfied through the current watchdog stack; it needs either a
    raw inotify reader/`IN_Q_OVERFLOW` check, or to rely on the mandatory
    periodic reconciliation (which is present in §7.1) as the convergence proof
    with overflow detected indirectly (mismatch vs recorded observation). This
    is a concrete evidence-gap item to resolve before the §13.9 gate closes.
- **`watch.py` today has no reconciliation/startup-scan/periodic logic at all**
  (grep confirms zero references). Everything §7.1 adds — startup scan, overflow
  mark, periodic cadence, manifest-vs-observation compare — is net-new. That is
  expected (the architecture does not claim it exists), but it means the §13.9
  gate is entirely forward work and should be timeboxed in execution planning.

**Verdict per area 4:** PASS WITH RISK. Cost feasible; overflow-detection
mechanism must be made concrete, not left to the watchdog hedge.

### 2.5 Review area 5 — Retained-generation lifetime and GC (§10) crash evidence

**Finding: the invariant is structurally guaranteed by COW, and the promotion-window faults are tested, but no single crash test asserts the combined active+previous-survive invariant.**

- **COW gives retention by construction.** `file_generation_store.py` `stage_rows`
  only ever `col.upsert(...)` — **no delete on promote**. Promotion to N+1 uses
  different copy-on-write physical IDs (`fg1_<sha256(collection+generation+logical)>`),
  so it cannot overwrite N's rows. Previous-generation rows remain physically
  present until an explicit GC (disabled by §10.1). This is the strongest
  grounding the architecture inherits, and `test_file_shrink_and_valid_empty_...`
  asserts exactly that the N, N+1, N+2 physical IDs are all retained after
  successive active changes (no crash).
- **What the crash suite covers (verified in source):**
  - `test_process_crash_recovery_and_bar_p_claims_are_separate` — real `os._exit`
    (SIGKILL-equivalent) mid-staging; reopen proves WAL replay recovery.
  - `test_known_queue_vector_replay_tail_recovers_exact_expected_set` — real
    `os._exit` after staging a large tail; proves the queue is the durable tail
    and reopen replays returning only the active generation.
  - `test_process_death_after_partial_candidate_never_changes_serving_generation`
    — real `os._exit` after staging a partial N+1; old N still serves, partial row
    inert.
  - `test_postpublication_failure_requires_exact_durable_republish` — simulated
    directory-fsync fault after pointer bytes visible; proves bytes are
    unqualified (`may_serve=False`) and recovery re-mints via exact qualification.
  - `test_recovery_does_not_guess_when_manifest_or_rows_fail` — qualification/
    hash-mismatch recovery refuses.
  - These cover §11's "crash after pointer bytes, before success" and
    "pointer/manifest mismatch → quarantine" rows.
- **The gap (named, medium):** the *crash* tests kill the process **at staging**,
  while the *promotion-window* tests use **simulated exceptions** (patched
  `atomic_write_json`, `PostPublicationDurabilityError`). **No test kills the
  process during the actual `publish_active_pointer()` promotion sequence and
  then asserts both active AND immediate-previous generations are physically
  intact and searchable.** The retention is structurally guaranteed, so this is
  unlikely to be a real invariant break — but §13.11 ("Pointer/fence/source-path
  crash injection passes every transition") does not currently have a test that
  injects a crash at the publish step and checks physical retention of
  active+previous. This is a concrete test to add in the §13.11 gate and a
  candidate for the formal model's "GC never selects an active/protected/pinned
  generation" property.
- **§10.3 pin-before-dereference consistency:** the architecture's protocol
  (tentative resolve → pin → revalidate → retry → dereference rows only after
  valid pin) is consistent with what CG-1 proved about Chroma durability: rows
  are read exactly (cold validation) and the store snapshots one active map per
  read (`_get_rows` reads fail closed per owner→generation pair from a single
  snapshotted view, §G4b). The pin work is future software, so "consistency with
  what CG-1 proved" is best stated as: **CG-1 provides the exact-read and
  fail-closed primitives the pin protocol depends on; the pin itself is not yet
  implemented or crash-tested, which §10.3 correctly defers to a later sub-gate.**

**Verdict per area 5:** PASS WITH RISK. Retention is structurally guaranteed;
add a promotion-time crash+retention test and pin-protocol crash coverage to
satisfy §13.11/§10.3 before online GC.

### 2.6 Review area 6 — Cross-reference with CG-1 closure (G4b)

**Finding: the G4b findings are acknowledged and the durability claim is inherited correctly.**

- **All G4b/activation blockers have a home in the architecture.** The CG-1
  closure (`CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md`) recorded five
  activation blockers. In the architecture: (1) doctor raw-ID drift → §3 + §9.2
  generation-aware drift; (2) `projection_parity` physical-ID preference → §3 +
  §9.1 namespaced identity (`ledger_id` semantic key, `row["id"]` deprecated for
  file rows); (3) semantic-review queue growth from physical-pair uniqueness →
  §10.2 admission control; (4) legacy path aliases → §8 decision (explicit owner
  migration; alias ambiguity blocks canary); (5) direct read bypasses → §3
  inventory + §13.3 (four classifications to zero) + §9.4 fitness gates. No G4b
  finding is silently dropped.
- **CG-1 durability claim (§2 item 13) is inherited correctly.** The architecture
  says "CG-1's measured durability bar covers process-crash recovery and its
  documented SQLite/Chroma behavior; it does not claim full power-loss
  durability." This matches the dependability handoff's Bar-P contract exactly:
  `synchronous=FULL`, `journal_mode=DELETE`, fsync-at-commit measured via the
  LD_PRELOAD shim, **no post-unlink directory fsync** (residual power-loss risk
  explicitly NOT claimed). §11's "Machine crash/power loss → Preserve CG-1
  durability claim; restart qualification fails closed if rows do not match
  pointer" is the correct, minimal restatement — it preserves the process-crash
  guarantee and fails closed on anything beyond it. This is a faithful inheritance,
  not an over-claim. The one nuance to keep visible: the residual power-loss risk
  is a real, documented gap that must never be read as "durable enough"; the
  architecture's phrasing keeps the risk honest.
- **A G4b-adjacent item the architecture could name more prominently (low):** the
  `test_all_direct_chroma_read_boundaries_are_explicitly_classified` harness note —
  the read-boundary inventory returns empty under dot-prefixed absolute paths
  (`~/.local/...`). §13.4 says the boundary must work from normal, `/tmp`, and
  hidden-parent worktree paths and that "the CG-1 hidden-parent discovery weakness
  is fixed." Good. But the current harness **fails empty (silently passes) rather
  than failing loudly** on a hidden parent. A silent-empty inventory would understate
  bypasses. Worth the execution plan asserting the inventory test *must* assert it
  discovered at least the four known constructors (not just zero violations), so an
  empty-discovery regression cannot look like a clean pass.

**Verdict per area 6:** PASS.

---

## 3. New failure modes / evidence gaps discovered (summary)

| # | Item | Severity | Section | Disposition needed before canary |
|---|------|----------|---------|-----------------------------------|
| N1 | `query.py` broad `except Exception` fallback is an unmediated (authority-bypassing) serving read; mechanism to prevent a generation-authority failure routing there is unnamed | Medium | §5.3 / §13.3 | Name/design the guard (or explicit exclusion list) so the fallback cannot serve on authority/pointer/manifest/fence failure |
| N2 | Watchdog cannot surface `IN_Q_OVERFLOW`; observer neither fails nor restarts on overflow, so the §7.1 hedge does not auto-fire | Medium | §7.1 / §13.9 | Concrete overflow detection (raw inotify reader or rely on periodic reconcile-as-convergence-proof); timebox |
| N3 | No crash test asserts active+previous retention across one real kill during `publish_active_pointer()`; retry lacks a terminator (livelock) | Medium | §10.1/§2.7 + §13.11; §5.1 + §13.10 | Add promotion-time crash+retention test; bind resolution retries to a measured cap with observable refusal |
| N4 | Reconciliation scan cost unmeasured (no avg source size / ratified cadence) | Low | §7.1 / §13.17 | Measure hashing cost and ratify cadence in execution planning |
| N5 | Read-boundary inventory can silently return empty on a hidden parent (harness note) rather than failing loudly | Low | §13.4 | Assert inventory discovers the four known constructors, not merely zero violations |
| N6 | `#7463` is external (macOS) evidence; local Linux behavior remains empirically ungated until the §13.15 tests run | Low | §13 / §15 | Not a defect; the §13.15 pinned-1.5.9 tests (partially pre-existing) are the gate |

---

## 4. What I checked vs. what I could not verify

**Checked (evidence-based):**
- `query.py` broad fallback at ~428 and ~523; `_fallback_query_rows` applies no
  owner/fence/authority filter (confirmed raw `collection_metadata_rows` read).
- `watch.py`: uses watchdog `Observer`; no overflow handling, no reconciliation/
  startup-scan/periodic logic (grep: zero). Handler records only `src_path` into an
  unbounded list.
- Installed watchdog source: `IN_Q_OVERFLOW` defined but unreferenced except the
  constant; no `is_overflow` accessor; buffer drops overflow without surfacing.
- `file_generation_store.py`: promote is `upsert`-only (no delete-on-promote) →
  COW retention by construction; `_assert_owner_budget` enforces the one-
  abandoned-generation guard.
- CG-1 test suite: durability (SIGKILL replay), faults (partial-candidate inert),
  pointer post-publication fault + recovery-no-guess, shrink/empty-retention —
  all read directly from source.
- Chroma `#7463` + PR `#7469` via upstream issue/PR (reporter's explicit
  "not a data-loss report"; replay-cost + missing flush primitive).
- Tier-L closure (`STATUS-chroma-reconcile-tier-l.md`, FLASH closeout): orphan
  parity tier S; distinct inconsistency axis from `#7463`.
- Corpus scale for §7.1 cost: 21k units / 2591 summaries / 1363 indexed sources
  from `convmem brief` (2026-08-15).

**Could not verify (noted as limits, out of scope per handoff):**
- That the `query.py` broad-exception fallback is actually reachable in a way
  that would cross a generation-authority boundary **today** — today there is no
  generational authority in production (CG-1 is hermetic, zero production
  callers confirmed in G4b), so the fallback cannot currently mis-serve a
  generation. The risk is *future*, at first cutover.
- Whether watchdog's C-extension `Inotify` binds `IN_Q_OVERFLOW` into the raw
  read (the `.pyc` matches the constant) — the analysis holds regardless because
  `InotifyEvent`/`InotifyBuffer` provide no overflow accessor or propagation path.
- Live running of the CG-1 suite or the acceptance packet on `1222b1e` — this is
  a read-only evidence review; no code was changed or executed beyond reading
  sources.
- The exact memory/CPU micro-budget of reconciliation at a specific cadence —
  requires the ratified cadence the architecture defers to execution planning.
- The formal model (§13.18) content and the Cursor feasibility review outcomes —
  both separate lanes.

**Read-only:** No implementation, no tests added, no files modified beyond this
review artifact. Deliverable produced per the handoff's file path and format.

---

## 5. SHA confirmation

This verdict — **PASS WITH RISKS** — applies solely and exactly to
`1222b1ede2d6cc5da582388768f06d60b36c5e50` on
`plan/2026-08-14-cg2-production-activation`. If the architecture bytes change,
this review must be re-run against the new revision; the named risks (N1–N3,
especially) must be reconciled in the §13 evidence packet before canary.

---
**TL;DR:** PASS WITH RISKS on the six areas — #7463 characterization accurate,
fail-safe table honest, GC/retention structurally sound. Three medium gaps to
close before canary: the `query.py` unmediated fallback lacks a named guard, the
watchdog watcher cannot surface `IN_Q_OVERFLOW`, and no crash test asserts the
active+previous invariant across a real promotion kill (plus an unbounded
linearization retry). Low-severity measurement/inventory notes also recorded.
