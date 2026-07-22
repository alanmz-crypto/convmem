# Verify Plan — <arc-slug>

```
Planning Status

Phase:        Verify (<arc-slug>)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** `<branch or main tip SHA>`  
**PR(s):**  
**EXECUTION / ARCHITECTURE:**  
**Goal:** Prove this arc was done correctly within scope.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
BugBot-only V0 rows may use **N/A (exempt)** when Execute recorded a valid
exemption and reason. An applicable SHA mismatch is always **FAIL**, never SKIP.

**GATE** = Ryan process step; not a mechanical agent PASS.

**Flow:** Complete **V0–Vn** → Mechanical PASS|FAIL → independent sign-off → Ryan GATE.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| … | … |

---

## V0 — Preconditions

```bash
# tip / PR / doctor as needed
```

### External Review evidence input

Copy this row from Execute; do not decide applicability in Verify.

| Field | Value |
|-------|-------|
| `gate_applicability` | `required` \| `exempt` |
| `reason` | … |
| `subject_tip_sha` | … |
| `bugbot_reviewed_sha` | … \| `n/a` |
| `result` | `clean` \| `findings` \| `unreachable` \| `n/a` |
| `finding_disposition` | Per finding: `fixed` \| `ryan_accepted` \| `none` |
| `authority_reference` | Ryan acceptance / comment authority / `n/a` |

| ID | Check | PASS / FAIL / SKIP / N/A |
|----|-------|---------------------------|
| V0a | Subject tip SHA resolves to the commit being verified | … |
| V0b | Execute applicability decision and reason are present | … |
| V0c | If required: BugBot-reviewed SHA equals subject tip SHA and PR-native evidence is cited; **FAIL** on mismatch | … |
| V0d | If findings: each is `fixed` or `ryan_accepted` under Execute's lifecycle; if unreachable: Ryan's tip-specific acceptance is cited | … |
| V0e | If exempt: record `N/A (exempt)` with reason and subject tip SHA | … |

---

## V1 — …

| ID | Check | PASS |
|----|-------|------|
| V1a | … | … |

---

## Vn — Independent sign-off

| ID | Check | PASS |
|----|-------|------|
| Vna | Written PASS/FAIL naming tip SHA and residuals | … |

Verifier performs **no** cleanup or correction.

---

## Evidence log

```text
VERIFY-<arc-slug> — tip <sha> — runner <lane> — <ISO-8601>
V0: …
…
Mechanical: PASS|FAIL
Sign-off: …
```
