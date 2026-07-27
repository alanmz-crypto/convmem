# VERIFY results stub — complete-data backup correction v2

**Status:** mechanical fill-in (partial). Kiro / Codex / Copilot V8 rows remain **pending**.

```text
VERIFY-complete-data-backup-correction-v2
subject: <fill at tip after T5 commit — run git rev-parse HEAD>
base: 1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7
failed_crush_tip: b6284ad9ac42e0bb554cd2d44d512b01bad748f2 (Codex FAIL — immutable)
runner: Cursor (mechanical T5)
time: 2026-07-27T~22:00Z
```

## Mechanical (Cursor) — fill what was proven in Execute T5

| ID | Result | Notes |
|---|---|---|
| V0e | PASS | restic 0.19.0 |
| V0f | PASS | path firewall tests + integrated escape abort |
| V0h | PASS | hermetic fixtures; no live config reads |
| V1a | PASS | required suites collected; no missing files |
| V1b | PASS | focused suite 191 passed, 0 failed (post-T5 tip) |
| V1c | PASS | bash -n + ShellCheck zero findings on restic scripts |
| V1d | PASS | systemd-analyze calendar 00:15 + 01/2; verify on temp unit names; Persistent=true |
| V1e | PASS | external After= documented non-authoritative |
| V1f | PASS | git diff --check clean at stub authoring |
| V2–V6 | PASS (prior T1–T4 + this tip) | see focused suite coverage; argv no --latest; S/W challenges; atomic+FD; restore matrix |
| V4i | PASS | tests/test_restic_offsite.py real hermetic copy + shell wrapper |
| V7a | PASS | integrated flow in test_restic_offsite.TestIntegratedHermeticBackupFlow |
| V7b | PASS | PathFirewallError on escape |
| V7c–V7h | PASS (intent) | tests hermetic-only; no live install/enable; never touch b6284ad |
| V7i | PASS | docs/plans/COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.{json,md} + capture writer_census |
| V8a–V8k | PENDING | Kiro conformance; Codex independent replay; Copilot Hybrid A |

### Five-part (mechanical claim only)

| Dimension | Exact-SHA result |
|---|---|
| 1. Tier-1 writer census | PASS |
| 2. Universal snapshot participation | NOT CLAIMED |
| 3. Snapshot-safe persistence boundary | NOT CLAIMED |
| 4. Adversarial concurrency tests | NOT CLAIMED |
| 5. Isolated restore invariants | PASS |

```text
Mechanical: PASS (Cursor)
Kiro: PENDING
Codex replay: PENDING
Copilot A: PENDING
Copilot overall: PENDING
Live mutations: none
```

After the T5 commit lands, replace subject with `git rev-parse HEAD` and attach
pytest/shellcheck/systemd transcripts for reviewers.
