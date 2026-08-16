# Codex Handoff — CodeQL Complex Therapy Planning

**Arc:** CodeQL Complex Therapy
**Date:** 2026-08-16
**From:** Codex planning lane
**To:** Kiro adversarial review → Ryan Execute decision
**Branch:** `plan/2026-08-16-codeql-complex-therapy`
**Review package SHA:** `c74c7f8611ac0bf563618270c2c3244715df7d67`

## Review binding

The planning package that was reviewed and pushed before this additive handoff
is exactly `c74c7f8611ac0bf563618270c2c3244715df7d67`. It contains the
producer-identity, trust-boundary, recurring-attestation, latency-policy, and
independent SHA-lineage hardening. The handoff is the explicit carrier for
that SHA; the branch tip advances when this pointer update is committed.
Reviewers must retain the named package SHA and the final carrier SHA from the
push handoff as separate, copy-pasteable identities. No abbreviated SHA is
authoritative.

## SHA incident requiring independent review

The preceding carrier commit `9dfaa6722141b8a82bf5f2a79931501b732dec33`
temporarily named the package as `190c468a4a034831ccdf60a321bca44b93221af4`,
which was not the real hardening commit. The actual earlier hardening commit
was `190c4683f452c1a2f70ae7630269d92658eb8974`; corrective commit
`790d5fd2efb7023040cc5b1f400cd513ea554fd6` fixed the pointers. This incident
is review evidence, not an authority source.

Kiro must independently run the following from a fresh checkout or fetched
remote state, and record the output in the review:

```bash
git fetch origin
git rev-parse c74c7f8611ac0bf563618270c2c3244715df7d67
git show -s --format='%H %s' c74c7f8611ac0bf563618270c2c3244715df7d67
git log origin/main..origin/plan/2026-08-16-codeql-complex-therapy --oneline
git rev-parse origin/plan/2026-08-16-codeql-complex-therapy
```

The `git rev-parse` result for the remote branch is the current carrier
authority; no pasted final-carrier SHA is authoritative.

## Consequence

The package proposes making the three live CodeQL contexts required alongside
the existing Pylint/Pytest contexts in `Protect Main` (`19156572`), while
preserving strict freshness, bypass policy, and all existing rules. It records
GitHub's server-side current-head/producer mediation as an accepted trust
boundary, adds a separately authorized same-name/nonmatching-producer probe,
defines recurring attestation, and surfaces path-scoped gating as a
re-scoping alternative to blanket latency acceptance. It remains
planning-only: no ruleset mutation, workflow edit, implementation, or
disposable PR has been authorized or performed.

## Live evidence

Fresh planning-time PR #197 (`740424884f8921f1586f6b82648a0a290be40836`) showed:

| Context | Producer | Integration/app id |
|---|---|---:|
| `Analyze (actions)` | GitHub Actions | `15368` |
| `Analyze (python)` | GitHub Actions | `15368` |
| `CodeQL` | GitHub Advanced Security | `57789` |

Execute must revalidate these names, producers, head SHA, and URLs in the same
session immediately before any PATCH. A mismatch stops the operation.

## Review decisions required

Kiro/Ryan should explicitly decide:

1. Whether all three contexts remain the intended required set.
2. Whether requiring `CodeQL` intentionally inherits its current GHAS
   results-check failure semantics without changing thresholds or adding the
   separate native code-scanning rule.
3. Whether Ryan accepts the latency/queue trade-off of requiring CodeQL on
   ordinary PRs, including documentation-only PRs. PR #197 observed roughly
   40s for `Analyze (actions)`, 56s for `Analyze (python)`, and 3s for `CodeQL`;
   these are observations, not an SLA.
4. Whether the isolated malformed-workflow disposable control is acceptable.
   If it does not create an independent CodeQL red/missing condition while
   Pylint/Pytest remain successful, Cursor must close/delete it and obtain new
   Ryan authorization before using a different fixture.
5. Whether Ryan explicitly authorizes the producer-identity probe, only when
   exactly one CodeQL-required context is red/missing and the other four are
   green; otherwise it is not run or counted.
6. Whether Ryan selects blanket all-three latency acceptance or the
   path-scoped alternative, understanding that the latter reopens workflow and
   architecture scope.
7. The named owner, quarterly cadence, and fail-closed response for recurring
   post-Execute attestation.
8. The independent SHA-lineage check above passes, including confirmation that
   the final review uses the fetched remote tip rather than the transient typo.

## Required review reading

- [`ARCHITECTURE-codeql-complex-therapy.md`](../plans/ARCHITECTURE-codeql-complex-therapy.md)
- [`EXECUTION-codeql-complex-therapy.md`](../plans/EXECUTION-codeql-complex-therapy.md)
- [`VERIFY-codeql-complex-therapy.md`](../plans/VERIFY-codeql-complex-therapy.md)
- [`STATUS-codeql-complex-therapy.md`](../plans/STATUS-codeql-complex-therapy.md)
- [Planning-package comparison](https://github.com/alanmz-crypto/convmem/compare/main...plan/2026-08-16-codeql-complex-therapy)

## Authorization boundary

Until Ryan grants Execute, Cursor must not PATCH `Protect Main`, edit any
workflow, create a disposable PR, post a same-named producer probe, or exercise
the bypass. Kiro reviews the planning artifact first; Ryan separately grants
ruleset Execute, disposable controls, and the optional producer probe. No agent
merges `main`.

I finished: [Arc CodeQL Complex Therapy] SHA-bound hardening handoff
Next step: Kiro adversarial review of the named package and additive carrier, then Ryan's latency-policy and Execute decisions
Next lane: Kiro → Ryan
See my work: `c74c7f8611ac0bf563618270c2c3244715df7d67` and the planning-package comparison above

**TL;DR:** Review package `c74c7f8611ac0bf563618270c2c3244715df7d67` is explicitly named; Kiro must independently verify the SHA chain and fetched carrier before Ryan chooses the latency policy and authorizes Execute.
