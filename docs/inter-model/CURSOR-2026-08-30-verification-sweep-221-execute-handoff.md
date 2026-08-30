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
| 2a | Copilot audit-lane | [`COPILOT-2026-08-30-verification-sweep-221-execute-handoff.md`](COPILOT-2026-08-30-verification-sweep-221-execute-handoff.md) | **CLOSED — FAIL** @ `722141d…` |
| 2a-r | Copilot audit-lane | [`COPILOT-2026-08-30-verification-sweep-221-rerun-execute-handoff.md`](COPILOT-2026-08-30-verification-sweep-221-rerun-execute-handoff.md) | Blocked on fix merge |
| 2b | Kiro | [`KIRO-2026-08-30-verification-sweep-221-execute-handoff.md`](KIRO-2026-08-30-verification-sweep-221-execute-handoff.md) | Blocked on 2a-r PASS |
| 3a | Kiro | [`KIRO-2026-08-30-verification-sweep-202-execute-handoff.md`](KIRO-2026-08-30-verification-sweep-202-execute-handoff.md) | Blocked on step 2 |
| 3b | Copilot audit-lane | [`COPILOT-2026-08-30-verification-sweep-202-execute-handoff.md`](COPILOT-2026-08-30-verification-sweep-202-execute-handoff.md) | Blocked on 3a |

**Active dispatch:** none — **merge fix PR** then Copilot step **2a-r**.

Fix branch: `fix/2026-08-30-2026-08-30-inter-model-provenance-reindex` @ `cf706d7`

Background specs (not execute dispatches): [221 trapdoor integration](CURSOR-2026-08-30-verification-sweep-221-trapdoor-integration-handoff.md) · [202 CodeQL closeout](CURSOR-2026-08-30-verification-sweep-202-codeql-closeout-handoff.md)
