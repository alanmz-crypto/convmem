# Documentation Handoff: [Arc Project-state reconciliation only] Landed closeout

**Date:** 2026-08-30
**Author:** Codex (forensic reconciliation/documentation lane)
**For:** Ryan (review and PR decision)
**Authorization:** Ryan, 2026-08-30 (bounded project-state reconciliation handoff)

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `LANDED / CLOSED` |
| **Branch** | `docs/2026-08-30-project-state-reconciliation-handoff` (closeout carrier) |
| **Corrective SHA** | `ad9a9b6a039768c85b704f2bf17034c2605d63fa` |
| **Landing SHA** | `a924d3887329dd51f1e0ac917f8ab21bae513c57` on `main` |
| **Push status** | Corrective squash-merged; this handoff is the documentation-only closeout carrier |
| **PR** | Corrective PR #253 squash-merged; closeout carrier is separate |
| **Ryan GATE** | Squash-merge the closeout PR after ordinary checks; no technical or operational gate is opened |
| **Track A ingest** | `/home/lauer/.codex/sessions/2026/08/30/rollout-2026-08-30T02-31-26-01a05194-9300-7c70-90df-f4b6886a8fed.jsonl` — index nudged; active-file change caused a safe skip, and watch will retry after debounce |

## What changed

ConvMem's canonical project-routing surfaces now agree with live GitHub state at
`origin/main` `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d`.

**Why this exists:** stale canonical claims routed agents toward already-landed
work and blurred the boundary between mainline, branch-only implementation,
review state, and operational authority.

The corrective records:

- Recovery Authority T1–T3 landed; T3 remains scratch-only/non-serving, T4 is
  unauthorized, and V4k remains blocked.
- CG-2 Design A Execute-close landed via PR #250; production D0/D1, activation,
  V8c, pointer/fence publication, GC, Shadow, and R2b remain unauthorized.
- R2b I1–I3 remains branch-only in draft PR #252 at unreviewed Corrective V
  `20d7f567184500c33c9c82eb0d1c4d90fe6bc5f2`, with required Pylint failing.
  Draft PRs #246/#248/#249/#251 are superseded but preserved.
- Naturalistic product-value architecture, execution, and G1–G4 are branch-only;
  no study execution or product conclusion is authorized.
- Portland Protocol-v3 ended in seed-generation failure; no retry or Agent B
  execution is authorized, and pre-v3 evidence remains preserved.
- Watch OOM isolation, relocation retrieval scoping, and writer-attestation
  hardening are landed/closed rather than active routes.

## Changed files

| What | Path |
|------|------|
| Cross-arc current-state snapshot | `docs/inter-model/STATUS.md` |
| Current routing pointer | `docs/inter-model/LATEST.md` |
| Recovery Authority current-state brief | `docs/plans/STATUS-recovery-authority.md` |
| R2b current-state and supersession brief | `docs/plans/STATUS-r2b-capture-auth.md` |

## Explicit non-changes

- No runtime, test, formal-model, architecture, execution-plan, VERIFY, config,
  generated-protocol, or experiment-artifact change.
- No production execution, restore, activation, serving, or external mutation.
- No implementation, review, merge, packet, duration, capture, or operational grant.
- No deletion, collapse, or repurposing of superseded provenance.
- No PR was opened.

## Verification

- `convmem doctor` — PASS with four pre-existing/non-fatal warnings.
- Live GitHub recheck — `origin/main`, all five open draft PRs, PR #252 head and
  checks, Naturalistic G4, and Portland tips confirmed after editing.
- `git diff --check origin/main...HEAD` — PASS.
- `pytest -q tests/test_brief.py` — 16 PASS; sandbox-only pytest-cache warning.
- Changed-file inventory — exactly the four Markdown files above.
- No dedicated generated/status-surface consistency test exists.

## Residual ambiguity

`NONE` requiring adjudication. PR #252's body still names older frozen
coordinates, but its live head/check state is unambiguous and the drift is
explicitly documented in the corrected status surfaces.

## What NOT to do

- Do not use this reconciliation as production, implementation, review, merge,
  or activation authority.
- Do not reopen completed Recovery T3, CG-2 Execute-close, watch OOM, relocation,
  or writer-attestation work.
- Do not merge or delete preserved R2b candidates as part of this docs PR.
- Do not advance R2b, CG-2 reference-v2, Naturalistic methodology, Portland,
  or broader documentation modernization from this handoff.

## Recommended next action

Squash-merge the documentation-only closeout PR after required checks pass.
No implementation, experiment, production, or activation work follows from it.

## Leaving / picking up checklist

**Author (leaving):**

- [x] Corrective squash-merged via PR #253 at `a924d388`
- [x] Handoff created
- [x] `LATEST.md` points to this handoff
- [x] Verification completed against live GitHub state
- [x] No authority-expanding language introduced

**Ryan (picking up):**

- [ ] Squash-merge the closeout PR after ordinary checks
- [ ] Treat the reconciliation arc as closed; merge does not activate anything

**TL;DR:** **[Arc Project-state reconciliation only]** The documentation-only
correction at `ad9a9b6` squash-merged via PR #253 as `a924d388`; this closeout
preserves the handoff and opens no implementation, production, or activation
authority.
