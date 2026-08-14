# CG-1 Closure Gate G4b — GAP closed + independent review PASS

**Date:** 2026-08-13
**Author:** Crush (independent reviewer, convmem lane)
**For:** Ryan (acceptance) and the CG-1 reviewers (Sol / Kiro / ChatGPT)
**Relates to:** `HANDOFF-CG1-DEPENDABILITY-2026-08-10.md` → `CHATGPT-2026-08-10-cg1-closure-gate-g4a.md`
**Reviewed bytes:** stabilization SHA `2ed229244ea1d7cdf9a83630ad56d5a194426826`

---

## Summary

The G4a material GAP (cold-validation binding to promotion) is **structurally
closed** at reviewed SHA `2ed229244ea1d7cdf9a83630ad56d5a194426826`. Independent
review of the delta `7a35dbf..2ed2292` declared **PASS**. This packet re-points
the closure equation to the new stabilization SHA and records that the final
independent-audit step of Sol's mandated correction loop is complete.

## Why this packet exists

The G4a packet (`CHATGPT-2026-08-10-cg1-closure-gate-g4a.md`) froze the tested
bytes at `7ac88cb3…` and left the closure equation unsatisfied:

```
tested bytes       = 7ac88cb3…
reviewed bytes     = NONE
accepted bytes     = NONE
pushed bytes       = 7a35dbf… (does not include stabilization)
```

Since then the branch advanced (and was recovered after a git incident) to a
new tip `2ed2292…`, which contains the GAP correction. Per Sol's mandated
correction loop — minimum correction → targeted tests → Ruff → full suite →
new stabilization SHA → new Sol packet → new independent audit — the final
independent-audit step is now done here. This packet is the new-Sol-packet
bookkeeping re-pointed to `2ed2292…`.

## CG-1 worktree reconciliation table (Pass 3 entry ticket)

**Recorded:** 2026-08-13 (Cursor, read-only audit). **Merge classification rule:**
`git diff --stat origin/main <tip>` — zero output ⇒ `MERGED_CONTENT_EQUIVALENT`.

| Worktree / path | HEAD | SHA on remote | Content-equivalent to `origin/main` | Restore reports salvaged | Closure doc corrected |
|-----------------|------|---------------|---------------------------------------|--------------------------|------------------------|
| `~/.local/share/convmem/worktrees/feat-2026-08-10-cg1-recovery` | — | — | — | — | **N/A — path removed in worktree Pass 1 (2026-08-13); do not recreate unless a new doc contract requires it** |
| `/tmp/convmem-cg1-lint` | `2ed2292…` (removed 2026-08-13) | **yes** | **yes** (`MERGED_CONTENT_EQUIVALENT`) | **yes** — `restore-f090683bc4f4.{json,md}` → `~/Projects/convmem/complete-data-restore-reports/` | **yes** |
| `/tmp/convmem-cg1-verify` | `2ed2292…` (removed 2026-08-13) | **yes** | **yes** (same) | **yes** — `restore-54ecff7733c3.{json,md}` → same dir | **yes** |

**Tracked modifications on `/tmp/convmem-cg1-lint` (classify before removal):**

| Path | Classification |
|------|----------------|
| `file_generation_pointer.py` | Workspace-local drift — matches post-merge delta vs `origin/main` at `2ed2292`; **not** authoritative over `origin/main` |
| `tests/test_file_generation_pointer.py` | Same — test adjustments aligned with main's merged CG-1 tree, not unique evidence |

**PR #172:** squash-merged to `origin/main` as `e2f8b0f40a7473cd4adc73c7c2b77749b830eb83` (2026-08-14). Stabilization SHA `2ed2292…` remains the **reviewed-bytes** anchor for G4b; production canonical is `origin/main` post-merge.

## Frozen artifact state (updated)

