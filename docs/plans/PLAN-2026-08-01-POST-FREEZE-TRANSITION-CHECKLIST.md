# Post-freeze transition checklist — planning only

**Mode:** Review and planning only. This checklist authorizes nothing now. It
does not arm C7, close the C6 HOLD, reset a standing-check row, enable Shadow,
or authorize any config, register, ledger, service, census, Chroma, cleanup,
deletion, pruning, or other live-artifact operation.

**Freeze boundary:** the deployed checkout remains frozen at
`76126e07a97187f68d925dd8b431d2d03967084f` through 2026-08-07 00:00 UTC.
No step below may be considered before that UTC boundary. Ryan must name every
state-changing operation separately after the read-only gates pass.

## 0. Freeze-end gate — read-only

1. Confirm the current UTC time is strictly after 2026-08-07 00:00 UTC.
2. Run the existing read-only `convmem doctor` protocol and note its output in
   the session transcript or chat. Do **not** run `convmem record`.
3. Note active-unit and summary counts from the read-only health output. These
   are observations, not a standing-check reset or a ledger entry.

If the time gate is not met or the health check reports a new critical failure,
stop. No later section is authorized by this checklist.

## 1. Deployed identity and Shadow state — read-only, Ryan host only

Ryan must run these checks on the deployed checkout that production writers
import. A worktree or remote-tracking ref is not a substitute:

```bash
git rev-parse HEAD
git show HEAD:writer_census.py >/dev/null
git show HEAD:chroma_write_store.py | rg 'record_writer_open|record_writer_close'
```

Record the results in chat/session notes only. Confirm the deployed identity and
C7 code before continuing. A SHA mismatch, missing file, or import error is a
STOP; it does not authorize choosing a successor SHA.

Before any Python introspection, Ryan must establish from the exact deployed
source that the imported modules have no module-level file, lock, database,
network, or service side effects. `python -B` suppresses bytecode writes but is
not by itself proof of read-only imports. If that negative property cannot be
proven, stop and do not run the introspection commands.

After that proof, the following may be used only to print identity values:

```bash
python -B -c 'from chroma_write_store import WRITER_GATE_PROTOCOL_VERSION; print(WRITER_GATE_PROTOCOL_VERSION)'
python -B -c 'import config as c; from pathlib import Path; cfg=c.load_config(c.CONFIG_PATH); print(Path(cfg["index"]["chroma_dir"]).expanduser().resolve())'
python -B -c 'from chroma_write_store import DEFAULT_WRITER_LOCK; print(DEFAULT_WRITER_LOCK.expanduser().resolve())'
```

Run the read-only doctor check and confirm `shadow_ledger: disabled`. Do not
alter config, activation manifests, services, Chroma, census artifacts, or
Shadow state to make the check pass.

## 2. Freshness and unexpected-artifact recheck — read-only

1. Re-run the read-only doctor/brief/unresolved checks and note results only in
   chat/session notes; do not create, close, or modify observations.
2. Compare the live count with the historical plan-authorship snapshot
   (12,452 units / 1,779 summaries at 2026-07-31 08:42 UTC) and the standing
   thresholds (`5714 × 2.0 = 11,428`; `5708 × 2.0 = 11,416`). Arithmetic does
   not authorize tuning or a register edit.
3. Recheck the recency decision and recent gate-failure windows read-only.
4. Inspect whether the census directory or any C6 generator/evidence artifact
   appeared unexpectedly. Do not delete, repair, move, or prune anything; an
   unexpected artifact is a STOP to report to Ryan.

## 3. Preserve the held gates — read-only review

- C7 remains unarmed unless a separately named Ryan authorization and valid
  census artifact prove otherwise.
- Shadow remains disabled.
- C6 remains HOLD unless fresh event-size evidence, independent review, and all
  seven C6 boundary rows are complete.
- Recency remains evaluation-only; escalation remains denominator/HOLD-bound.
- No observation, standing-check row, config, ledger, census, Shadow, Chroma,
  service, cleanup, deletion, or pruning state may be changed by this review.

Any failed gate is a STOP, not an invitation to repair or bypass the evidence.

## 4. Separate Ryan authorization gates

No lane may infer authorization from this checklist or from PASS results above.
Ryan must name the exact resource, operation, and final value (or named
one-shot) before any of the following:

- C7 arm, observation mutation, or final report;
- C6 operation or event-size generator implementation;
- Shadow activation;
- recency config/register change or escalation threshold/register change;
- any config, register, ledger, service, census, Chroma, cleanup, deletion,
  pruning, or other live-artifact operation.

Until such a named authorization exists, stop after read-only verification.

## Verdict

**POST-FREEZE TRANSITION CHECKLIST — PLAN ONLY**

This document preserves the source-plan stop conditions and makes no claim that
the freeze has ended, that any gate has passed, or that any operation is
authorized.
