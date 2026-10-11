# Implementation Handoff: Codex rollout admission, corrective 4 (gate-3 FAIL fixes)

**Arc: Codex (#286).**
**Date:** 2026-10-11
**Author:** Claude (Opus 5.5), design author
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-10-10. This is the same hermetic implementation
grant as the
[Execute handoff](CURSOR-2026-10-10-issue-286-codex-rollout-admission-execute-handoff.md).
It fixes review findings only and adds no new scope.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `feat/2026-10-10-issue-286-codex-rollout-admission` |
| **Tip SHA** | `905ad40` (failed gate 3; see below) |
| **Push status** | pushed to origin |
| **PR** | not opened; Ryan opens it after both reviews PASS |
| **Ryan GATE** | none to start. After this corrective: Copilot audit and Kiro recheck on the new exact tip, then Ryan's PR/merge decision. |

### Gate-3 result at `905ad40` (2026-10-11)

Both reviews failed the same tip. They don't conflict, so Sol-High does not
apply.

- **Kiro:** FAIL, on the Pylint regression gate only. All six §13 conditions
  pass their named tests. Kiro ruled on three items the design didn't cover:
  - **(a)** the D8 lineage fields are accepted;
  - **(b)** the terminal quarantine stays generic, covering every
    `live_route_refused` including Kiro exact-path sources;
  - **(c)** the D8 prose should name the lineage mechanism. That edit is
    done in this commit.
- **Copilot audit:** FAIL, with six findings, all reproduced hermetically.
  Claude confirmed each against the code at `905ad40`.

---

## What to build

Close every gate-3 finding so that both reviewers can pass the next exact
tip. Behavior stays as designed: admitted Codex rollouts use the guarded
incremental route, and a refused source is quarantined terminally by path
and never respawns. The findings show four paths that escape those
guarantees: crash recovery, verbose mode, source growth during a run, and
the marker parser.

**Why this exists:** the guards protect paid-call spend and watcher memory.
If one path can bypass them, the protection doesn't hold.

---

## Findings and required fixes

| # | Sev | Finding (reviewer) | Location at `905ad40` | Required fix |
|---|---|---|---|---|
| C1 | High | A pending transaction rolls forward before any admission guard or the D8 lineage check. A replay transformed above the chunk cap, and a rollback→re-enable replay committed instead of refusing (Copilot). | `incremental_jsonl.py:2221` (`return self._roll_forward(existing_tx)`), ahead of `:2277`/`:2332` | Recovery must refuse wherever a fresh run would, with zero provider calls. That covers identity, size, chunk cap, frontier subset and D8 lineage, for Codex-admitted sources. Either run the same guards on the roll-forward path before any replay transform, or refuse roll-forward for an admitted source whose guards fail. |
| C2 | High | In verbose mode stderr is inherited, so the marker is never captured. Exit 91 becomes `index subprocess exit 91` and is not quarantined; 3 events spawned 3 children (Copilot). | `watch.py:243–267` | Always capture stderr (and stdout), echoing them when verbose, so refusal handling never depends on verbose mode. |
| C3 | High | The parent's fallback hash keeps an unbounded `incomplete` buffer. An 8 MiB line with no newline retained 8 MiB despite 64 KiB reads (Copilot). | `adapters/jsonl_prefix.py` `streaming_complete_prefix_digest_for_path`; parent fallback in `watch.py` `_record_ready_path_failure` | Now that the digest is evidence only (§13 c3), the **parent never hashes**. The child always emits the digest in its marker; for `source_too_large`, the child computes it with an O(1)-memory hash. The parent records whatever the marker carries (an empty digest is allowed). Also make the helper O(1) memory: update one hasher with every byte, and take `hasher.copy()` just after each newline, rather than holding the tail. |
| C4 | High | Source growth bypasses the size ceiling. `_revalidate_live_prefix` reads the new full size unchecked (1,234 → 2,258 bytes against a 1,334-byte ceiling, then committed) (Copilot). | `incremental_jsonl.py:808–813` | For admitted sources, check `st_size` against `max_source_bytes` before the read and refuse `source_too_large`. Bound the read to what revalidation needs. |
| C5 | Medium | Any error text containing the marker quarantines the path. The regex is unanchored and the exit status isn't checked; an exit-1 child quarantined a non-Codex path (Copilot). | `watch.py:296–304` and the failure path at `:659` | Treat a failure as a refusal only when the child exits with the dedicated code 91 **and** stderr has a line matching the whole pattern `^live_route_refused:<outcome>(:<64-hex>)?$`. Carry the return code structurally (a typed exception or attribute), not by re-parsing message text. |
| C6 | Medium | A noncanonical admission root (`/../sessions`, `/./`, `/missing/..`) is silently normalized and accepted, not rejected (Copilot). | `config.py:106` → `_canonical_config_path` (`abspath`) | Reject any root whose raw value isn't already canonical: it must be absolute, contain no `.` or `..` component, and contain no symlink component. Accepting a root after normalizing it is the defect. |
| K1 | Gate | The Pylint regression gate fails (Kiro). This contradicts the PASS in the corrective-3 handoff-back. | gate output vs `ci/pylint-baseline.json` | Fix `convmem.py` C0207 (`rsplit(':', maxsplit=1)`). Break the three new cyclic pairs (`doctor↔watch`, `ingest↔watch`, `source_reconciler↔watch`), for example by moving refusal-state reads into a small module that both sides import. Only allowlist a cycle if breaking it isn't feasible, and say why. Clear the test-file findings (unused imports, line length, W0212, C1803, W0613). |

---

## What NOT to build

- No change to the §13 rulings: the quarantine stays terminal by path, and
  it stays generic across all `live_route_refused` (Kiro ruling (b)).
- No new admission rules, config keys or outcomes beyond what these fixes
  need.
- Everything in the Execute handoff's "What NOT to build" still applies: no
  live config, systemd, runtime worktree, watcher start, live index or
  provider call, and no PR.

---

## Test expectations

Hermetic only, as before. Each finding needs a test that fails at `905ad40`
and passes after the fix:

1. **C1:**
   - a `PREPARING` transaction replayed with a lower chunk cap refuses with
     zero provider calls;
   - a rollback→re-enable with a pending transaction refuses
     `projection_checkpoint_mismatch` with zero provider calls;
   - a pending transaction that passes all guards still rolls forward (no
     recovery regression).
2. **C2:** in verbose mode, a refusal quarantines on the first event, and 3
   later events spawn zero children.
3. **C3:**
   - the parent computes no digest on any refusal path;
   - the helper's memory stays bounded for a single 8 MiB unterminated line
     (assert the retained buffer is ≤ the read size, or use `tracemalloc`);
   - the property test against `prefix_sha256(data[:prefix_boundary(data)])`
     still passes.
4. **C4:** a source that grows past the ceiling between capture and
   revalidation refuses `source_too_large` with zero provider calls.
5. **C5:**
   - an exit-1 child whose error text quotes a marker does not quarantine;
   - exit 91 without a whole-line marker does not quarantine;
   - exit 91 with a whole-line marker does.
6. **C6:** `/../`, `/./`, `/x/..` and a symlink component each fail config
   validation, and an already-canonical root passes.
7. **K1:** the exact CI Pylint gate command passes (see Acceptance).

---

## Acceptance criteria

- [ ] C1–C6 and K1 are each fixed, and each is mapped to its test name in the
      handoff-back.
- [ ] The full CI-equivalent suite is green, apart from the known #320
      golden-eval test that depends on the live corpus.
- [ ] The Pylint regression gate passes when run exactly the way CI runs it.
      Paste the command and its final line, not just "PASS":
      `python scripts/pylint_regression_gate.py ci --report <pylint.json> --pylint-status <st> --branch-baseline ci/pylint-baseline.json`
      (mirror `.github/workflows` for how the report is produced).
- [ ] The secret scan, critical invariants, writer inventories and canary
      baselines pass; refresh any of them that drift.
- [ ] No live resource is touched.

---

## Branch convention

Same branch: `feat/2026-10-10-issue-286-codex-rollout-admission`. First
cherry-pick the docs commit that adds this file. It carries the D8 prose
update and the §13 record of Kiro's rulings, and both are normative. Push
after every commit with an explicit refspec. Ryan squash-merges.

---

## Related files

| What | Path |
|------|------|
| Normative design, §13 as amended | `docs/plans/DESIGN-issue-286-codex-rollout-admission.md` |
| Original Execute handoff | `docs/inter-model/CURSOR-2026-10-10-issue-286-codex-rollout-admission-execute-handoff.md` |
| Arc brief | `docs/plans/STATUS-codex-jsonl-production-integration.md` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on the pushed design branch
- [x] `LATEST.md` bullet updated with resume state
- [x] STATUS Update Log line
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Cherry-pick the docs commit; read §13 and this file
- [ ] State Goal / role / system state / next action; Arc: Codex
