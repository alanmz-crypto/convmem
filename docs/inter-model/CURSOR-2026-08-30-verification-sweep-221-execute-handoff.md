# Execute routing index: [Arc Recent-Completions Verification Sweep] Tier-0 steps 2–3

**Date:** 2026-08-30
**Author:** Cursor (dispatch)
**For:** Ryan (routing)

Single-agent execute handoffs — dispatch **one agent at a time** in order.

---

## Sequence (4 steps)

| Step | Agent | Handoff | State |
|------|-------|---------|-------|
| 1 | Kiro | [`KIRO-2026-08-30-verification-sweep-253-execute-handoff.md`](KIRO-2026-08-30-verification-sweep-253-execute-handoff.md) | **CLOSED** — Kiro PASS @ `a924d388…` |
| 2a | Copilot audit-lane | [`COPILOT-2026-08-30-verification-sweep-221-execute-handoff.md`](COPILOT-2026-08-30-verification-sweep-221-execute-handoff.md) | **CLOSED — FAIL** (provenance re-index) |
| 2b | Kiro | [`KIRO-2026-08-30-verification-sweep-221-execute-handoff.md`](KIRO-2026-08-30-verification-sweep-221-execute-handoff.md) | Blocked — remediation first |
| 3a | Kiro | [`KIRO-2026-08-30-verification-sweep-202-execute-handoff.md`](KIRO-2026-08-30-verification-sweep-202-execute-handoff.md) | Blocked on step 2 |
| 3b | Copilot audit-lane | [`COPILOT-2026-08-30-verification-sweep-202-execute-handoff.md`](COPILOT-2026-08-30-verification-sweep-202-execute-handoff.md) | Blocked on 3a |

**Active dispatch:** none — **remediation gate** on #221 provenance re-index before Kiro 2b or step 3.

### Step 2a closed (Copilot FAIL — do not re-litigate)

```text
Subject SHA: 722141d31e586151f361ef7006ad74c71cdff534
Copilot audit-lane: FAIL — provenance re-index mints fresh assertion under stable
  projection ID; add_unit() rejects replacement; green CI missed existing-row path
Tree match (bfe79f7… vs 722141d…): Y
GAP closed: N
```

Background specs (not execute dispatches): [221 trapdoor integration](CURSOR-2026-08-30-verification-sweep-221-trapdoor-integration-handoff.md) · [202 CodeQL closeout](CURSOR-2026-08-30-verification-sweep-202-codeql-closeout-handoff.md)
