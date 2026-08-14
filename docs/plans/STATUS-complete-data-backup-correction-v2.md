# Arc Brief — Complete-data Backup Correction v2

> Every model working on this arc must read this file at session start. After
> reading, state: “Goal: [one sentence]. My role: [what I’m here to do]. The
> system currently: [what exists]. Missing: [what doesn’t exist yet].”

## 1. What This Is For (product goal)

ConvMem must back up the complete ConvMem-owned data root rather than treating
the Chroma projection as the whole safety boundary. This arc makes that claim
honest and mechanically testable: one immutable `BackupContext`, an explicit
`complete-data-v2` profile, fallback-free snapshot selection, durable atomic
publication, capture evidence, and a closed restore-state matrix.

The correction is implemented and the v2 rollout is complete on `main`. The
remaining open work is the separately governed Hybrid consistency-bar audit;
that audit must not be confused with a new backup implementation or with
Universal Tier-1 writer coordination.

## 2. System Design (how the pieces connect)

```text
explicit env/profile
        │
        ▼
  BackupContext ──► restic_snapshot.py ──► tagged local snapshot (S)
        │                    │
        │                    └──────────► external lineage copy (D)
        ▼
 backup_workflows.py ──► health / ensure / copy / integrity / restore
        │
        ├── .convmem-backup-evidence.json (capture evidence, not authority)
        ├── atomic_files.py (durable JSON/JSONL publication)
        └── complete_data_restore.py (closed VALID/ADVISORY/REPAIRABLE/BLOCKED matrix)
```

The important invariants are:

- `complete-data-v2` requires an explicit data root and the exact
  `convmem-data-v2` tag; legacy Chroma-only and v1 snapshots never prove v2
  protection.
- Every safety workflow uses the shared Restic boundary and exact-path
  resolution; resolver failure never falls back to a newer or legacy snapshot.
- Local source identity `S` and external destination identity `D` are recorded
  separately; protection requires the documented lineage relationship.
- Capture evidence is compared during restore validation but is never a repair
  source or authority.
- Restore validators never repair, and unknown state blocks.
- Until the documented v2 rollout grants are complete, doctor must report
  `WARN_LEGACY_ONLY` rather than claim complete-data protection.

## 3. What Exists Right Now (file map)

### On `main` (merged and rolled out)

| File or area | What it does | State |
|---|---|---|
| `restic_snapshot.py` | `BackupContext`, profile, path safety, Restic boundary, resolution and lineage | Complete |
| `backup_workflows.py` | Shared ensure/copy/health/integrity/restore orchestration | Complete |
| `atomic_files.py` | Durable atomic publication with fsync and cleanup semantics | Complete |
| `complete_data_restore.py` | Closed restore matrix and evidence-aware validation | Complete |
| `restic_gate.py`, `doctor.py`, `observe.py` | Consumers routed through the corrected boundaries | Complete |
| `config/restic.env.example` and service/timer examples | Explicit v2 profile and data-root configuration | Complete |
| `tests/test_restic_*.py`, `tests/test_backup_workflows.py`, `tests/test_atomic_files.py`, `tests/test_complete_data_restore.py` | Hermetic, fault-injection and consumer-wide proof | Complete |
| `COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.{json,md}` | Hybrid audit inventory and writer census | Complete artifact; audit use remains separate |

### Planning and evidence references

| File | State |
|---|---|
| `ARCHITECTURE-complete-data-backup-correction-v2.md` | Historical locked direction; implementation landed as PR #125 |
| `EXECUTION-complete-data-backup-correction-v2.md` | Historical execution contract; stages T1–T5 completed |
| `VERIFY-complete-data-backup-correction-v2.md` | Verification contract/stub; exact-SHA evidence is the authority for review |
| `docs/inter-model/LATEST.md` | Records PR #125 and the four post-merge v2 rollout grants |
| `COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md` | Separate Hybrid consistency-bar audit contract |

### Does not exist yet / remains open

- A closed Hybrid Five-part consistency-bar audit and its owner disposition.
- Any Universal Tier-1 writer coordination or global quiescence proof; those
  were explicitly out of scope for this arc.
