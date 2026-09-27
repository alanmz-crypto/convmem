# Arc Brief — ConvMem Switchboard

> **Arc: ConvMem Switchboard.** Current-state snapshot. Historical milestones and
> evidence remain in the architecture/execution plans and Git history.

## 1. Product goal

Provide OpenClaw a version-adapted, read-only ConvMem connector without making
OpenClaw, prompts, generated text or connector state an authority source. The
connector may retrieve only within a startup-bound operator scope, may not write or
approve ConvMem data, and may not weaken existing ConvMem behavior.

Done for the bounded merge slice means: the exact reviewed connector is safely
integrated with current main; ordinary tests run under ordinary CI; the exact strict
fixture tests run under the immutable qualified runtime; both sets reconcile to the
complete collected universe; doctor and fenced-publication safety defects are closed;
R2b content identity converges; M8/MCP/Pylint and required GitHub checks pass; Kiro
passes the exact integrated tip; and Ryan separately authorizes merge. Real OpenClaw,
live data and later Gates D/W/D-V/E/F are not part of this slice.

## 2. System state

```text
current main 5c6a4a8 ─┐
                       ├─ PR #342 head 94f29eb ── required pytest RED
reviewed M11 evidence ─┘                            │
                                                   ├─ doctor import containment defect
                                                   ├─ fenced retry/recovery defect
                                                   ├─ qualified CI has no published runtime
                                                   └─ R2b content identity not converged

reviewed plan-only §18.22 / §10.20 at a23d843
        │
        ├─ §18.23 / §10.21 local runtime packet Kiro PASS at c63e52b
        │       └─ independent provenance/licensing FAIL / PAUSE
        │               └─ first archive immutable and rejected for publication
        │
        ├─ §18.24 / §10.22 replacement delivery-set plan
        │       └─ three roles: runtime + compliance/source + manifest
        │       └─ Kiro exact-tip PASS at 3402e62a
        │
        ├─ §18.25 / §10.23 provenance-lock schema v1
        │       └─ Kiro PASS; offline P0 stopped in disposable staging
        │       └─ one component was initially classified as null-version
        │
        ├─ §18.26 / §10.24 provenance-lock schema v2 plan
        │       └─ Kiro PASS; one granted P0 stopped fail-closed
        │       └─ raw component omits version; no result/durable packet
        │
        ├─ §18.27 / §10.25 provenance-lock schema v3 plan
        │       └─ exact-object absent-member projection only
        │       └─ fresh schema-v3 roots; no retry/read authorized
        │
        │ Kiro v3 review → separately granted fresh P0 execution
        │ → lock review → separately granted build/review/publication stages
        ▼
held doctor → publisher/recovery → CI → R2b inventory corrections
        │ fresh CI/M8/MCP/Pylint/safety evidence
        ▼
Kiro integrated-tip PASS → Ryan merge decision
```

The bounded synthetic implementation and durable evidence are preserved. Kiro passed
the PR-corrective design at overlay
`a23d84390daa6b784d61b86b112361023363aae8`. Kiro then passed the separate
runtime-delivery packet at `c63e52be138d0c101e8898dee929e33c33267672`, but Codex's
independent provenance/licensing review and Kiro's independent concurrence both
returned `PUBLICATION_ELIGIBLE=false`, `LICENSING_DISPOSITION=PAUSE`. The first
archive stays immutable, local and rejected for publication. Sections 18.24/10.22 now
define only the replacement delivery-set plan, which Kiro passed at
`3402e62a8479011814bfa76ce9e1c3269dc34350`. Sections 18.25/10.23 froze
schema v1; Kiro passed it at `5f3978525c8685f59329ccae78d184d4a1822b4b`.
Ryan then granted an offline P0 attempt. It proved the exact 30,421-file runtime tree
after a bounded collector retry, but stopped before packet publication on a component
initially classified as `version=null`. No durable v1 packet or review root exists;
its disposable `packet.work` remains rejected PAUSE evidence. Sections 18.26/10.24
defined schema v2 around that explicit-null premise. Kiro passed it, but the single
granted v2 run proved the raw component omits `version` and correctly stopped before a
result or durable packet. Its one completed runtime pass and evidence copy bring the
cumulative consumed ledger to three passes and 7,106,471,781 bytes. Sections
18.27/10.25 now define a plan-only schema-v3 successor at fresh roots. It permits only
the exact hash-bound `base64` absent-member tuple to project the immutable GitHub
revision and rejects null or any other missing version. Kiro review and a new P0
execution grant are required; no collector freeze, retry, runtime/evidence read, lock
derivation, network acquisition, build, corrective implementation or external
publication is authorized. PR `#342`
remains merge-blocked by required GitHub `pytest (3.12)`, the two safety findings and
the absent publishable qualified runtime.

