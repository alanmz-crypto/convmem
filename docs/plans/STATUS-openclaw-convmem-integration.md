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
        │       └─ Kiro PASS; exact-object absent-member projection only
        │       └─ one granted offline P0 completed at the exact read ceiling
        │       └─ immutable packet PAUSE: 98,608 unresolved rows
        │
        ├─ §18.28 / §10.26 P0 result-binding plan
        │       └─ exact result/manifest/packet identities frozen
        │       └─ Kiro PASS; independent disposition now frozen
        │
        ├─ §18.29 / §10.27 pre-acquisition + clean-replacement plan
        │       └─ disposition: technical PASS, provenance/licensing PAUSE
        │       └─ 98,608 blockers partitioned losslessly; no origin invented
        │       └─ three host-path-bearing ELFs require clean replacement
        │
        │ Kiro PASS at a10a84d → current-main reconciliation merged at 5bcc6c7
        │ → Kiro exact-main PASS at 5bcc6c7
        ├─ §18.30 / §10.28 component + ownership work-item plan
        │       └─ 1,221 component items + 19 unresolved ownership disputes
        │       └─ 98,608 IDs assigned once; twenty batches / 49 audit pages
        │       └─ PR #348 merged at d79f03c; Kiro exact-main PASS
        │
        │ → separately granted offline work-item packet + independent review
        │ → separately planned exact origins
        │ → separately granted acquisition → clean build/review/publication
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
18.27/10.25 defined a schema-v3 successor at fresh roots. Kiro passed it, Ryan granted
one collector freeze and one offline P0 execution, and Codex completed that execution
without network or retained-source access. The immutable packet binds the exact
30,421-file runtime tree, 651 evidence objects, 1,221 components, one exact `base64`
absent-member projection and 65 negative controls. It is honestly `PAUSE` and not
build-eligible because 98,608 provenance/licensing rows remain open. Sections
18.28/10.26 froze the exact result, manifest and packet for review. Kiro passed that
binding, Ryan separately authorized Claude's independent review, and the canonical
disposition at SHA-256 `45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669`
records technical `PASS`, provenance and licensing `PAUSE`, and required human counsel
without changing the packet. That review also found three captured ELF objects with
embedded `/home/lauer/miniforge3` paths; Tcl/Tk additionally carry absolute loader
paths. Sections 18.29/10.27 now define lossless pre-acquisition coverage and require a
clean replacement build from independently locked inputs. They name no authoritative
origin and authorize no request, retained-source read, repair, build, corrective
implementation or external publication. Sections 18.30/10.28 now freeze the complete
planning-only work-item model: 1,221 component items, 19 ownership-dispute items,
all 98,608 open IDs assigned once, all 1,384 nested edges assigned to their container,
and deterministic twenty-batch/49-page derived views. No work-item packet exists and
PR `#348` merged the plan at `d79f03c27976ce3460a79f168641d00f2ff291b6`;
Kiro returned exact-main PASS. That merge and review authorize no packet creation,
read or acquisition.
PR `#342`
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
| Provenance-lock schema v3 | **KIRO PASS / OFFLINE P0 PAUSE** — one exact run completed with five cumulative passes and 11,643,965,233 bytes; durable packet tree `491ae60b…` contains 98,608 open rows and is not build-eligible |
| P0 result binding and independent disposition | **KIRO PASS / REVIEW PAUSE** — §§18.28/10.26 preserve result `db755121…`, manifest `6791d33a…` and packet `491ae60b…`; disposition `45442e93…` is technical PASS but provenance/licensing PAUSE with 98,608 exact open IDs and human counsel required |
| Pre-acquisition and host-path plan | **MERGED / KIRO EXACT-MAIN PASS** at `5bcc6c7` — §§18.29/10.27 define lossless coverage, origin-candidate authority boundaries and clean replacement for three host-path-bearing ELFs; PR `#345` replaced conflicting `#344` with the same four-document plan reconstructed from exact current main; no acquisition or build is authorized |
| Component/ownership work-item plan | **MERGED / KIRO EXACT-MAIN PASS** at `d79f03c` — PR `#348` landed §§18.30/10.28 with one future seven-file offline packet, 1,221 component items, 19 unresolved ownership disputes and exact 98,608-ID/1,384-edge coverage; no packet, read or acquisition is authorized |
| Work-item schema closure | **PLAN-ONLY / KIRO REVIEW REQUIRED** — the first author-freeze preflight stopped before any packet/disposition read because v1 was not closed enough to implement; §§18.31/10.29 define fresh v2 roots, exact seven-file/nested/result schemas and deterministic `W001`–`W040` receipts; freeze and authoring remain unauthorized |
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
| Provenance-lock schema v3 P0 | **KIRO PASS / OFFLINE P0 PAUSE** | Durable packet exists and verifies; 98,608 unresolved rows block build eligibility |
| P0 result binding | **KIRO PASS / INDEPENDENT REVIEW PAUSE** | Exact disposition preserves structural PASS while provenance/licensing and build eligibility remain blocked |
| Pre-acquisition and host-path planning | **MERGED / KIRO EXACT-MAIN PASS** at `5bcc6c7` | Later origin planning and every operation remain separately gated |
| Plan PR | **MERGED / REVIEWED** — `#345` at `5bcc6c7` replaced conflicting `#344` | Exact current-main parent, four Switchboard planning documents only and byte-equality to carrier `6429d27`; planning merge grants no acquisition or build authority |
| Component/ownership work-item design | **MERGED / KIRO EXACT-MAIN PASS** at `d79f03c` | Planning PASS grants no read or packet authority; a separate Ryan grant is required before an offline author may read the immutable packet or create the seven-file bundle |
| Work-item schema-v2 correction | **PLAN-ONLY / REVIEW PENDING** | Exact-tip Kiro PASS and a new Ryan author-freeze grant are required; v1 remains uninstantiated and its absent roots cannot be reused |
| Runtime licensing/publication | **PAUSE / NOT AUTHORIZED** | Complete lock, replacement build, final packet, independent licensing PASS and separate Ryan external-action grant |
| R2b content-attestation convergence | **REVIEWED PLAN / NOT AUTHORIZED** | Independent held inventory rotation after all governed edits |
| Corrective evidence and integrated review | **NOT STARTED** | All held corrections must pass supervision |
| Merge | **BLOCKED / Ryan-owned** | Required checks green + safety review + Kiro exact-tip PASS + Ryan decision |
| Gates D/W/D-V/E/F, live data, deployment, promotion | **BLOCKED** | Separate future architecture, review and Ryan grants |