| Field | Value |
|-------|-------|
| Stabilization SHA | `2ed229244ea1d7cdf9a83630ad56d5a194426826` |
| Branch | `feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate` |
| Authoritative worktree | **None local** — `/tmp/convmem-cg1-*` worktrees **removed** after salvage (2026-08-13). Reviewed bytes remain at SHA `2ed2292…` on `origin/feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate`. Restore reports in `~/Projects/convmem/complete-data-restore-reports/`. |
| Baseline at review | `0be0a05b9984ba2b23b2f1dc1728904951560d96` |
| Reviewed delta | `7a35dbf0f5d081164ef2856ef4951f6b259878e8..2ed229244ea1d7cdf9a83630ad56d5a194426826` |
| Merge state | **PR #172 MERGED** → `origin/main` @ `e2f8b0f…` |

**Important:** `/tmp/convmem-cg1-delivery`, `feat-2026-08-10-cg1-recovery`, and `/tmp/convmem-cg1-*` are superseded/removed. Do not recreate unless a new doc contract requires it.

## The G4a GAP — closed

### What the GAP was

`publish_active_pointer()` accepted a caller-supplied `exact_generation_validator`
callback. A caller could supply `lambda manifest: True` and mint a
`QualifiedActivePointer` without any exact generation validation, violating the
locked `built → validated → durably promoted → serving` lifecycle.

### The correction (structural enforcement — Sol's interpretation 2)

Three commits implement the GAP fix and hang onto it with tests:

**`f194fd3` — "enforce fresh validation before generation authority"** (core fix):
- Removed the `exact_generation_validator` parameter from `publish_active_pointer`
  and `recover_active_pointer`. The vulnerable seam no longer exists.
- Added a module-private `_run_fresh_process_qualification()` that always invokes
  `run_cold_validation()` in a **new interpreter** on the hash-bound manifest,
  and cross-checks the child's returned `valid`, `owner_digest`, `generation_id`,
  and `manifest_sha256` against the caller-bound manifest.
- Sealed the serving token: `QualifiedActivePointer.__init__` raises `TypeError`;
  only the module-private `_make_qualified_active_pointer()` mints after the full
  authority sequence. `healthy_state`/`degraded_safe_state` enforce exact-type +
  seal.

**`2ed2292` — "bind generation authority to owner and manifest"** (hardening):
- `_reload_verified_caller_reference()` binds the caller-held manifest to its
  canonical persisted, hash-bound bytes (filename + resolved path + bytes). Called
  before choosing the lock/path and again under the owner lock.
- The store's `_get_rows` reads fail closed per-row on the exact owner→generation
  pair using a single snapshotted active view (no mixed-state reads).

**`7ac88cb` — "close committed-generation verification gaps"** (evidence):
- Added the negative cold-validation test (tampered bytes rejected in a fresh
  interpreter), a durability test tweak, and updated the shadow-writer coverage
  inventory. Additive evidence only; no production behavior change.

### Why no bypass remains

- `exact_generation_validator` appears nowhere in production source — only in a
  regression test asserting it is absent from both API signatures and that passing
  it raises `TypeError`.
- `candidate_revalidator` / `recovery_revalidator` (the drift hooks) cannot mint
  authority: they only reject `False`, and the mandatory fresh-process cold check
  runs regardless.
- `file_generation_pointer` is imported only by tests — zero production callers,
  so the signature change has no stale-caller regression. The mechanism is
  hermetic/opt-in as scoped.

## Key regression tests added (targeted-tests step)

- `test_public_authority_apis_have_no_fake_validator_seam` — asserts via
  `inspect.signature` that `exact_generation_validator` is absent from both APIs;
  passing `lambda manifest: True` raises `TypeError`.
- `test_direct_or_forged_token_cannot_claim_healthy_serving` — direct constructor
  raises `TypeError: sealed` (even with the real seal); forged tokens and subclasses
  fail `healthy_state`/`degraded_safe_state` with `module-sealed`.
- `test_private_fresh_qualification_binds_child_result_to_manifest` — guards the
  subprocess-result owner/gen/hash binding.
- `test_reused_active_generation_id_cannot_cross_owner_boundary` — the `2ed2292`
  cross-owner binding across query, exact-lookup, metadata, and count surfaces.
- `test_fresh_qualification_or_candidate_drift_refuses_promotion` — promotion is
  refused when cold qualification fails or drift is False.

