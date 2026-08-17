# Handoff: CodeQL Complex Therapy — Planning Package (Codex)

**Arc:** CodeQL Complex Therapy  
**Date:** 2026-08-16  
**Author:** Cursor  
**For:** Codex (architecture / execution / VERIFY planning)  
**Authorization:** Ryan, 2026-08-16 (session — authorize Codex to start planning; no implementation)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `AUTHORIZED` — planning `NOT_STARTED` |
| **Branch** | `plan/2026-08-16-codeql-complex-therapy` |
| **Base `main`** | `9c2a678` (Pinwheel arc closed #197) |
| **Push status** | push after this commit |
| **PR** | not opened |
| **Ryan GATE** | Review planning package; then authorize Execute lane separately |
| **Track A ingest** | Cursor session `72d96af9-e892-4d1d-9574-2016130c351b` |

---

## Consequence

After Pinwheel and CI Kryptonite, `main` requires `pylint (3.12)` and `pytest (3.12)`
but **CodeQL still passes without blocking merge**. This arc should close that gap:
make CodeQL a **required** merge condition (or an explicit documented subset), with
VERIFY evidence and disposable controls — same discipline as Kryptonite #188 and
Pinwheel #192–#194.

---

## What Codex must produce (planning only)

Deliver on branch `plan/2026-08-16-codeql-complex-therapy` (or successor plan branch):

1. `docs/plans/ARCHITECTURE-codeql-complex-therapy.md`
2. `docs/plans/EXECUTION-codeql-complex-therapy.md`
3. `docs/plans/VERIFY-codeql-complex-therapy.md`
4. `docs/plans/STATUS-codeql-complex-therapy.md` (JudgeBench 10-section template)
5. Update `AGENTS.md` and `config/agent-protocol.md` **Active STATUS files** list
6. Short Codex handoff back to Ryan/Kiro with merge-reading links

**No implementation** in this phase — no ruleset edits, no workflow commits, no
disposable PRs until Ryan authorizes Execute after planning review.

---

## Problem (product terms)

GitHub Advanced Security runs CodeQL on pull requests. Checks often **pass** and
appear on the PR, but **Protect Main does not require them**. A change that fails
CodeQL (or stops running it) can still merge if pylint and pytest are green.

Kryptonite explicitly documented this gap (`ARCHITECTURE-ci-behavioral-merge-gate.md`,
VERIFY `V1e` **N/A**). Pinwheel intentionally did **not** fix it (`V6c` out of scope).

---

## Live system state (verify at planning time — do not trust this handoff alone)

| Surface | State |
|---------|--------|
| `main` tip | `9c2a678` after Pinwheel closeout |
| Workflow | `.github/workflows/pylint.yml` — pylint + pytest jobs only; **no CodeQL workflow in repo** |
| Protect Main ruleset | `19156572` — **required:** `pylint (3.12)`, `pytest (3.12)` only |
| CodeQL on PRs | Observed passing on recent PRs (#187, #191); contexts include `Analyze (python)`, `Analyze (actions)`, `CodeQL` — **Codex must record exact context strings** from a live PR or API |
| Bypass | Repository-role bypass `always` on ruleset — document; do not exercise as evidence |
| Dependabot | GitHub reports 1 open critical alert on default branch — **scope decision:** fix in this arc vs separate |

---

## Predecessor arcs (patterns to reuse)

| Arc | What to copy |
|-----|----------------|
| **CI Kryptonite** (#187 + disposable #188) | Required status on ruleset; disposable PR proves red check + `mergeStateStatus=BLOCKED` |
| **Pinwheel** (#191 + #192–#194) | VERIFY oracle rows; Ryan disposable authorization; Kiro V7a; arc closeout |

**Distinction to preserve:** passing CodeQL ≠ required CodeQL (Kiro closeout handoff,
`CODEX-2026-08-15-ci-behavioral-merge-gate-closeout-handoff.md`).

---

## Planning questions Codex must resolve

1. **Which check context(s)** become required? (e.g. `CodeQL` vs `Analyze (python)` vs both)
2. **Ruleset-only vs workflow changes** — is adding required status sufficient if CodeQL is already triggered by GHAS?
3. **Negative control** — what disposable change produces a **required** red CodeQL result without a real long-lived vulnerability on `main`? (Pattern: Kryptonite used a failing test on a disposable branch.)
4. **Strict policy** — align with existing `strict_required_status_checks_policy: true`
5. **Scope lock** — do not weaken pylint/pytest/Pinwheel; do not change bypass policy as “proof”
6. **VERIFY rows** — map V0–V7 like Pinwheel (disposable controls = separate Ryan grant in EXECUTION)

---

## What NOT to build (planning or execute without new grant)

- Pinwheel pytest pin, manifest checker, or contract tests
- Runtime, Chroma, ledger, or corpus changes
- Broad dependency remediation unrelated to the merge gate (unless Ryan scopes Dependabot into arc)
- Exercising admin bypass as negative-control evidence
- Implementation or disposable PRs in **this** planning authorization

---

## Acceptance criteria (planning phase)

- [ ] Architecture states exact required status context name(s) and ruleset target
- [ ] Execution separates planning → Ryan review → Cursor implement → disposable controls
- [ ] VERIFY lists disposable negative control and restoration rows before Execute
- [ ] STATUS gives a fresh model Goal / Role / System / Next action
- [ ] `LATEST.md` updated when planning package ready for Ryan review

---

## Merge reading (inputs)

- [`ARCHITECTURE-ci-behavioral-merge-gate.md`](../plans/ARCHITECTURE-ci-behavioral-merge-gate.md)
- [`VERIFY-ci-behavioral-merge-gate.md`](../plans/VERIFY-ci-behavioral-merge-gate.md) — especially `V1e`, `V3c–V3e`
- [`ARCHITECTURE-pinwheel-pytest-ci.md`](../plans/ARCHITECTURE-pinwheel-pytest-ci.md) — CodeQL explicitly deferred
- [`VERIFY-pinwheel-pytest-ci.md`](../plans/VERIFY-pinwheel-pytest-ci.md) — closed arc evidence
- [`CODEX-2026-08-15-ci-behavioral-merge-gate-closeout-handoff.md`](CODEX-2026-08-15-ci-behavioral-merge-gate-closeout-handoff.md)
- [`STATUS-judgebench.md`](../plans/STATUS-judgebench.md) — STATUS template reference

---

## Codex session start

```bash
convmem doctor && convmem brief --stdout-only
git fetch origin && git switch plan/2026-08-16-codeql-complex-therapy
# Confirm base: git merge-base HEAD origin/main
gh api repos/alanmz-crypto/convmem/rulesets/19156572
gh pr checks 191   # or latest merged PR — capture CodeQL context strings
```

**Arc: CodeQL Complex Therapy** — state Goal / Role / System / Next action in first response.