## 5. Your role

**If Ryan sent you here now:** review the exact §§18.31/10.29 work-item schema-v2
correction. Confirm that it preserves the merged §§18.30/10.28 coverage model while
closing every seven-file field/type/null/identity rule, binding exclusively to
`component-lock.jsonl`, defining a nonrecursive output tree and deterministic
`W001`–`W040` receipts at fresh v2 roots. A PASS authorizes planning only. Ryan must
separately grant a synthetic author freeze and, later, one bounded real authoring run.

Do not access a provenance origin or retained-source root, create a work-item/evidence
packet, rerun a collector, read or mutate the runtime, edit the immutable packet or
disposition, repair a binary, build a replacement, select a license, create
compliance/source bytes, apply §18.22, edit product/tests/CI/inventory, create a tag/
release/asset, rerun acceptance evidence, update PR `#342`, merge, deploy or run real
OpenClaw.

## 6. What remains before merge and before live use

1. Kiro must review the exact schema-v2 semantic parent and milestone overlay. A
   later Ryan grant may freeze one author only against a same-cardinality synthetic
   fixture and exactly forty mutants, stopping before real reads or root creation.
2. Under another exact Ryan grant, that frozen offline author may read only the
   immutable packet/disposition within named ceilings and create the exact seven-file
   v2 packet at fresh roots. An independent reviewer then proves the 1,240-item,
   98,608-ID, 1,384-edge, twenty-batch, 49-page and 19-dispute unions. No network,
   runtime or retained-source read is part of that grant.
3. A separate exact metadata/acquisition operation packet must name every allowed
   origin/root, method, redirect, parser, byte/request ceiling, checkpoint and fresh
   coordinate. Kiro review and another Ryan grant are required before any request,
   VCS fetch or retained-source read.
4. Codex may then perform only the granted bounded acquisition. An independent
   provenance/licensing reviewer and human counsel inspect the resulting immutable
   evidence. Only a later packet with zero unresolved rows plus independent technical,
   provenance and licensing PASS can become build-eligible.
5. A separately reviewed recipe/build packet must rebuild the host-path-bearing
   components and complete runtime from independently locked inputs, without copying or
   rewriting rejected binaries. Under a separate Ryan grant, a named builder creates
   the three-role replacement set once in fresh disposable roots; Codex independently
   qualifies it across two distinct build prefixes and host-path-negative controls.
6. A plan-only final packet pins every name, size, hash and coordinate. Kiro and the
   independent licensing reviewer inspect the actual final bytes. Only
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
- No schema-v3 collector rerun, runtime/evidence read, packet mutation or replacement;
  the P0 budget is exhausted and its packet is immutable.
