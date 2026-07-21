# Verify Plan — Verify Every Arc (Planning OS)

```
Planning Status

Phase:        Verify (verify-every-arc)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** `4da68e8a2fe6fee011d29b40afc791aa76213a3f` (PR #62 head)
**Base:** `1b090bca40f4ee42f07efc5a55220636e93c073f`
**PR:** [#62](https://github.com/alanmz-crypto/convmem/pull/62)
**EXECUTION / ARCHITECTURE:** No standalone EXECUTION file — this is a
docs-infrastructure arc. Change scope is fully enumerated in the six-file diff
against `main`.

**Goal:** Prove that the mandatory-VERIFY arc rule is correctly wired into the
Planning OS — the new phase guide is contract-compliant, the template is
copyable, the kernel and downstream guides reference the new phase, and
`convmem doctor` passes.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line
of evidence.
**GATE** = Ryan process step; not a mechanical agent PASS.

**Flow:** V0 → V1 → V2 → V3 → V4 (sign-off) → Ryan GATE.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Six files in PR #62: `docs/PLANNING-PROTOCOL.md`, `docs/planning/VERIFY-PLANNING.md`, `docs/planning/EXECUTE-TASK.md`, `docs/planning/EXECUTION-PLANNING.md`, `docs/plans/VERIFY-TEMPLATE.md`, `docs/inter-model/LATEST.md` | Implementation of any VERIFY plan for another arc |
| `convmem doctor` `planning_guide_contract` PASS with five guides | Content of sibling VERIFY plans already on main |
| Contract v1 structure requirements for `VERIFY-PLANNING.md` | PR #42 Dependabot bump (explicitly exempt) |
| Downstream wiring in `EXECUTE-TASK.md` and `EXECUTION-PLANNING.md` | Architecture changes to Planning OS beyond phase wiring |
| LATEST.md pointer to new phase | Any code, tests, or runtime behavior |

---

## V0 — Preconditions

```bash
convmem doctor
git -C ~/Projects/convmem rev-parse HEAD
git -C ~/Projects/convmem merge-base --is-ancestor \
    1b090bca40f4ee42f07efc5a55220636e93c073f HEAD && echo base_ancestor_ok
```

| ID | Check | PASS |
|----|-------|------|
| V0a | `convmem doctor` exits 0 (warnings non-fatal) | All checks PASS (1 non-fatal WARN) |
| V0b | `planning_guide_contract` passes with 5 guide(s) | `contract v1: 5 guide(s) ok` |
| V0c | HEAD is `4da68e8a2fe6fee011d29b40afc791aa76213a3f` | Confirmed |
| V0d | Base `1b090bc…` is ancestor of HEAD | `base_ancestor_ok` |
| V0e | No unrelated dirty tracked files that could contaminate the diff | Git status clean (only untracked `.kilo/`, `login`) |

---

## V1 — File set

Exactly six files changed; no code, no tests, no runtime modules.

```bash
git -C ~/Projects/convmem diff origin/main...HEAD --name-only | sort
```

| ID | Check | PASS |
|----|-------|------|
| V1a | Exactly these six paths and no others: `docs/PLANNING-PROTOCOL.md`, `docs/planning/EXECUTE-TASK.md`, `docs/planning/EXECUTION-PLANNING.md`, `docs/planning/VERIFY-PLANNING.md`, `docs/plans/VERIFY-TEMPLATE.md`, `docs/inter-model/LATEST.md` | `git diff --name-only` matches exactly |
| V1b | No `.py`, `.sh`, `.json`, or `.toml` files changed | Grep diff for those extensions: clean |
| V1c | All changed files are under `docs/` | Path prefix check |

---

## V2 — Contract compliance (`VERIFY-PLANNING.md`)

`VERIFY-PLANNING.md` is a new phase guide. Contract v1 requires specific
headings, metadata fields, and exit-intent lines.

```bash
python3 -c "
from pathlib import Path
text = Path('docs/planning/VERIFY-PLANNING.md').read_text()
required_headings = [
    '## Phase Initialization',
    '## Objective',
    '## Responsibilities',
    '## Exit Criteria',
]
required_fields = ['Phase','Characters','Functions','Lanes','Authority','Probe Version']
required_stops = ['Cursor must stop here.', 'Await HITL.']
for h in required_headings: print('heading', 'PASS' if h in text else 'FAIL', h)
for f in required_fields: print('field', 'PASS' if f in text else 'FAIL', f)
for s in required_stops: print('stop', 'PASS' if s in text else 'FAIL', repr(s))
"
```

| ID | Check | PASS |
|----|-------|------|
| V2a | `## Phase Initialization` heading present | PASS |
| V2b | `## Objective` heading present | PASS |
| V2c | `## Responsibilities` heading present | PASS |
| V2d | `## Exit Criteria` heading present | PASS |
| V2e | All six metadata fields present: Phase, Characters, Functions, Lanes, Authority, Probe Version | PASS (all 6) |
| V2f | `Cursor must stop here.` present | PASS |
| V2g | `Await HITL.` present | PASS |
| V2h | Phase field value is `Verify Planning` | PASS |
| V2i | Authority field reads `Post-execute HITL — do not trust chat claims alone` | PASS |

---

## V3 — Content and wiring

### V3a — `VERIFY-PLANNING.md` content