## Independent verification (Crush, convmem lane)

Run from the exact reviewed bytes `2ed2292…`:

- **Full repository suite:** **1,284 passed, 230 subtests passed, 1 warning,
  0 failures** (independent re-run, ~9 min).
- **Focused CG-1 suite (11 files):** **58 passed**, including all GAP regression
  tests above.
- **Legacy ingest dedupe regression:** **7 passed**.
- **Static:** all CG-1 modules compile; `git diff --check` clean. (Ruff ran in
  Sol's environment; independent ruff not re-run here.)
- **Bypass hunt:** `exact_generation_validator` present only in tests as negative
  assertions; zero production callers of the pointer authority APIs.

**Harness note (not a defect):** one file's discovery test
(`test_all_direct_chroma_read_boundaries_are_explicitly_classified`) returns empty
when the repo lives under a dot-prefixed absolute path (e.g. `~/.local/…`, the
recovery worktree) because `_discover()` skips any path part starting with `.`.
Run the suite from a clean path (e.g. `/tmp/convmem-cg1-delivery` or a `/tmp`
copy) and it passes. Sol's original run used a `/tmp` worktree.

## Updated closure equation

```
tested bytes       = 2ed2292…  (1284 + 230 suite, 0 failures)
reviewed bytes     = 2ed2292…  (Crush G4b independent review: PASS)
accepted bytes     = PENDING   (Ryan GATE)
pushed bytes       = e2f8b0f…  (PR #172 squash-merged to origin/main)
```

CG-1 substrate is on `origin/main`. The reviewed stabilization SHA remains the
G4b audit anchor; `accepted` is still pending Ryan GATE. CG-2 activation remains
a separate grant.

## What is NOT done / not authorized

- Live activation of the mechanism (CG-2). Activation blockers remain in the
  PR #172 body.
- No production corpus or Chroma mutation.

## Next actions

1. **Ryan:** accept the review / GATE (if not already granted).
2. Later, CG-2 (activation) — separate grant.

---

## Appendix — Worktree cleanup **COMPLETE** (Cursor, 2026-08-13)

**Kiro verdict:** PASS on reconciliation table (`c34f2f2`). **Ryan authorized**
salvage + Batch 3; subsequent batches executed through plan completion.

| Metric | Value |
|--------|-------|
| Start | 92 worktrees |
| End | **7** (1 active checkout + 5 substantive + 1 decision-required) |
| Removed | 85 worktrees across Pass 1–2 and Batches 3–9 |
| `git branch -D` | **never used** (416 branches unchanged) |
| `--force` | **never used** |

### Remaining worktrees (intentional)

| Path | Branch | Status |
|------|--------|--------|
| `~/Projects/convmem` | active feature branch | writer checkout |
| `…/docs-2026-07-30-c7-c6-standing-check-readiness` | +89 commits | substantive / open PR candidate |
| `…/feat-2026-08-10-judgebench-live-driver` | +2 commits | substantive |
| `…/fix-2026-07-24-crush-bash-index-freeze` | +1 commit | substantive |
| `…/fix-2026-08-04-embedding-eval-gate1-hardening` | +43 commits | substantive |
| `…/fix-2026-08-07-judge-bench-judge-upgrades` | 8 dirty files | **DECISION_REQUIRED** — do not remove |
| `…/plan-2026-08-07-chroma-reconcile-revise` | +2 commits | substantive |

### Salvage archive (untracked in active checkout)

- `complete-data-restore-reports/` — restore-drill outputs including CG-1 pairs
- `docs/inter-model/debate-2026-07-15-who-fixes-retrieval/CODEX-top-two-problems-and-plans.md`
- `/tmp/convmem-salvage-plan-activation-corrective/EXECUTION-shadow-phase0-activation-corrective.patch`

### Out of scope (not part of cleanup plan)

- Local branch `wip/2026-07-15-codex-top-two-proxy` (no worktree; no remote) — push or explicit discard
- `fix/2026-08-07-judge-bench-judge-upgrades` dirty WIP — commit/PR or discard