- No review-root or disposition mutation: the canonical independent disposition exists
  at `45442e93…`, retains all 98,608 open IDs and is immutable.
- No provenance HTTP/VCS request, retained-source read or artifact parsing before a
  separately reviewed origin-by-origin acquisition plan and exact Ryan grant.
- No work-item root, packet or result before exact-tip Kiro PASS and a separate Ryan
  offline-authoring grant; that future grant cannot include network, retained-source or
  runtime access.
- No work-item omission, duplicate or reassignment: 1,221 component items, 19
  ownership-dispute items, 1,384 primary container-edge assignments and all 98,608
  open IDs remain exact. Batches and pages are derived views, never authority.
- No guessed owner, candidate-origin promotion, license selection or host-path repair
  route in a work item. `READY_FOR_REVIEW` is not access authority.
- No promotion of a package name, PURL, installed metadata/SBOM URL, search result,
  familiar registry, guessed path, ambient cache, current-host ownership or `latest`
  into artifact authority.
- No omission, duplication, reassignment or owner guessing in the 1,221-component,
  30,421-file, 1,384-edge and 98,608-unresolved baseline sets.
- No repair, resume, deletion, copy, hard-link or authority citation from schema-v1/v2
  staging; their partial output and consumed reads remain rejected PAUSE evidence.
- No CycloneDX version inference except the exact §18.27 raw-object/component/key-set/
  path-bound absent-member rule; explicit null and every other missing version remain
  `PAUSE`.
- No packet repair: packet and review leaf roots are separately atomic and immutable.
- No copying or post-build repair of the three host-path-bearing ELF objects; no
  `patchelf`, `chrpath`, binary prefix rewrite, rolling-host substitution or blanket
  absolute-path/debug exception. Clean construction from independently locked inputs
  is the only admissible remedy.
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
| Architecture | `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` §§18.22–18.31 |
| Execution | `docs/plans/EXECUTION-openclaw-convmem-integration.md` §§10.20–10.29 |
| Milestone overlay | `docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md` M11 |
| Switchboard status | `docs/plans/STATUS-openclaw-convmem-integration.md` |
| Cross-arc R2b status | `docs/plans/STATUS-r2b-capture-auth.md` |
| Implementation pull request | `https://github.com/alanmz-crypto/convmem/pull/342` |
| Replacement plan pull request | `https://github.com/alanmz-crypto/convmem/pull/345` — merged as `5bcc6c7`; Kiro exact-main PASS |
| Work-item plan pull request | `https://github.com/alanmz-crypto/convmem/pull/348` — merged as `d79f03c`; Kiro exact-main PASS |
| Superseded conflicting plan pull request | `https://github.com/alanmz-crypto/convmem/pull/344` |

## 10. Update protocol

Keep this file a current-state snapshot. Overwrite sections 3–6 when the plan is
reviewed, a grant is issued, a held correction lands, evidence changes state, or the PR
merges. Session narrative belongs in Track A. Keep one current milestone-level line.

| Date | Who | Change |
|---|---|---|
| 2026-09-28 | Codex | Closed the plan-only work-item schema v2 after the first freeze preflight found v1 under-specified; no packet/disposition read or root creation occurred. |

**TL;DR:** [Arc ConvMem Switchboard] PR `#342` preserves the accepted bounded
connector but cannot merge. The first qualified-runtime archive passed byte validation
and Kiro packet review but failed independent publication provenance/licensing review;
it remains immutable and unpublished. Kiro passed the separately gated three-role
replacement plan at `3402e62a`. Schema v1 stopped on a component initially classified
as null-version. Schema v2 passed review, but its one run proved the raw member is
absent and stopped before result or durable packet creation. Schema v3 then passed
review and its one granted offline P0 produced immutable packet tree `491ae60b…` at
the exact read ceiling. Independent disposition `45442e93…` confirms the packet is
technically exact but retains provenance/licensing `PAUSE`, human-counsel requirement
and all 98,608 blockers. PR `#345` merged the §§18.29/10.27 current-main
reconciliation at `5bcc6c7`, and Kiro passed that exact main tip. The plan defines
lossless pre-acquisition coverage and
clean replacement for three host-path-bearing ELFs without naming an authoritative
origin. Sections 18.30/10.28 now freeze the seven-role offline work-item design,
1,221 component items, 19 unresolved ownership disputes, exact 98,608-ID/1,384-edge
assignment and non-authoritative twenty-batch/49-page projections; Kiro review is
complete on merged main `d79f03c`, and no packet exists. Acquisition, binary repair, build, implementation, publication, evidence
reruns, merge, real OpenClaw and later gates remain unauthorized.
