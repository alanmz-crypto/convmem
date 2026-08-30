# Execute Handoff: [Arc Recent-Completions Verification Sweep] Copilot audit-lane — #221 post-remediation re-review

**Date:** 2026-08-30
**Author:** Cursor (dispatch)
**For:** **Copilot audit-lane** (you execute this handoff)
**Authorization:** Ryan proxy GATE — **blocked until fix PR merges to `main`**

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED — blocked on fix merge` |
| **Sequence** | **Step 2a-r** (Copilot re-review after remediation) |
| **Fix branch** | `fix/2026-08-30-2026-08-30-inter-model-provenance-reindex` @ `cf706d7` |
| **Prior verdict** | Step 2a **FAIL** @ `722141d…` (provenance re-index) — stands as historical attestation |
| **Subject SHA** | `<fix merge SHA on main>` — fill after Ryan merges fix PR |
| **Ryan GATE after you** | PASS → dispatch Kiro step 2b; FAIL → remediation continues |

### Step 2a closed (do not re-litigate)

```text
Subject SHA: 722141d31e586151f361ef7006ad74c71cdff534
Copilot audit-lane: FAIL — provenance re-index mints fresh assertion under stable ID
Tree match: Y
GAP closed: N
```

### Remediation landed (Ryan proxy authorization)

Fix PR replays existing provenance identity on **unchanged** inter-model/Kiro
re-index; **changed** section content fails closed pending supersession work.

---

## What you must do (not optional)

At the **fix merge SHA on `main`**, issue terminal **PASS or FAIL** covering:

1. Unchanged inter-model/Kiro re-index preserves assertion identity (regression closed)
2. Write gating / writer-boundary / TLS nesting (prior PASS scope — confirm still sound)
3. Changed-content path behavior (fail-closed acceptable if documented; supersession may be follow-up)

**Do not** re-litigate the historical FAIL at `722141d…` — that attestation remains valid
for the pre-fix landing era.

---

## Evidence commands (run yourself)

```bash
git fetch origin
git merge-base --is-ancestor <fix-merge-sha> origin/main
git show <fix-merge-sha> -- inter_model_index.py tests/test_inter_model_provenance_reindex.py

pytest tests/test_inter_model_provenance_reindex.py tests/test_p3_assertion_continuity.py -q
```

Inspect `inter_model_index._replay_unchanged_inter_model_projection` and
`_guard_changed_inter_model_replace`.

---

## Output contract (required)

```text
Subject SHA: <fix merge SHA on main>
Copilot audit-lane: PASS|FAIL — <one line rationale>
Remediates step 2a FAIL at 722141d…: Y|N
GAP closed: Y|N
```

**GAP for #221 closes only if this PASS + Kiro step 2b PASS.**

---

## What NOT to do

- Do not start before fix PR is merged to `main`.
- Do not proceed to Kiro 2b or #202 step 3 from this lane.
- Do not issue COMMENTED-only deferral.

---

## Reference

Original step 2a: [`COPILOT-2026-08-30-verification-sweep-221-execute-handoff.md`](COPILOT-2026-08-30-verification-sweep-221-execute-handoff.md)

Routing index: [`CURSOR-2026-08-30-verification-sweep-221-execute-handoff.md`](CURSOR-2026-08-30-verification-sweep-221-execute-handoff.md)

**TL;DR:** [Arc Recent-Completions Verification Sweep] Copilot re-review at fix merge SHA — blocked until merge. Step 2a-r.
