# Handoff: CG-2 Architecture — Resolve N1–N3 and Author Formal Model

**Date:** 2026-08-14
**Author:** Kiro (design review lane)
**For:** OpenAI Codex (architecture + formal model)
**Authorization:** Ryan, 2026-08-14 (verbal; resolve before lock is confirmed best path)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `plan/2026-08-14-cg2-production-activation` (tip `196826e`; architecture at `1222b1e`) |
| **Push status** | Pushed to origin |
| **PR** | Not opened |
| **Ryan GATE** | Architecture HITL lock after you deliver; reviewers quick-confirm delta |
| **Predecessor** | You authored the architecture and the advisory disposition pass at `1222b1e` |

---

## Context: where the review chain stands

You wrote the CG-2 architecture. Three lanes reviewed it at your exact SHA
`1222b1e`. All three passed:

| Lane | Verdict | Deliverable |
|------|---------|-------------|
| Kiro (design correctness) | PASS | Session Track A |
| Cursor (implementation feasibility) | PASS WITH RISKS | `CURSOR-2026-08-14-cg2-feasibility-review.md` @ `5eb7eac` |
| Crush (evidence/failure) | PASS WITH RISKS | `CRUSH-2026-08-14-cg2-evidence-review.md` @ `ded7bc2` |

No reviewer issued FAIL. No architecture revision is needed. But both
risk-bearing reviews converged on three gaps that must be closed **before**
Ryan locks the architecture and before you can write a complete formal model.

---

## What you need to do

Two deliverables, in order:

### Deliverable 1: Resolve N1–N3 as architecture addenda

Add small, precise mechanism descriptions to the existing architecture document.
These are not rewrites — they fill gaps the reviewers named. The architecture
already says the right things conceptually; you are naming the structural
mechanism that makes each claim implementable and model-checkable.

#### N1 — Name the fallback guard mechanism (§5.3 / §13.3)

**Problem:** `query.py` lines ~428 and ~523 catch broad `except Exception` and
fall through to `_fallback_query_rows`, which reads raw Chroma metadata with no
owner/fence/authority filtering. The architecture says authority failures must
fail closed (§5.3), but it doesn't name the structural mechanism that prevents
a generation-authority exception from reaching that fallback.

**What to write:** A §5.3 sub-section or table row that specifies how the
serving repository distinguishes authority/pointer/fence exceptions (which must
fail closed) from transient Chroma contention (which may fall back). Name
whether this is a typed-exception hierarchy, a repository-internal catch that
never propagates authority errors to the outer `except Exception`, or an
explicit reclassification of what `_fallback_query_rows` is allowed to serve
under generational mode.

**Cursor's finding to incorporate:** The additional serving-adjacent paths
beyond the four AST-classified sites (`open_chroma_for_read`, keyword fallback,
`chroma_readonly` SQLite walks) must also sit behind the same boundary or be
explicitly classified. The inventory's four sites are necessary but not
sufficient.

#### N2 — Specify the overflow-detection strategy (§7.1 / §13.9)

**Problem:** The architecture says "If the watch library cannot expose a
trustworthy overflow signal, observer failure/restart marks the watched scope
reconciliation-required." Crush traced the installed watchdog source and proved
that `IN_Q_OVERFLOW` is defined but never surfaced — the event is silently
swallowed by `InotifyBuffer`. The observer neither fails nor restarts on
overflow, so the hedge doesn't auto-fire.

**What to write:** A concrete strategy that doesn't depend on watchdog exposing
overflow. Options the reviewers identified:

- Raw inotify reader (bypasses watchdog for overflow detection only)
- Mandatory periodic reconciliation as the sole convergence proof (overflow
  detected indirectly by source/manifest mismatch)
- Observer restart on any interruption marks scope reconciliation-required
  (weaker but simpler)

Name which approach the architecture requires (or name a spike that decides).
The §13.9 forced-overflow gate needs to know what it's testing.

#### N3 — Bind the authority-resolution retry and specify termination (§5.1 / §13.10)

**Problem:** The seqlock-like read/verify/retry pattern has no named retry
limit. Under rapid pointer republication (batch promotion, rename migration),
the resolver could retry indefinitely — safe (fail-closed) but not converged.
A latency/backlog budget (§13.17) needs a bounded retry with a terminal state.

**What to write:** A §5.1 sub-bullet or paragraph that:

1. Names a measured retry cap (e.g., N attempts or T duration)
2. Specifies the terminal state on cap exhaustion (QUARANTINED? observable
   refusal? request-level error?)
