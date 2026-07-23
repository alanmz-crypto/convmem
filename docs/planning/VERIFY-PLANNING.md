# Verify Planning

Answers: **How do we prove this arc was done correctly — without trusting chat claims alone?**

Enter after Execute Task + HITL review for an **arc**. Copy
[`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md) to
`docs/plans/VERIFY-<slug>.md`, fill checks, run mechanical evidence, stop for
independent sign-off and Ryan GATE.

---

## Phase Initialization

| Field | Value |
|-------|-------|
| **Phase** | Verify Planning |
| **Characters** | Independent Reviewer, Test-First Reviewer |
| **Functions** | Reviewer |
| **Lanes** | Cursor (mechanical evidence); Kiro or Ryan-named independent lane (sign-off); Ryan (GATE) |
| **Engineering References** | Arc EXECUTION / ARCHITECTURE plans; [`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md) |
| **Probe Version** | v1 |
| **Exit Condition** | VERIFY artifact complete; mechanical run recorded; HITL sign-off / GATE pending |
| **Authority** | Post-execute HITL — do not trust prior chat claims alone |

Only after initialization may verify work begin.

---

## Objective

Produce and run a durable `docs/plans/VERIFY-<slug>.md` for the active **arc**
so closeout is evidence-based.

**Arc:** work tracked by an `ARCHITECTURE-*` and/or `EXECUTION-*` plan, or a
multi-PR milestone Ryan names an arc.

**Not required (unless Ryan says otherwise):** drive-by single-file docs typos,
Dependabot-only bumps, or a Ryan-written waiver in the PR/handoff.

This phase is Verify OS. It is not implementation
([`EXECUTE-TASK.md`](EXECUTE-TASK.md)) and not plan revision
([`REVISE-PLANNING.md`](REVISE-PLANNING.md)).

---

## Responsibilities

### Planning Status (emit at start)

```
Planning Status

Phase:        Verify Planning
Characters:   Independent Reviewer, Test-First Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro or named independent lane (sign-off); Ryan (GATE)
Authority:    Post-execute HITL — do not trust chat claims alone
```

### When to enter

- After Execute for an arc, before calling the arc closed / soft-closed.
- When Ryan asks for a verification plan for a named arc.
- Not for greenfield design or task shaping (Architecture / Execution Planning).
- Not as a substitute for per-task pytest/doctor during Execute.

### Required inputs

| Input | Why |
|-------|-----|
| Arc EXECUTION and/or ARCHITECTURE plan | Scope boundary |
| Merged tip SHA(s) / PR numbers | Authority tip |
| Execute External Review evidence row | Applicability decision; subject tip and reviewed SHA; result and finding dispositions when BugBot was required |
| [`VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md) or existing VERIFY stub | Structure |
| Contemporaneous evidence (logs, inventories) when re-proof is impossible | Honest SKIP |

### Verify loop (ordered)

| Step | Name | Actions |
|------|------|---------|
| **0** | **Name the artifact** | `docs/plans/VERIFY-<slug>.md` (create from template if missing) |
| **1** | **Scope lock** | In-scope / out-of-scope; forbid scope creep into next arc |
| **2** | **Write checks** | Numbered V0…Vn; each PASS/FAIL/SKIP + one-line evidence rule |
| **3** | **Assign lanes** | Mechanical filler vs independent sign-off vs Ryan GATE |
| **4** | **Mechanical run** | Cursor (or named runner) fills evidence; no chat-only PASS |
| **5** | **Independent sign-off** | Kiro (default) or Ryan-named lane; no cleanup/correction by verifier |
| **6** | **HITL GATE** | Ryan merges VERIFY docs and/or accepts arc close |

### Minimum bar (every arc VERIFY)

- **Human consequence block first** (consequence for Ryan → 5 Ws → TL;DR;
  honest limits if any) — see [`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md).
  This does **not** replace the tables below; both are required.
- **Merge reading links** in that human block (ARCHITECTURE / EXECUTION /
  VERIFY / LATEST Active handoff, plus any other docs the close depends on)
- Scope lock table
- Numbered checks with PASS/FAIL/SKIP + one-line evidence
- Explicit lanes (mechanical / independent / Ryan GATE)
- Evidence log line (tip SHA, runner, timestamp)
- Soft-close / arc close blocked until VERIFY exists and mechanical run is
  recorded — or Ryan writes an explicit waiver

### BugBot confirmation prerequisite

Execute owns BugBot applicability under
[`EXECUTE-TASK.md`](EXECUTE-TASK.md#external-review-gate). Verify copies that
decision and confirms its evidence; it does not reclassify the change.

When Execute recorded `gate_applicability=required`, V0 must:

- cite the **subject tip SHA** (the commit being accepted) and
  **BugBot-reviewed SHA** (the commit BugBot evaluated);
- cite visible PR-native BugBot evidence;
- return **FAIL**, not SKIP, when the two SHAs differ; and
- confirm every finding is `fixed` or `ryan_accepted`, or that the accepted tip
  is clean, using the lifecycle in Execute.

When Execute recorded `gate_applicability=exempt`, V0 may record
`N/A (exempt)` only with the exemption reason and subject tip SHA. When BugBot
was unreachable, V0 must cite Ryan's written, tip-specific acceptance; absence
of that acceptance is FAIL.

Domain hardness (Restic absolute, overwrite STOP, etc.) belongs in the arc
VERIFY file, not this phase guide.

### Awareness (read-only)

- [`PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md)
- Example: [`../plans/VERIFY-r2a-config-generation.md`](../plans/VERIFY-r2a-config-generation.md)
- [`../CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md) — independent shipped-work style

### Outputs

- `docs/plans/VERIFY-<slug>.md` (filled or stub→filled)
- Mechanical evidence table / log
- Independent sign-off note (or pending)
- **No** implementation drive-by, **no** merge by agent, **no** `convmem record`
  unless Ryan asks

---

## Exit Criteria

This phase ends when:

- [ ] Four invariant questions answered (from [`PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md#four-question-invariant))
- [ ] Arc named; VERIFY path named
- [ ] Scope lock complete
- [ ] Checks V0…Vn written to minimum bar
- [ ] Execute External Review decision confirmed; applicable BugBot SHAs match and findings are disposed, or an exempt / Ryan-accepted N/A is evidenced
- [ ] Mechanical run recorded (or honest SKIP with contemporaneous evidence cite)
- [ ] Independent sign-off requested or recorded
- [ ] No self-declared arc close without Ryan GATE or written waiver
- [ ] No `convmem record` unless Ryan asks

Cursor must stop here. Await HITL.