| ID | Check | PASS |
|----|-------|------|
| V3a1 | Defines **arc** and when Verify is not required (drive-by typos, Dependabot, written waiver) | Present in Objective |
| V3a2 | Names the verify loop steps V0–V6 (name artifact → scope lock → write checks → assign lanes → mechanical run → independent sign-off → GATE) | Present in Responsibilities |
| V3a3 | Minimum bar stated: scope lock, numbered checks, explicit lanes, evidence log, soft-close blocked until VERIFY exists or waiver written | Present in Responsibilities |
| V3a4 | Links `VERIFY-TEMPLATE.md`, example `VERIFY-r2a-config-generation.md`, and `PLANNING-PROTOCOL.md` | All three linked |
| V3a5 | Exit criteria checklist includes independent sign-off, no self-declared arc close, no `convmem record` | All three present |

### V3b — `VERIFY-TEMPLATE.md` content

| ID | Check | PASS |
|----|-------|------|
| V3b1 | Contains Planning Status block with all six metadata fields as `<placeholders>` | PASS |
| V3b2 | Contains Scope lock table (In scope / Out of scope) | PASS |
| V3b3 | Contains numbered V0 stub and Vn independent sign-off stub | PASS |
| V3b4 | Contains Evidence log stub with `tip <sha>`, `runner <lane>`, ISO-8601 timestamp | PASS |
| V3b5 | File is copyable without modifications required before structure is valid | PASS |

### V3c — Kernel wiring (`PLANNING-PROTOCOL.md`)

| ID | Check | PASS |
|----|-------|------|
| V3c1 | Workflow diagram now shows `Verify Planning` step between HITL Review and Revise Planning | PASS |
| V3c2 | Phase table includes `Verify Planning → planning/VERIFY-PLANNING.md` row | PASS |
| V3c3 | Arc rule paragraph present: every arc needs `VERIFY-<slug>.md`; stub during Execution Planning is OK; Ryan may waive in writing | PASS |
| V3c4 | Documentation Rule table includes `plans/VERIFY-<slug>.md` row | PASS |

### V3d — Downstream wiring (`EXECUTE-TASK.md`, `EXECUTION-PLANNING.md`)

| ID | Check | PASS |
|----|-------|------|
| V3d1 | `EXECUTE-TASK.md` Objective now references `VERIFY-PLANNING.md` and states arc handoff must name `VERIFY-<slug>.md` before claiming merge-ready closeout | PASS |
| V3d2 | `EXECUTE-TASK.md` Verification routes table includes `Arc closeout (Verify OS)` row linking `VERIFY-PLANNING.md` | PASS |
| V3d3 | `EXECUTE-TASK.md` Exit Criteria includes `If this task closes an arc: VERIFY path named` | PASS |
| V3d4 | `EXECUTION-PLANNING.md` Objective now references `VERIFY-PLANNING.md` and states execution plan must name companion VERIFY path | PASS |
| V3d5 | `EXECUTION-PLANNING.md` Planning Loop step 5 renamed to "Arc VERIFY companion" | PASS |
| V3d6 | `EXECUTION-PLANNING.md` Plan Artifact Template includes `Arc VERIFY companion` section | PASS |
| V3d7 | `EXECUTION-PLANNING.md` Awareness list includes `VERIFY-PLANNING.md` link | PASS |
| V3d8 | `EXECUTION-PLANNING.md` Exit Criteria includes `If arc: companion VERIFY path named (stub OK)` | PASS |

### V3e — LATEST.md pointer

| ID | Check | PASS |
|----|-------|------|
| V3e1 | LATEST.md updated heading from `R2a VERIFY plan after one-job closeout` to `VERIFY required every arc — Planning OS` | PASS |
| V3e2 | New bullet at top of Active handoff: links VERIFY-PLANNING.md, VERIFY-TEMPLATE.md, PLANNING-PROTOCOL.md, and example VERIFY-r2a-config-generation.md | PASS |

---

## V4 — Independent sign-off (Kiro)

| ID | Check | PASS |
|----|-------|------|
| V4a | Written PASS/FAIL naming tip `4da68e8a2fe6fee011d29b40afc791aa76213a3f` and any residuals | — |
| V4b | V0–V3 mechanical checks independently confirmed | — |
| V4c | No cleanup or correction performed by verifier | Verifier-only |

---

## Evidence log

```
VERIFY-verify-every-arc — tip 4da68e8a2fe6fee011d29b40afc791aa76213a3f — runner Kiro — 2026-07-20
V0: doctor PASS; planning_guide_contract: 5 guide(s) ok; HEAD 4da68e8a confirmed;
    base 1b090bc ancestor ok; no dirty tracked files (only untracked .kilo/ login)
V1: 6 files changed, all under docs/, no .py/.sh/.json/.toml — PASS
V2: 14/14 contract checks PASS (4 headings, 6 fields, 2 stops, phase value, authority value)
V3a: VERIFY-PLANNING.md — arc defined, drive-by/waiver exemptions, loop steps V0–V6,
     minimum bar, VERIFY-TEMPLATE/example/PLANNING-PROTOCOL links, exit criteria — 9/9 PASS
V3b: VERIFY-TEMPLATE.md — Planning Status, metadata placeholders, scope lock, V0 stub,
     sign-off stub, evidence log stub — 6/6 PASS
V3c: PLANNING-PROTOCOL.md — workflow diagram, phase table, arc rule, documentation rule — 4/4 PASS
V3d: EXECUTE-TASK.md + EXECUTION-PLANNING.md — Objective refs, arc closeout row,
     loop step, template section, awareness link, exit criteria — 8/8 PASS
V3e: LATEST.md — heading updated, bullet with four links — 5/5 PASS
Mechanical: PASS (41/41 checks)
Sign-off: pending (Kiro V4)
```
