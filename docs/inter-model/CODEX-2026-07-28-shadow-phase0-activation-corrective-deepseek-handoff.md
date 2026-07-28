# Codex → DeepSeek V4-Pro: review Shadow Phase 0 activation corrective plan

**Who:** Codex authored the corrective plan; DeepSeek V4-Pro is the independent
technical reviewer; Ryan owns plan acceptance, implementation authorization,
performance budgets, and every live activation decision.
**What:** Review the planning-only Shadow Phase 0 activation corrective plan at
commit bfceb65b6a07a4d2183085d1bac0c22f23b97055 and return a written PASS or
FAIL with concrete blockers and residual risks.
**When:** 2026-07-28, after Codex reproduced the activation-validation and
first-write privacy failures against main revision
83b8c11683c1295579c4fad9c8316f9f8fc3d10f.
**Why:** The current activation verdict is HOLD / NOT READY. Ryan wants the
corrective plan reviewed before any bounded implementation slice is sent to
Cursor.
**How:** Read the entire plan, verify its claims against the named repository
revision, stress-test the proposed invariants and slice boundaries, and return
the required review format below. Do not implement, activate, or edit live
state.

## Exact review target

| Field | Value |
|---|---|
| Plan branch | plan/2026-07-28-shadow-phase0-activation-corrective |
| Plan commit | bfceb65b6a07a4d2183085d1bac0c22f23b97055 |
| Reviewed main revision | 83b8c11683c1295579c4fad9c8316f9f8fc3d10f |
| Phase 0 merge on main | 4535107143279c87e8b34c1eab7e4dee88bffc68 |
| Primary artifact | docs/plans/EXECUTION-shadow-phase0-activation-corrective.md |
| Current activation verdict | HOLD / NOT READY |
| Shadow live state | Disabled |

This handoff may be committed after bfceb65. The review subject is the plan file
as introduced by bfceb65; the later handoff-only commit does not alter that
subject.

## What Codex verified

1. The focused Shadow suite still passes:

       pytest -q tests/test_shadow_ledger_phase0_t*.py \
         tests/test_shadow_writer_coverage_scan.py
       61 passed

2. No Shadow activation CLI or script exists.
3. Factory validation checks only enabled state, configured/caller root, shallow
   manifest completeness, and manifest root.
4. A temporary malformed fixture containing unsupported versions, negative
   counts/sequence, wrong revision, mismatched ledger identity, and a corrupt
   ledger was still accepted:

       {"malformed_manifest_corrupt_ledger_inject": true}

5. Under umask 022 with an injected first-fsync failure, a payload-bearing
   ledger remained mode 0644:

       {"first_fsync_failure_mode": "0o644", "payload_present": true}

6. Append scans the complete ledger for duplicate-event detection and again for
   sequence allocation. Its latency field is calculated before synchronous
   health-sidecar persistence.
7. Doctor and inventory derive health independently and can misstate invalid,
   missing, empty, active/historical, and Chroma-only conditions.
8. No live config, Chroma data, Shadow artifact, ledger, manifest, health file,
   backup setting, or production state was changed.

These findings are authoritative input to the plan review. Reproduce or inspect
them as needed, but do not reinterpret the passing 61 tests as activation
approval.

## Read first

1. docs/plans/EXECUTION-shadow-phase0-activation-corrective.md — entire file.
2. docs/plans/ARCHITECTURE-shadow-ledger-phase0.md — especially the eleven
   locked decisions, activation baseline, failure model, and readiness claims.
3. docs/plans/PHASE0-SHADOW-CONTRACT.md.
4. docs/plans/VERIFY-shadow-ledger-phase0.md — understand what the original
   61-test evidence does and does not prove.
5. docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.md.
6. Relevant code: shadow_ledger.py, shadow_sink.py, chroma_write_store.py,
   shadow_inventory.py, doctor.py, chroma_readonly.py, chroma_store.py, and the
   factory caller inventory.