## 3. What exists right now

| Surface | Current state |
|---|---|
| Pull request | **OPEN / MERGE BLOCKED** — `#342`, base `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`, head `94f29ebabee31112cccb223fd1445cb782aac6eb` |
| Required checks | CodeQL, secret scan and Pylint pass; required `pytest (3.12)` fails with 83 failures |
| Pytest failure families | 22 fixture-only inner-role nodes, 56 qualified-runtime/Unicode nodes, five R2b authority-content identity nodes |
| Doctor safety | **REVIEWED PLAN / NOT IMPLEMENTED** — invalid/import-refused MCP profile can abort all of doctor because `SystemExit` is not contained |
| Publisher safety | **REVIEWED PLAN / NOT IMPLEMENTED** — historic fenced record can match operation ID without independently proved input digest |
| CI applicability | **REVIEWED PLAN / NOT IMPLEMENTED** — §18.22/§10.20 freeze complete `U=O∪Q` ordinary/qualified execution without skip/selector weakening |
| Rejected runtime archive | **LOCAL BYTE PASS / PUBLICATION FAIL** — exact 30,421-file tree SHA-256 `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`; archive SHA-256 `6f9cfa93e3847793a42279e6ff79e07ed0b47c23d6ec7a368a4e8cb530ce594e`; immutable local diagnostic evidence only |
| Replacement delivery set | **PLAN-ONLY / KIRO PASS** at `3402e62a` — §18.24/§10.22 require a rebuilt runtime archive, compliance/corresponding-source archive and canonical manifest from a complete reviewed component lock |
| Provenance-lock schema v1 | **KIRO PASS / P0 PAUSE** at `5f397852` — exact runtime tree proved; collection stopped on a component initially classified as null-version; no durable packet/review root exists and disposable staging is rejected evidence |
| Provenance-lock schema v2 | **KIRO PASS / P0 PAUSE** at `2956f701` — the one granted run proved the raw `base64` component omits `version`; it stopped before result/ledger/manifest/durable packet creation, and its partial staging remains rejected evidence |
| Provenance-lock schema v3 | **PLAN-ONLY / KIRO REVIEW PENDING** — §18.27/§10.25 admit only the exact-object absent-member projection under fresh `schema-v3` roots; no collector freeze or execution is authorized |
| Runtime publication | **PAUSE / NOT AUTHORIZED** — independent reviews confirmed incomplete provenance/licensing; no tag, release or asset exists |
| R2b identity | 120-member governed set; committed `b716152fbf725633a55371f6acf7ed5580a704bd`, independently resolved `e060dce4eb3d51e0f4650ded8bd1aad4f2a34f4b` at pre-correction PR head |
| Historical bounded evidence | M0–M8 accepted at `8010fb0`; final M11 implementation/evidence and Kiro conformance PASS preserved at `94f29eb` |
| Real OpenClaw | **NOT EXERCISED / BLOCKED** — no installation, upgrade, runtime qualification, deployment or live use is authorized |
| Related maintenance plane | OpenClaw Watch Coverage is separate; no watch activation is authorized here |

## 4. Completion state