- Authorization for any new live repository, timer, restore, or policy change;
  the completed rollout is not a blanket grant for future operations.

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Corrective architecture/execution/VERIFY package | **DONE** (#124) | — |
| Fresh v2 implementation and hermetic proof | **DONE** (PR #125, `83b8c11`) | — |
| Post-merge v2 rollout: profile, local snapshot, external lineage, timers | **DONE** (2026-07-28) | — |
| Hybrid consistency-bar audit | **OPEN, separate track** | Copilot audit evidence and Ryan disposition |
| Any broader backup/restore redesign | **OUT OF SCOPE** | New architecture and Ryan grant |

**Summary:** The v2 correction and rollout are complete. The next model should
review or close the separate Hybrid audit, not re-run the rollout or invent a
new backup gate.

## 5. Your Role (read this to know what you’re here to do)

If you are reviewing readiness, compare the merged implementation and its exact
verification evidence with the Hybrid contract. Confirm that legacy false-green
paths remain impossible and that the v2 rollout claims are not expanded beyond
their evidence.

If you are working on the open audit, use the census and Copilot Hybrid bar as
the source of truth, record the audit disposition separately, and keep it
distinct from Shadow, JudgeBench, R2b capture, and production configuration.

If Ryan asks for a live backup, restore, timer, or policy change, stop at the
owner/grant boundary. This brief does not authorize an operational mutation.

If you do not know why you are here, read `docs/inter-model/LATEST.md` and ask
Ryan before changing code, live configuration, or backup state.

## 6. What Remains Before This Arc Is Fully Closed

- [ ] Complete the separate Hybrid Five-part consistency-bar audit.
- [ ] Record Ryan’s disposition for that audit without changing the v2 rollout
      claim.
- [ ] Keep future live backup, restore, timer, and policy changes under a new
      explicit grant and exact evidence package.

## 7. Hard Stops (models cannot cross)

- Do not edit or rehabilitate historical failed artifacts `492e6e7…` or
  `b6284ad…`.
- Do not restore legacy snapshot selection or catch resolver failures into
  PASS/SKIP behavior.
- Do not claim complete-data protection from `legacy-chroma`, `convmem-chroma`,
  or `convmem-data-v1` evidence.
- Do not activate Universal Tier-1 coordination, Shadow backup authority, or a
  new timer/configuration from this brief.
- Do not perform live Restic, repository, restore, or systemd changes without
  the named Ryan grant and a fresh evidence boundary.

## 8. Relationship to ConvMem (the bigger picture)

```text
ConvMem safety and evaluation landscape:
├── complete-data backup v2 (THIS ARC) — protects the durable data root
├── Chroma reconcile — rebuilds the searchable projection; separate arc
├── R2b capture — authorizes one corpus capture; separate Ryan gate
├── Shadow Ledger Phase 0 — disabled delta-capture path; separate activation gate
└── JudgeBench — semantic calibration over retrieved evidence; separate gold gate
```

The backup arc protects the source data and its recovery evidence. It does not
make Chroma authoritative over the ledger, authorize capture, enable Shadow, or
select a JudgeBench model.

## 9. Key Design Files (for deep dives)

| Purpose | Path | Read when |
|---|---|---|
| Architecture | `docs/plans/ARCHITECTURE-complete-data-backup-correction-v2.md` | Reviewing boundaries and invariants |
| Execution | `docs/plans/EXECUTION-complete-data-backup-correction-v2.md` | Reconstructing T1–T5 and grant boundaries |
| Verification | `docs/plans/VERIFY-complete-data-backup-correction-v2.md` | Checking exact-SHA evidence |
| Writer census | `docs/plans/COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.md` | Reviewing Hybrid audit scope |
| Hybrid audit contract | `docs/inter-model/COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md` | Closing the remaining separate track |
| Current cross-arc handoff | `docs/inter-model/LATEST.md` | Confirming rollout and current ownership |

## 10. How to Update This Brief (departure protocol)

Keep this file a current-state snapshot, not a session log. Overwrite sections
3–6 when a milestone changes, remove completed checklist items, keep the role
guidance aimed at the next model, and add only one milestone-level line to the
Update Log. Session narrative belongs in Track A ingest.

The test is: could a fresh model read only this file and know what exists, what
is blocked, and which owner may authorize the next action?

## Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-09 | Codex | Added the missing arc brief; v2 rollout is complete and the Hybrid audit remains separately open. |
