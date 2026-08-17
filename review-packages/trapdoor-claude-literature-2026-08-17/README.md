# Trapdoor literature-review transport bundle

This is a docs-and-review-artifacts-only transport bundle for an external
Claude review. It does not modify the accepted Interlude package, construct the
Trapdoor Bridge, authorize implementation, or change runtime/live-data
surfaces.

## Accepted Interlude package

The accepted package remains the separate Interlude revision
`0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361` on
`plan/2026-08-16-trapdoor-interlude-hunt`. FF1 remains accepted at
`3c746faa47409f7def02d2fd24351fbc936a9720`.

The files below are auxiliary review material from the Trapdoor
dependability/provenance planning arc. Their embedded SHA references are
historical review targets and must not be mistaken for the accepted Interlude
revision or for implementation evidence.

## Included local artifacts

| File | Embedded review target | Purpose |
|---|---|---|
| `CLAUDE-REVIEW-HANDOFF-2026-08-15.md` | `75caa444a6274ff070b02483d8e3bbb22bb15b50` | Earlier Claude literature-review handoff. |
| `CLAUDE-REVIEW-SUPPLEMENT-2026-08-15.md` | `18cf79330be40a043ce32a399308d0761049080e` | Assertion-store recovery correction supplement. |
| `CLAUDE-REVIEW-PACKAGE-2026-08-15.zip` | Snapshot archive | Planning-only package accompanying the supplement. |
| `DEPENDABILITY-REVIEW-PACKAGE-2026-08-15.zip` | Snapshot archive | Earlier planning-only review package and handoff. |
| `KIRO-COPILOT-AUDIT-HANDOFF-2026-08-15.md` | `8f037a50c4cdce170320bbfd6160c932f7661798` | Read-only safety/isolation audit handoff. |

The external challenge must report any material finding using the accepted
FF1/FF2 row, challenged assumption, external evidence, severity, survival
decision, and smallest correction. No finding changes the Interlude package
without a later Ryan decision.
