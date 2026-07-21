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

| ID | Check | PASS |
|----|-------|------|
| V0a | … | … |

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
