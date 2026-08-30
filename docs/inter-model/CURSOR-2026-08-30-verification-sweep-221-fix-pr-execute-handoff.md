# Execute Handoff: [Arc Recent-Completions Verification Sweep] Cursor — #221 fix PR delivery

**Date:** 2026-08-30
**Author:** Cursor (dispatch)
**For:** **Cursor** (PR delivery lane — you execute this handoff)
**Authorization:** Ryan proxy GATE — remediation fix implemented @ `cf706d7`

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `CLOSED` — PR [#258](https://github.com/alanmz-crypto/convmem/pull/258) opened |
| **PR** | [#258](https://github.com/alanmz-crypto/convmem/pull/258) |
| **Sequence** | **Remediation delivery** — blocks Copilot step 2a-r until Ryan merges |
| **Branch** | `fix/2026-08-30-2026-08-30-inter-model-provenance-reindex` |
| **Tip SHA** | `cf706d732ac5f66a8ac31ea72397d9b0cdb21770` |
| **PR** | **not opened** (as of handoff authoring) |
| **Ryan GATE after you** | Squash-merge PR when CI green — **you do not merge** |

### Context (do not re-litigate)

| Step | Verdict |
|------|---------|
| 2a Copilot @ `722141d…` | **FAIL** — provenance re-index (historical attestation stands) |
| Fix @ `cf706d7` | Replay assertion on unchanged re-index; fail-closed on changed content |
| 2a-r Copilot | Blocked until fix lands on `main` |
| 2b Kiro | Blocked until 2a-r PASS |
| #202 3a/3b | Blocked until step 2 closes |

---

## What you must do (not optional)

**Do not** restate this handoff to Ryan without executing it.

**Do:**

1. Confirm branch tip and diff against `origin/main`
2. **Open the fix PR** (no PR exists yet)
3. Wait for required CI checks or report failures
4. Return the **Output contract** below with PR URL and CI status
5. Update routing docs on `docs/2026-08-30-2026-08-30-verification-sweep-tier0-handoffs` with PR number (commit + push)

**Do not** merge, rebase onto unrelated work, or start Copilot 2a-r from this lane.

---

## Pre-flight

```bash
git fetch origin
git rev-parse fix/2026-08-30-2026-08-30-inter-model-provenance-reindex
git log -1 --oneline fix/2026-08-30-2026-08-30-inter-model-provenance-reindex
git diff origin/main...fix/2026-08-30-2026-08-30-inter-model-provenance-reindex --stat
pytest tests/test_inter_model_provenance_reindex.py tests/test_p3_assertion_continuity.py -q
```

Expected diff: `inter_model_index.py` + `tests/test_inter_model_provenance_reindex.py` only.

---

## PR to open

**Title:** `fix: replay provenance when re-indexing unchanged inter-model sections`

**Body:**

After the verification sweep, Copilot found that re-indexing an existing inter-model section minted a fresh provenance assertion under the same stable projection ID, causing `add_unit()` to reject the write. Green CI missed this existing-row path.

**Who:** Cursor Execute (Ryan proxy authorization)
**What:** Replay existing provenance identity on unchanged re-index; fail-closed on changed content
**When:** Ready for merge @ branch tip
**Why:** Closes Copilot step 2a FAIL on #221 Trapdoor integration
**How:** Merge → Copilot step 2a-r → Kiro step 2b → resume tier-0 #202

**Test plan:**
- [ ] `pytest tests/test_inter_model_provenance_reindex.py tests/test_p3_assertion_continuity.py -q`
- [ ] Required CI green on PR

**TL;DR:** Replay provenance on unchanged inter-model re-index; changed-content supersession remains future work.

---

## Output contract (required)

```text
Fix branch: fix/2026-08-30-2026-08-30-inter-model-provenance-reindex
Tip SHA: <full SHA>
PR: #<number> <url>
CI: green|failing — <check names if failing>
Resume state: READY_FOR_RYAN_MERGE|BLOCKED_ON_CI
Next agent after merge: Copilot step 2a-r — COPILOT-2026-08-30-verification-sweep-221-rerun-execute-handoff.md
```

Post this block in chat. Ryan squash-merges when CI is green.

---

## What NOT to do

- Do not merge (Ryan owns merge).
- Do not dispatch Copilot 2a-r before merge lands on `main`.
- Do not expand scope (supersession for changed content is deferred).
- Do not touch verification-sweep docs on the fix branch — docs updates belong on the docs branch.

---

## After Ryan merges (not your step — for routing)

1. Record merge SHA in [`COPILOT-2026-08-30-verification-sweep-221-rerun-execute-handoff.md`](COPILOT-2026-08-30-verification-sweep-221-rerun-execute-handoff.md)
2. Dispatch **Copilot audit-lane** with that handoff only
3. After Copilot 2a-r PASS → dispatch **Kiro** with [`KIRO-2026-08-30-verification-sweep-221-execute-handoff.md`](KIRO-2026-08-30-verification-sweep-221-execute-handoff.md)

Routing index: [`CURSOR-2026-08-30-verification-sweep-221-execute-handoff.md`](CURSOR-2026-08-30-verification-sweep-221-execute-handoff.md)

**TL;DR:** [Arc Recent-Completions Verification Sweep] Open fix PR @ `cf706d7`, confirm CI, hand back to Ryan for merge — then Copilot 2a-r.