7. Builder guidance if needed:
   docs/builder-reference/ousterhout-builder-digest.md,
   hard-parts-builder-digest.md, ddia-builder-digest.md,
   arch-patterns-python-builder-digest.md, and
   evolutionary-architectures-builder-digest.md.

## Review posture

You are an independent plan reviewer, not an implementing lane.

- Do not edit code, tests, configuration, or the plan.
- Do not enable Shadow or create live activation artifacts.
- Do not mutate live Chroma, JSONL authority, manifests, ledgers, health
  sidecars, backups, timers, or production settings.
- Do not expand into historic rebuild, Chroma redesign, authority transfer,
  canonical schema, later Shadow phases, or backup-policy work.
- Do not fill missing latency numbers with invented thresholds.
- Do not send an implementation slice to Cursor.
- If repository access is read-only, that is sufficient; return the review in
  chat or a review document only if Ryan separately asks for one.

## Required review questions

### A. Activation transaction and write-gap proof

1. Does a shared writer lease acquired before live config load and held through
   store close, paired with an exclusive activation lease, mechanically prevent
   both old-session and stale-config write gaps?
2. Does the plan account for every current production writer and for legacy
   processes running code without the new gate?
3. Is config-last atomic replacement a sound commit point when ledger and
   manifest installation are separate renames?
4. Can every crash point be classified without trusting a stale journal?
5. Are prepare, abort, resume, first-event verification, and rollback outcomes
   unambiguous and non-destructive to Chroma?
6. Is holding one guarded invocation through human commit authorization
   operationally credible, or does the plan need a different authorization
   mechanism?

### B. Shared validation contract

1. Is one ShadowValidationResult deep enough to serve writer factory,
   preparation, doctor, inventory, and verification without mode-dependent
   semantic drift?
2. Are all required refusal codes mechanically testable and correctly separated?
3. Does writer-mode validation prove enough without incorrectly comparing an
   old baseline against naturally evolved Chroma?
4. Does full ledger validation once per write session create a new scaling
   blocker that the plan must resolve before implementation?
5. Are collection UUID, code revision, config/manifest SHA, activation ID,
   ledger header identity, baseline digest, and sequence bindings sufficient?
6. Are there missing downgrade/upgrade, tamper, hardlink, or TOCTOU cases?

### C. Secure creation and filesystem policy

1. Does descriptor-relative O_EXCL/O_NOFOLLOW creation plus fchmod/fstat prove
   0600 privacy before byte one under all listed umasks?
2. Is a non-payload ledger header the right first durable record and is its
   identity binding crash-safe?
3. Are short write, fsync uncertainty, directory fsync, existing-file recovery,
   link count, owner, type, symlink component, inode swap, and cleanup rules
   complete?
4. Is the open decision about a 0700 parent versus a private subdirectory
   sufficiently bounded, and what exact policy do you recommend?
5. Can any artifact path alias or replace Chroma, config, another Shadow
   artifact, or an ancestor through a race the plan misses?

### D. Doctor, inventory, and rollback truth

1. Do the proposed state-to-verdict mappings eliminate false green without
   turning disabled mode into a false failure?
2. Are active, historical, total, baseline, touched, and Chroma-only counts
   defined consistently?
3. Should prepared_not_committed be WARN or FAIL while config remains disabled?
4. Are enabled validation failure and first-event timeout rollback rules
   appropriately strict?
5. Does rollback preserve Chroma success and accurately record an uncaptured
   Shadow gap without pretending the baseline can be reused?

### E. Performance canary and thresholds

1. Does the timer include the complete synchronous append and health path?
2. Are event-size, ledger-volume, concurrency, warm-up, run count, percentile,
   cold-open, and disabled-versus-enabled comparisons adequate?
3. Is the workload representative without reading production payloads?
4. Are the symbolic Ryan-owned thresholds a valid plan gate, or do any values
   need to be resolved before the plan can honestly be called ready for
   implementation review?
5. Are immediate failure and live rollback conditions deterministic enough?
6. Does eliminating duplicate suppression and using bounded-tail sequence
   allocation preserve the locked duplicate/replay contract?