| Milestone | Status | Blocking condition |
|---|---|---|
| Architecture and bounded T0–T5 contract | **DONE / preserved** | Does not authorize production or real OpenClaw |
| M0–M8 bounded implementation | **TEST PASS / accepted** at `8010fb0` | Historical exact baseline/runtime only |
| M11 current-main reconstruction and evidence | **PASS / preserved** at `94f29eb` | Does not satisfy current required GitHub pytest context |
| PR creation | **DONE** — PR `#342` | Merge not authorized |
| PR required pytest | **FAIL** | Ordinary CI cannot execute qualified strict nodes correctly |
| PR-corrective plan | **KIRO PASS / preserved** at `a23d843` | Does not authorize implementation |
| Doctor import containment | **REVIEWED PLAN / NOT AUTHORIZED** | Ryan implementation grant after runtime gate |
| Fenced publication recovery | **REVIEWED PLAN / NOT AUTHORIZED** | Ryan implementation grant after runtime gate |
| CI ordinary/qualified partition | **REVIEWED PLAN / NOT AUTHORIZED** | Runtime delivery + Ryan implementation grant |
| First runtime packet | **KIRO PASS / PUBLICATION FAIL** at `c63e52b` | Archive stays immutable and rejected for publication |
| Replacement delivery-set plan | **KIRO PASS / preserved** at `3402e62a` | Does not authorize provenance execution or build |
| Provenance-lock schema v1 | **KIRO PASS / OFFLINE P0 PAUSE** | Disposable v1 staging is rejected; no in-place repair, resume or acceptance transfer |
| Provenance-lock schema v2 | **KIRO PASS / OFFLINE P0 PAUSE** | Exact absent-member refusal preserved; no result/durable packet and no in-place retry, repair, deletion or reuse |
| Provenance-lock schema v3 | **PLAN-ONLY / REVIEW PENDING** | Kiro exact-tip review, then a new schema-v3 P0 grant; no collector freeze/root/read/retry follows automatically |
| Runtime licensing/publication | **PAUSE / NOT AUTHORIZED** | Complete lock, replacement build, final packet, independent licensing PASS and separate Ryan external-action grant |
| R2b content-attestation convergence | **REVIEWED PLAN / NOT AUTHORIZED** | Independent held inventory rotation after all governed edits |
| Corrective evidence and integrated review | **NOT STARTED** | All held corrections must pass supervision |
| Merge | **BLOCKED / Ryan-owned** | Required checks green + safety review + Kiro exact-tip PASS + Ryan decision |
| Gates D/W/D-V/E/F, live data, deployment, promotion | **BLOCKED** | Separate future architecture, review and Ryan grants |

## 5. Your role

**If Ryan sent you here now:** perform Kiro's exact-tip design/scope review of the
schema-v3 semantic parent and milestone overlay. Verify §18.27/§10.25 preserve both
rejected P0 attempts and the cumulative three-pass/7,106,471,781-byte read ledger; use
new single-assignment `schema-v3` roots; admit only the exact hash-bound `base64`
component whose raw `version` member is absent; reject JSON null and every other
missing-version component; and leave every other §18.25 encoding, role, ownership,
closure, authority and review rule unchanged. Confirm Kiro PASS cannot authorize a
collector freeze, retry or runtime/evidence read.

Do not create a schema-v3 provenance root, reuse schema-v1/v2 staging, inspect or derive the component lock, make a
provenance HTTP/VCS request, download/parse artifacts, build or modify a runtime, create compliance/
source bytes, apply §18.22, edit product/tests/CI/inventory, create a tag/
release/asset, rerun acceptance evidence, update PR `#342`, merge, deploy or run real
OpenClaw.

## 6. What remains before merge and before live use

1. Kiro returns binary exact-tip PASS or FAIL on the §18.27/§10.25 schema-v3
   semantic parent and milestone overlay.
2. Ryan separately decides whether to authorize one fresh schema-v3 offline P0 run
   under exact new roots, collector identity, read ceilings and commands.
3. If P0 closes without an unresolved row, Ryan separately decides whether to authorize
   schema-bound read-only derivation of the complete
   component lock, ownership map, artifact/source/build ledger and licensing/source-
   delivery matrix.
4. Kiro and an independent provenance/licensing reviewer inspect that exact lock; no
   unresolved row is eligible for a build.
5. Under a separate Ryan grant, a named builder creates the three-role replacement set
   once in fresh disposable roots; Codex independently qualifies it. A plan-only final
   packet then pins every name, size, hash and coordinate.
6. Kiro and the independent licensing reviewer inspect the actual final bytes. Only
   after both PASS may Ryan consider a single-assignment publication grant. CI
   admission remains a later separate grant.
7. Ryan separately decides whether to grant the exact held product/test/CI/R2b
   correction.
8. Under those grants, Cursor applies the reviewed plan and stops at each held doctor,
   publisher/recovery, CI and R2b inventory commit; Codex independently inspects and
   issues commit-specific supervision.
9. Codex runs fresh doctor, crash-matrix, ordinary/qualified CI, R2b convergence,
   unchanged Pylint, two M8, seven MCP and durable-evidence verification on the exact
   integration tip and actual GitHub PR merge commit.
10. A focused independent safety/isolation audit reviews publisher recovery and CI
   containment. Kiro reviews the exact integrated tip and evidence.
