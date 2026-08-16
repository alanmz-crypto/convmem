# Codex Handoff — CodeQL Complex Therapy Planning

**Arc:** CodeQL Complex Therapy
**Date:** 2026-08-16
**From:** Codex planning lane
**To:** Kiro adversarial review → Ryan Execute decision
**Branch:** `plan/2026-08-16-codeql-complex-therapy`
**Review package SHA:** `45046fafd0aa918042a89ae7e9a85fb707ce55d1`

## Review binding

The planning package that was reviewed and pushed before this additive handoff
is exactly `45046fafd0aa918042a89ae7e9a85fb707ce55d1`. The handoff is the
explicit carrier for that SHA; the branch tip advances when this handoff and
the latency addendum are committed. Reviewers must retain the named package
SHA and the final carrier SHA from the push handoff as separate, copy-pasteable
identities. No abbreviated SHA is authoritative.

## Consequence

The package proposes making the three live CodeQL contexts required alongside
the existing Pylint/Pytest contexts in `Protect Main` (`19156572`), while
preserving strict freshness, bypass policy, and all existing rules. It remains
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

## Required review reading

- [`ARCHITECTURE-codeql-complex-therapy.md`](../plans/ARCHITECTURE-codeql-complex-therapy.md)
- [`EXECUTION-codeql-complex-therapy.md`](../plans/EXECUTION-codeql-complex-therapy.md)
- [`VERIFY-codeql-complex-therapy.md`](../plans/VERIFY-codeql-complex-therapy.md)
- [`STATUS-codeql-complex-therapy.md`](../plans/STATUS-codeql-complex-therapy.md)
- [Planning-package comparison](https://github.com/alanmz-crypto/convmem/compare/main...plan/2026-08-16-codeql-complex-therapy)

## Authorization boundary

Until Ryan grants Execute, Cursor must not PATCH `Protect Main`, edit any
workflow, create a disposable PR, or exercise the bypass. Kiro reviews the
planning artifact first; Ryan separately grants ruleset Execute and disposable
controls. No agent merges `main`.

I finished: [Arc CodeQL Complex Therapy] SHA-bound planning handoff and latency decision gate
Next step: Kiro adversarial review of the named package and additive carrier, then Ryan’s Execute decision
Next lane: Kiro → Ryan
See my work: `45046fafd0aa918042a89ae7e9a85fb707ce55d1` and the planning-package comparison above

**TL;DR:** Review package `45046fafd0aa918042a89ae7e9a85fb707ce55d1` is explicitly named; Kiro must review it plus the additive latency gate before Ryan authorizes Execute.