### F. Scope and implementation slices

1. Do C1-C6 have coherent prerequisites, allowed/prohibited files, rollback,
   evidence, and merge-while-disabled rules?
2. Is the order correct, especially C1 validation, C2 secure append, C3 writer
   gate, C4 truth surfaces, C5 activation, and C6 canary?
3. Are any slices too broad or coupled to merge safely while disabled?
4. Does any proposal weaken the properties that already passed?
5. Are necessary activation corrections cleanly separated from optional future
   optimizations and later Shadow phases?

## Repository checks

Use a separate read-only checkout/worktree if possible. Name the exact SHA you
review.

    git fetch origin
    git switch plan/2026-07-28-shadow-phase0-activation-corrective
    git rev-parse HEAD
    git show bfceb65:docs/plans/EXECUTION-shadow-phase0-activation-corrective.md
    git diff --check origin/main...bfceb65
    pytest -q tests/test_shadow_ledger_phase0_t*.py \
      tests/test_shadow_writer_coverage_scan.py
    convmem doctor

The full pytest suite is optional for this plan-only review. If run, label it
supplementary; the plan file is the artifact under review.

## Required output

### 1. Verdict

    SHADOW ACTIVATION CORRECTIVE PLAN REVIEW
    Plan commit: bfceb65b6a07a4d2183085d1bac0c22f23b97055
    Verdict: PASS | FAIL
    Confidence: high | medium | low
    One-line rationale: ...

PASS means the plan is ready for Ryan/Kiro implementation review, not that
Shadow may be activated or that Cursor may start without authorization.

### 2. Findings

Provide findings ordered by severity:

- BLOCKER — must change before plan approval.
- HIGH — must be assigned to a slice/gate before implementation.
- MEDIUM — should improve the plan or acceptance evidence.
- LOW — optional clarity or future hardening.

For each finding include:

1. exact plan section or source symbol;
2. failure scenario;
3. violated invariant;
4. smallest corrective plan edit;
5. whether it changes slice ordering or open decisions.

Say “No findings” explicitly for an empty severity level.

### 3. Question-by-question disposition

Answer sections A-F with PASS, FAIL, or NEEDS DECISION and one evidence-based
sentence per question group. Do not use generic “looks good.”

### 4. Open-decision recommendations

Recommend:

- private parent-directory policy;
- first-event timeout behavior;
- authorization mechanism while the exclusive gate is held;
- whether prepared_not_committed is WARN or FAIL while disabled;
- whether cold writer-session full-ledger validation is acceptable;
- what measurements Ryan should see before approving numeric latency budgets.

Do not invent the numeric budgets.

### 5. Slice and approval conclusion

State:

- whether C1 may be authorized after Ryan/Kiro review;
- which later slices remain blocked by open decisions;
- whether any proposed correction should be moved between slices;
- whether targeted Copilot safety/isolation audit remains warranted;
- confirmation that live activation remains forbidden.

### 6. Final line

End with exactly one:

    DEEPSEEK PLAN REVIEW: PASS — ready for Ryan/Kiro implementation review

or:

    DEEPSEEK PLAN REVIEW: FAIL — plan corrections required before implementation review

Then add the mandatory response TL;DR.

## After DeepSeek returns

| Actor | Next action |
|---|---|
| Ryan | Reviews DeepSeek findings and decides whether Codex revises the plan. |
| Codex | Revises planning documents only if Ryan requests; no implementation. |
| Kiro | Performs the chartered design review on the exact accepted plan revision. |
| Cursor | Remains idle until Ryan authorizes one bounded implementation slice. |
| Copilot audit lane | Performs targeted safety/isolation audit only when assigned on an exact implementation revision. |

No DeepSeek PASS changes HOLD / NOT READY for live activation.

## TL;DR

DeepSeek reviews the corrective plan at bfceb65 for transaction correctness,
strict validation, first-byte privacy, truthful status, performance gates, and
bounded slices. The task is review-only; Shadow remains disabled, Cursor remains
idle, and Ryan owns every implementation and activation decision.