3. Notes that the formal model must prove the retry terminates under the stated
   bound

Crush suggested ordering evidence reads (verify pointer last, since publication
is the final monotonic step) to minimize retries in practice.

#### Commit guidance

- Small delta on the plan branch (same branch you authored on)
- Each resolution can be a sentence to a paragraph — not a new section
- The new tip SHA becomes the lock candidate
- Push immediately after commit

---

### Deliverable 2: Bounded formal authority model (§13.18)

After N1–N3 are resolved, author the TLA+/PlusCal model (or equivalently
reviewable exhaustive transition model) that §13 item 18 requires. The model
must check at least these safety properties (from the architecture):

1. Only a qualified pointer target serves a generational owner
2. At most one generation serves per owner
3. An owner resolution linearized after the fence cannot resolve legacy
4. A pre-fence frozen reader may finish while retained legacy rows are protected
5. Active/source stale checks prevent promotion
6. Under a stated fair-reconciler assumption, lost notification state cannot
   remain the only record of source drift: reconciliation queues or quarantines
   an observed source/manifest mismatch
7. Recovery never changes pointer choice by completeness
8. GC never selects an active/protected/pinned generation
9. No target is reclaimed between tentative resolution and a validated pin
10. Rename migration never admits old and new owners to one newly resolved vector
11. One request never changes its frozen owner generation mid-request
12. **NEW (from N3):** Authority-resolution retry terminates within the stated
    bound and produces a terminal refusal on exhaustion

Place the model in a reviewable location (e.g., `docs/plans/` or a dedicated
`formal/` directory — your call on naming, but it must be on the plan branch
and pushed).

---

## What NOT to do

- **No implementation.** No `.py` changes, no test additions, no production
  config.
- **No execution plan.** That comes after Ryan locks.
- **No full architecture rewrite.** N1–N3 are addenda — a few paragraphs total.
- **No CG-1 changes.** CG-1 is merged and closed.
- **No other arcs** (JudgeBench, Shadow Ledger, etc.).
- **No activation, GC, or production grants.**

---

## After you deliver

1. Push the plan branch with N1–N3 resolved and the formal model committed.
2. Name the new tip SHA in your forward announcement.
3. Kiro, Crush, and Cursor quick-confirm the delta doesn't invalidate their
   existing PASS. (This is a delta check — the addenda are additive, not
   structural. Full re-review only if you change a state machine or invariant.)
4. Ryan Architecture HITL lock on the confirmed revision.
5. You then author the execution plan (separate grant, after lock).

---

## Review evidence to read

| What | Where |
|------|-------|
| Cursor feasibility review (full) | `git show 5eb7eac:docs/inter-model/CURSOR-2026-08-14-cg2-feasibility-review.md` |
| Crush evidence review (full) | `git show ded7bc2:docs/inter-model/CRUSH-2026-08-14-cg2-evidence-review.md` |
| Your architecture (current tip) | `git show 1222b1e:docs/plans/ARCHITECTURE-cg2-production-activation.md` |
| CG-1 substrate (on main) | `file_generation_pointer.py`, `file_generation_store.py`, etc. |
| Installed watchdog source (N2 trace) | Crush's §2.4 in the evidence review |
| `query.py` fallback (N1 evidence) | `query.py` lines ~425–435, ~520–530 |

---

## Acceptance criteria

- [ ] N1 resolved: fallback guard mechanism named in architecture; broader
      serving-path coverage acknowledged
- [ ] N2 resolved: overflow-detection strategy specified concretely (not
      dependent on watchdog hedge alone)
- [ ] N3 resolved: retry bound named; terminal state specified; formal model
      property listed
- [ ] Formal model authored and committed on the plan branch
- [ ] Model covers all 12 safety properties listed above
- [ ] Model is reviewable (TLA+/PlusCal with comments, or equivalent with
      explicit state space and invariant assertions)
- [ ] Plan branch pushed with new tip SHA
- [ ] Forward announcement with SHA, deliverable paths, and next lane

---

## Branch convention

Continue on `plan/2026-08-14-cg2-production-activation`. Push immediately after
each commit. The new tip SHA after your work is the Architecture HITL lock
candidate.

---

## Leaving checklist (Kiro, author)

- [x] This handoff committed and pushed
- [x] `LATEST.md` CG-2 bullet reflects review-complete state and next step
- [x] Both reviewer deliverables fetched and verified
- [ ] Codex notified (Ryan relays)