11. Ryan alone decides whether PR `#342` may merge.
12. Real OpenClaw still requires deliberate update/pin, fresh capability probe, Gate D
   runtime/containment/distribution review, then Gates W/D-V/E and later promotion.

## 7. Hard stops

- No merge while required `pytest (3.12)` is red or either safety defect remains.
- No skip, xfail, marker, wildcard or failure-derived selector to make CI green.
- No change to the Pylint job/baseline/gate or the existing M8 runner.
- No import-time refusal weakening in `mcp_server.py`.
- No ordinary publish/admission while a lineage is fenced.
- No fence clearing when durable intent is present or uninspectable.
- No runtime `latest`, mutable replacement, host fallback, repair or substitution.
- No publication or CI use of the rejected §18.23 archive.
- No schema-v3 root, packet member, collector freeze, runtime/evidence read,
  provenance HTTP/VCS request or artifact parsing before Kiro v3 PASS and an exact
  Ryan P0 execution grant.
- No repair, resume, deletion, copy, hard-link or authority citation from schema-v1/v2
  staging; their partial output and consumed reads remain rejected PAUSE evidence.
- No CycloneDX version inference except the exact §18.27 raw-object/component/key-set/
  path-bound absent-member rule; explicit null and every other missing version remain
  `PAUSE`.
- No packet repair: packet and review leaf roots are separately atomic and immutable.
- No replacement build from copied rejected-runtime or rolling-host bytes; every input
  must be in the independently reviewed component lock.
- No partial delivery set: runtime, compliance/source and manifest roles are jointly
  required; the two archives must agree byte-for-byte on their shared component-lock/
  notice corpus, while the external manifest binds both without self-reference.
- No runtime release publication without exact external-action authorization.
- No external publication while `PUBLICATION_ELIGIBLE=false` or
  `LICENSING_DISPOSITION=PAUSE`; Kiro PASS does not clear licensing.
- No R2b member-set/seed/closure/route change and no live R2b operation.
- No sixth reviewed control document and no product allowlist widening.
- No duplicate hashing-helper refactor in this correction.
- No deployment, real OpenClaw, live data, watch activation, promotion or Gate
  D/W/D-V/E/F action.

## 8. Relationship to ConvMem and OpenClaw

This arc supplies the read-only runtime query path from OpenClaw to ConvMem. The
ordinary/qualified CI split is a merge-safety control for ConvMem, not runtime
qualification of real OpenClaw. Static R2b inventory convergence proves governed
source identity only; it does not authorize a capture. OpenClaw Watch Coverage remains
a separate repository-knowledge arc.

## 9. Key files

| Purpose | Path |
|---|---|
| Architecture | `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` §§18.22–18.27 |
| Execution | `docs/plans/EXECUTION-openclaw-convmem-integration.md` §§10.20–10.25 |
| Milestone overlay | `docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md` M11 |
| Switchboard status | `docs/plans/STATUS-openclaw-convmem-integration.md` |
| Cross-arc R2b status | `docs/plans/STATUS-r2b-capture-auth.md` |
| Open pull request | `https://github.com/alanmz-crypto/convmem/pull/342` |

## 10. Update protocol

Keep this file a current-state snapshot. Overwrite sections 3–6 when the plan is
reviewed, a grant is issued, a held correction lands, evidence changes state, or the PR
merges. Session narrative belongs in Track A. Keep one current milestone-level line.

| Date | Who | Change |
|---|---|---|
| 2026-09-27 | Codex | Schema-v2 P0 proved the raw `base64` component omits `version` and stopped fail-closed; schema v3 now freezes one exact-object absent-member projection under fresh roots. |

**TL;DR:** [Arc ConvMem Switchboard] PR `#342` preserves the accepted bounded
connector but cannot merge. The first qualified-runtime archive passed byte validation
and Kiro packet review but failed independent publication provenance/licensing review;
it remains immutable and unpublished. Kiro passed the separately gated three-role
replacement plan at `3402e62a`. Schema v1 stopped on a component initially classified
as null-version. Schema v2 passed review, but its one run proved the raw member is
absent and stopped before result or durable packet creation. Sections 18.27/10.25
preserve both attempts and freeze a fresh-root schema-v3 exact-object absent-member
projection; Kiro v3 review is next. Collector freeze/retry, runtime/evidence reads, provenance
acquisition, build, implementation, publication, evidence reruns, merge, real
OpenClaw and later gates remain unauthorized.
