# Verification Handoff: [Arc Recent-Completions Verification Sweep] #202 CodeQL closeout

**Date:** 2026-08-30
**Author:** Cursor (drafting lane)
**For:** **Kiro + Copilot audit-lane** (both required)
**Authorization:** Ryan proxy GATE — see [coordination handoff](CURSOR-2026-08-30-verification-sweep-tier0-coordination-handoff.md)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `AUTHORIZED — verdict pending` |
| **Subject** | PR #202 — CodeQL Complex Therapy arc closeout (docs only) |
| **Landed SHA** | `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481` |
| **PR #202 head** | `906cbd88141186f69de8a7c7d64fcfd50a54ce6b` (squash ≠ head) |
| **GitHub reviews on #202** | **0** |
| **Kiro PASS SHAs on record** | `d3d0bdd…`, `cd653d9…` — **NOT** on `main` ancestry |
| **Ryan GATE after verdict** | Accept arc closeout attestation or schedule remediation |

---

## What to verify

Attest that **live GitHub ruleset enforcement matches Grant A baseline** and
that closeout documentation at **`d10e1d5…`** accurately describes it.

**Do not** re-verify disposable `d3d0bdd9986c7f77e60f956c6018493f22b784f2` as
on-main code — that SHA was B2 producer-identity probe, intentionally not merged
(VERIFY V5f).

The arc’s mechanism is **ruleset API state**, not a git commit on `main`. Kiro/Copilot
cannot infer live config from `d10e1d5…` alone — use the bundled snapshot below.

---

## Bundled live ruleset snapshot (Cursor, 2026-08-30)

**Command:** `gh api repos/alanmz-crypto/convmem/rulesets/19156572`

| Field | Value |
|-------|--------|
| **ID** | `19156572` |
| **Name** | Protect Main |
| **Target** | `refs/heads/main` |
| **Enforcement** | `active` |
| **Updated** | `2026-08-16T17:28:45.193-05:00` |
| **Strict policy** | `true` |

**Required status checks:**

| Context | integration_id |
|---------|----------------|
| `pylint (3.12)` | 15368 |
| `pytest (3.12)` | 15368 |
| `Analyze (actions)` | 15368 |
| `Analyze (python)` | 15368 |
| `CodeQL` | 57789 |

**Ancestry check (confirmed):**

| SHA | On `main` ancestry? |
|-----|---------------------|
| `d10e1d5…` (landed closeout) | YES |
| `d3d0bdd…` (Kiro impl evidence) | NO |
| `cd653d9…` (Kiro planning closeout) | NO |

Compare live snapshot against Grant A baseline in
`docs/plans/VERIFY-codeql-complex-therapy.md` (V1/V2/V5e rows).

### Closeout commit scope

`d10e1d5…` — planning/protocol docs only (10 files); no workflow or ruleset
file on `main`. Disposable PRs #198–#201 were closed without merge.

---

## Reviewer tasks

### Kiro

1. Live ruleset `19156572` matches Grant A five-context baseline
2. Closeout docs at `d10e1d5…` accurately describe live enforcement
3. Bind attestation to **`d10e1d5f4993f60a32142115f8b8c0f0f9ea4481`** + snapshot above
4. Note: historical Kiro PASS at `d3d0bdd…` is disposable evidence only

### Copilot audit-lane

1. Producer binding claim (integration IDs, especially CodeQL `57789`)
2. No security regression vs Grant A/B evidence
3. Written PASS or FAIL naming subject **`d10e1d5…`** and ruleset snapshot

---

## Output contract

```text
Subject SHA (docs): d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
Live ruleset 19156572 vs Grant A: PASS|FAIL — <evidence>
Closeout doc accuracy: PASS|FAIL
Kiro: PASS|FAIL — <one line>
Copilot audit-lane: PASS|FAIL — <one line>
GAP closed: Y|N
```

---

## What NOT to do

- Do not treat Kiro PASS at `d3d0bdd…` as verdict on `main`.
- Do not merge or restore disposable branches #198–#201.
- Do not mutate ruleset from this review lane.
- Do not patch workflows on `main`.

---

## Acceptance criteria

- [ ] Live ruleset compared to VERIFY baseline (not chat claims)
- [ ] Both reviewers name `d10e1d5…` in written verdict
- [ ] Producer binding explicitly addressed
- [ ] GAP row closable or FAIL with material finding

**TL;DR:** [Arc Recent-Completions Verification Sweep] Kiro + Copilot attest live
ruleset `19156572` + doc accuracy at `d10e1d5…` — not disposable off-main SHAs.
