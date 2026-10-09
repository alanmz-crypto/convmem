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
        ├─ §18.31 / §10.29 work-item schema v2
        │       └─ Kiro PASS at dea026c; freeze preflight stopped before root/read
        ├─ §18.32 / §10.30 work-item schema v3 mappings
        │       └─ Kiro PASS at 21f5acc; first governed freeze PAUSED on W026
        │       └─ one-file v3.partial preserved; no JSON/final root/real read
        ├─ §18.33 / §10.31 collision-free retry correction
        │       └─ Kiro PASS at 59ae444; granted retry froze six files successfully
        │       └─ synthetic PASS author has no real author-packet command
        ├─ §18.34 / §10.32 capability closure + held real-read design
        │       └─ exact v3 freeze bound; real-author eligibility false
        │       └─ fresh v4 capability freeze + one-pass real-read contract; plan-only
        ├─ §18.35 / §10.33 synthetic write-budget correction
        │       └─ granted preflight stopped before root/process: 64 MiB is impossible
        │       └─ Kiro PASS at 7fe2752; corrected 1-GiB cap retained
        ├─ §18.36 / §10.34 synthetic result-identity correction
        │       └─ next preflight stopped before root/source/process: hash cycle
        │       └─ Kiro PASS at 3107d6f; exact two-value adapter retained
        ├─ §18.37 / §10.35 real-command argv correction
        │       └─ next preflight stopped before root/author/process/read/write
        │       └─ Kiro PASS at be76abc; exact real argv + cwd + order-only F002
        ├─ §18.38 / §10.36 input packet-tree identity correction
        │       └─ next preflight stopped before root/author/process/input read/write
        │       └─ Kiro PASS at 991f488; exact 902-member recipe retained
        ├─ §18.39 / §10.37 interpreter startup-isolation correction
        │       └─ next preflight stopped before root/author/process/read/write
        │       └─ PR #351 merged at a3b56ab; Kiro exact-main PASS
        ├─ §18.40 / §10.38 row-zero durability retry correction
        │       └─ granted v4 process sealed f6936649… and passed 52/52 controls
        │       └─ acceptance PAUSE: row-zero file fsync before event 1 unproved
        │       └─ PR #353 merged at 073b19b1; Kiro exact-main PASS
        │       └─ rejected root immutable; fresh retry grant executed once
        ├─ §18.41 / §10.39 coordinate-parent durability-audit correction
        │       └─ setup proved row-zero durability; process reached final publication
        │       └─ audit hook rejected coordinate-parent open before rename
        │       └─ sealed a9ceaa06… partial preserved; final root absent
        │       └─ PR #355 merged at 8e4bb2b; Kiro exact-main PASS
        │       └─ granted b7a8ade… retry stopped on stdlib hard-link overconstraint
        ├─ §18.42 / §10.40 standard-library dependency-link retry correction
        │       └─ one-file 99e4939d… partial preserved; final root absent
        │       └─ only the canonical stdlib dependency reader may accept nlink >= 1
        │       └─ Kiro PASS at 946b469; granted retry sealed d399e356… final tree
        ├─ §18.43 / §10.41 self-test receipt control-order retry correction
        │       └─ process reported PASS; acceptance PAUSE on W-then-F receipt order
        │       └─ sealed 816b713… final root immutable; partial sibling absent
        │       └─ fresh 946b469… roots absent; aggregate receipt validator merged
        │       └─ PR #357 merged at c5cb7c7; Kiro exact-main PASS
        ├─ §18.44 / §10.42 capability-freeze result binding
        │       └─ granted 946b469… retry sealed candidate tree 291cf777…
        │       └─ baseline clean; 52/52; receipt F001–F010 then W001–W042
        │       └─ all durability counters one; all forbidden-access counters zero
        │       └─ PR #359 merged at 02bf65c; Kiro exact-main PASS
        │       └─ sole accepted v4 author-capability candidate; no execution grant
        ├─ §18.45 / §10.43 one-shot real-author grant boundary
        │       └─ exact accepted author + 20-member command preserved
        │       └─ packet/disposition identities + four absent roots bound
        │       └─ PR #361 merged at 8d1c017; Kiro exact-main PASS
        │       └─ PR #362 merged snapshot at ff5ce7b; Kiro exact-main PASS
        │       └─ two later grants consumed; corrected process PAUSE on W001
        ├─ §18.46 / §10.44 unresolved-ID grammar correction
        │       └─ actual `unresolved_sha256:` vs author `unresolved:sha256:`
        │       └─ old candidate immutable/ineligible for real input
        │       └─ PR #363 merged at 0a250b1; Kiro exact-main PASS
        │       └─ PR #364 merged reviewed snapshot at 4f6266e
        ├─ §18.47 / §10.45 corrected capability-freeze result binding
        │       └─ separate exact two-SHA grant consumed once
        │       └─ tree 939b8849… sealed; receipt 920c0e0e…; 52/52 F-before-W
        │       └─ PR #366 merged at dd4dd39; Kiro exact-tip + exact-main PASS
        │       └─ sole accepted corrected-v4 candidate; no execution grant
        ├─ §18.48 / §10.46 corrected one-shot real-author grant boundary
        │       └─ PR #368 acceptance snapshot merged at 16dbd79
        │       └─ corrected author + exact 20-member command preserved
        │       └─ immutable inputs + four fresh absent output roots bound
        │       └─ plan-only; Kiro exact-tip review required before Ryan's decision
        │
        │ → Kiro exact-tip review → Ryan PR/merge decision → exact-main review
        │ → separate Ryan two-SHA grant at fresh output roots, if approved
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
read or acquisition. Kiro later passed schema-v3 mapping overlay `21f5acc`. Ryan's
single synthetic-freeze grant then stopped fail-closed: the unmutated fixture cycled a
1,221-edge ring and duplicated 163 keys, so the validator returned `W026` before any
JSON write or final rename. The preserved partial contains only author
`44b59831…` at mode `0644`; no acceptance receipt exists. Sections 18.33/10.31 keep
that partial immutable, bind a fresh retry coordinate and close one exact
collision-free 1,384-edge formula plus same-cardinality `W026` mutant. Kiro passed
the correction at `59ae444`, Ryan granted one retry, and the one process froze a
six-file synthetic PASS tree `65f32f11…` with the exact clean baseline and `42/42`
controls. That immutable author accepts only `synthetic-freeze`; it has no real
`author-packet` command or real I/O/root transaction. Sections 18.34/10.32 bind the
successful artifact honestly, set real-author eligibility false and define only a
fresh v4 capability freeze plus a later one-pass real-read contract. Neither is
authorized. Kiro passed that capability plan at `4210977`, and Ryan granted only the
synthetic v4 freeze. Astra stopped its static preflight before root creation or
process execution: the mandatory 98,608 gaps and citations require at least
71,983,840 bytes in one packet and 143,967,680 across the required two copies, so the
inherited 67,108,864-byte aggregate ceiling is impossible. Sections 18.35/10.33 keep
the full transaction and all 52 controls unchanged and replace only that rejected cap
with a hard 1-GiB aggregate plus an exact pre-write ledger. Kiro passed that correction
at `7fe2752`; Ryan granted only the corrected synthetic freeze. Astra's next static
preflight stopped before root, source or process because the disposable result would
hash the receipt while the receipt ledger hashes the result. Sections 18.36/10.34
replace only the synthetic result's two receipt-binding values with exact domain-
separated predecessor identities. The unchanged real result path still requires the
actual independently reviewed v4 identities. Kiro passed that correction at
`3107d6f`; Ryan granted only the corrected synthetic freeze. Astra's next static
preflight stopped before root, author, process, read or write because `F002` requires
an exact ordered real argv that the reviewed plan never enumerated. Sections
18.37/10.35 close only the nine-key v4 command contract, exact synthetic/real argv
and cwd values, and one order-only `F002` representative. Kiro passed that correction
at `be76abc`, and Ryan granted only the fresh synthetic freeze. Astra's next static
preflight stopped before root, author, process, input read or write because the future
real reader must verify immutable packet tree `491ae60b…` but the plan did not define
its 902-member directory/file serialization. A bounded read-only derivation then
recovered the exact recipe from frozen collector `26352b39…` without opening the
packet or disposition. Sections 18.38/10.36 bind strict descendants only, distinct
closed directory/file rows, raw UTF-8 path order and compact sorted-key JSON without
a final LF while preserving the single content pass and every existing control. Kiro
passed that correction at `991f488`, and Ryan granted only the fresh synthetic freeze.
Astra's final static preflight then stopped before root, author, process, read or write:
the reviewed interpreter command would run global `site.py`, execute
`distutils-precedence.pth` and import third-party `_distutils_hack` before the author
could establish its standard-library-only boundary. Sections 18.39/10.37 preserve the
nine-key command schema, five-key environment and every existing contract while adding
literal `-S` to both argv vectors, requiring `sys.flags.no_site == 1` and shifting only
the order-only `F002` slice indices. PR `#351` squash-merged the reviewed four-document
author contract at `a3b56abd3b5fa3fafe1b3f32de744bba3eb9772c`, and Kiro returned
exact-main PASS. PR `#352` merged the descriptive current-state snapshot at
`0f84b4a983f9c1a367bc6e790d109c4342560653`. Ryan then separately granted one
fresh v4 process. It exited zero, passed its clean baseline and all 52 controls,
reproduced forecast/observed writes of 333,949,322, stayed under the 2-GiB RSS ceiling
and atomically sealed six-file tree `f6936649…` with zero real-input or external
access. Acceptance remains `PAUSE`: external setup did not explicitly prove row-zero
file `fsync` before the governed process created ledger event 1. The sealed root is
immutable rejected evidence. Sections 18.40/10.38 define only new absent retry roots
under `fdf09017…/v4`, with exclusive row-zero creation and setup plus governed file-
then-directory `fsync` before event 1. PR `#353` squash-merged the reviewed four-
document plan at `073b19b1871203d50edb84ad845530441a4ba8d4`, and Kiro returned
exact-main PASS. PR `#354` then merged the descriptive snapshot at
`6de8845473e09742bcf5a44b2da22a285ed77570`, and Ryan granted one exact retry.
Setup proved row-zero file and partial-directory durability, and the sole process
reached final publication after passing its clean baseline and all 52 controls. It
exited one because the audit hook rejected the required coordinate-parent directory
open for the pre-rename `fsync`. The final root is absent; sealed six-file partial
tree `a9ceaa06…` is immutable PAUSE evidence. Sections 18.41/10.39 define only fresh
absent `b7a8ade…/v4.partial` and sibling final roots plus an exact phase-bound,
directory-only audit exception for the pre-/post-rename parent barriers. PR `#355`
squash-merged those four reviewed planning blobs at
`8e4bb2b704ea858301207c21b71427df4975b889`, and Kiro returned exact-main PASS.
PR `#356` merged the descriptive snapshot at
`30052061942c4c016fcb305946444c0453046cb1`. Ryan then issued the one exact retry
grant. Setup created durable row zero, but the process exited before any JSON write
because the dependency reader rejected canonical stdlib module `_blake2` solely for
link count two. The final root is absent; the consumed partial contains only author
`57ecd07b…` and has canonical tree `99e4939d…`. Sections 18.42/10.40 preserve that
partial as immutable PAUSE evidence and define only fresh absent `816b713…` roots plus
a deep stdlib dependency-reader boundary. Kiro passed the correction at `946b469`,
and Ryan issued one exact retry grant. The sole no-site process accepted `_blake2`,
ran its zero-violation baseline and all 52 individual controls, wrote exactly
302,475,056 forecast/observed bytes, completed both durability barriers and sealed
six-file final tree `d399e356…`. Acceptance is still `PAUSE`: receipt `8d3ecbe0…`
serialized `W001`–`W042` before `F001`–`F010`, rather than the inherited raw-ID order
`F001`–`F010` then `W001`–`W042`, and the aggregate validator failed to reject that
drift before external `PASS`. Sections 18.43/10.41 preserve the sealed final root as
immutable rejected evidence and define only fresh absent `946b469…` roots plus the
missing exact receipt-order validator. PR `#357` squash-merged those four reviewed
planning blobs at `c5cb7c7871354b97157f392123a658a1adab4210`, and Kiro returned
exact-main PASS. The merge and review authorize no setup, root, source, read, process
or retry; every prior grant and root is non-reusable. PR `#358` then merged the
descriptive snapshot at `2c22898b9974198fedfdf31459cb3efbcdfd08ea`, and Ryan issued
one exact two-SHA retry grant. External setup created and durably revalidated row zero
once; the sole no-site process completed the clean baseline, all 52 controls, the
22-event ledger and both parent barriers, sealed six-file tree `291cf777…`, reported
`PASS` and exited zero. Receipt `3b01f77c…` orders the complete controls exactly
`F001`–`F010`, `W001`–`W042`; forecast equals observed at 323,536,730 bytes, peak RSS
is 931,274,752 bytes, every durability counter is one and every forbidden-access
counter is zero. PR `#359` squash-merged the reviewed §§18.44/10.42 binding at
`02bf65c2b4c4930da632d5a9c818f8e8047d05de`, byte-identical to reviewed overlay
`5e268c861442375e97beb70585e48b4b7c60c8af`, and Kiro returned exact-main PASS.
Under §18.44.3, tree `291cf777…` is now the sole accepted v4 author-capability
candidate for a later Ryan decision. The process result's `accepted=false` remains
historically correct because the process could not accept itself; the consumed grant
is not reusable and no real authoring is authorized.
PR `#360` squash-merged the descriptive accepted-candidate snapshot at
`ca0397c084b2616809307249212b7153d9d8ba39`. Sections 18.45/10.43 now specify the
one-shot real-author grant boundary from that exact main tip: the accepted author,
literal command, two immutable inputs, four fresh output coordinates, ceilings,
returned evidence and post-run acceptance hold. At that stage the new plan still
required Kiro review and granted no input read, root creation or process authority.
PR `#361` squash-merged the exact reviewed §§18.45/10.43 plan at
`8d1c01762d920a91667f96182fab04c4fc583e86`, byte-identical to reviewed overlay
`d7f82fbcd3afd3887d4b3764b173958d5094ee53`; all six checks passed and Kiro
returned exact-main PASS. PR `#362` then squash-merged the reviewed current-state
snapshot at `ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c`, and Kiro returned exact-main
PASS. The first later grant stopped during zero-effect read-only output-lineage
preflight; the corrected successor grant passed preflight, launched exactly one
no-site process and failed closed at `DEPENDENCY_CLOSURE` with
`Refusal: W001: input ID prefix` after reading `54,052,776` real-input bytes. Peak
RSS was `2,059,636,736`; every forbidden-access counter was zero; all four output
coordinates remain absent and no output artifact exists. Both grants are consumed
and non-reusable. Sections 18.46/10.44 now define only the plan-level correction from
the author's wrong `unresolved:sha256:` spelling to the immutable packet's exact
`unresolved_sha256:` grammar and a fresh synthetic requalification route. PR `#363`
squash-merged that exact reviewed plan at
`0a250b197ce316f058e2df6d974aedc68d3db0e4`, byte-identical to reviewed overlay
`9241543c22b3d2f25e54cabd8ccb0203ed1feca5`; all six checks passed and Kiro
returned exact-main PASS. PR `#364` merged its reviewed snapshot at `4f6266e…`.
Ryan's separate exact two-SHA synthetic-freeze grant was consumed once; the sole
process sealed immutable tree `939b8849…`, receipt `920c0e0e…` proves exact
F-before-W order and 52/52 controls, all nine durability counters are one, every
forbidden-access counter is zero and resource ceilings hold. Sections 18.47/10.45
bind that result with historical `accepted=false`. PR `#366` squash-merged the
reviewed binding at `dd4dd39ce493e06462acdd21e9dd68466149f4b5`, byte-identical to
reviewed overlay `8c27c82391b195c0807fdb9e954954aac9725f52`; Kiro exact-tip and
exact-main reviews returned PASS. Under §18.47.3, tree `939b8849…` is the sole
accepted corrected-v4 author-capability candidate. The nine durability counters and
peak RSS remain process-attested evidence at 80% confidence: merge identity preserves
the attestation but does not independently reproduce those runtime facts. No real
read, root or process is authorized.
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
| Work-item author contract | **MERGED / KIRO EXACT-MAIN PASS** at `a3b56ab` — PR `#351` landed §§18.31–18.39/§§10.29–10.37 with the closed schema/mappings, synthetic qualification, shared-core command, write ledger, packet-tree recipe and literal `-S` startup isolation; PR `#352` merged its descriptive snapshot at `0f84b4a` |
| V4 synthetic capability freeze | **OLD CANDIDATE IMMUTABLE / REAL AUTHOR ATTEMPT PAUSED** — the first process sealed rejected tree `f6936649…`; the second stopped before rename and sealed `a9ceaa06…`; the third stopped at canonical `_blake2` and left one-file partial `99e4939d…`; the fourth sealed rejected tree `d399e356…` with W-before-F receipt order; the fifth sealed tree `291cf777…`, receipt `3b01f77c…` is exactly F-before-W, baseline and 52/52 controls pass, and Kiro accepted it under §18.44. The later real attempt exposed its source's W001 unresolved-ID grammar drift, so the tree remains immutable evidence and is no longer eligible for real input |
| Real work-item author attempt | **BOTH GRANTS CONSUMED / FAIL-CLOSED W001 PAUSE** — PR `#361` landed §§18.45/10.43 at `8d1c017`; PR `#362` merged the reviewed snapshot at `ff5ce7b`; the first grant stopped before effects; the corrected successor launched once and exited `1` at `DEPENDENCY_CLOSURE` on `Refusal: W001: input ID prefix`; all four outputs remain absent and neither grant is reusable |
| W001 unresolved-ID correction | **MERGED / KIRO EXACT-MAIN PASS** at `0a250b1` — PR `#363` landed §§18.46/10.44 byte-identical to reviewed overlay `9241543`; PR `#364` merged its reviewed snapshot at `4f6266e`; actual `unresolved_sha256:<64hex>`, rejection of the author's colon-style typo and W001–W042/F001–F010 remain bound |
| Corrected V4 capability freeze | **SOLE ACCEPTED CORRECTED CANDIDATE / REAL AUTHORING SEPARATELY GATED** — Ryan's one-shot grant was consumed; partial absent; final `0555` tree `939b8849…` has six single-link `0444` members and receipt `920c0e0e…`; PR `#366` merged the exact binding at `dd4dd39`, and Kiro exact-tip plus exact-main PASS established candidate acceptance without authorizing execution. The nine durability counters and peak RSS remain process-attested at 80% confidence |
| Corrected real-author grant plan | **PLAN-ONLY / KIRO REVIEW REQUIRED** — §§18.48/10.46 bind merged-main base `16dbd79…`, accepted tree `939b8849…`, the exact twenty-member no-site command, immutable packet/disposition identities, four fresh absent single-assignment outputs, one-pass ceilings and returned evidence. The 80% durability/RSS limitation remains explicit; no content read, root creation or process is authorized |
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
| Work-item schema-v2 correction | **KIRO PASS / FREEZE PREFLIGHT PAUSE** at `dea026c` | No freeze/evidence root was created; v2 remains absent and cannot be reused or reinterpreted |
| Work-item schema-v3 mapping correction | **KIRO PASS / FIRST FREEZE PAUSE** at `21f5acc` | Failed one-file partial is immutable and non-reusable; no JSON, final freeze or real packet root exists |
| Synthetic-edge freeze retry correction | **PASS / COMPLETED** — Kiro PASS at `59ae444`; six-file tree `65f32f11…` | Synthetic semantics passed, but the frozen v3 source has no real-author command and is ineligible for real input |
| Real-author capability correction | **KIRO PASS / STATIC PREFLIGHT PAUSE** at `4210977` | Fresh v4 roots remain absent; the reviewed 64-MiB write cap is mathematically impossible and the prior grant cannot be reused |
| V4 synthetic write-budget correction | **KIRO PASS / STATIC PREFLIGHT PAUSE** at `7fe2752` | Corrected 1-GiB ledger remains frozen; receipt/result identities are cyclic under the reviewed synthetic result |
| V4 synthetic result-identity correction | **KIRO PASS / STATIC PREFLIGHT PAUSE** at `3107d6f` | Exact predecessor identities remain frozen; `F002` lacks the literal ordered real command vector needed to construct the author |
| V4 real-command argv correction | **KIRO PASS / STATIC PREFLIGHT PAUSE** at `be76abc` | Exact command contract remains frozen; the 902-member input packet-tree identity recipe was missing |
| V4 input packet-tree identity correction | **KIRO PASS / STATIC PREFLIGHT PAUSE** at `991f488` | Exact packet-tree recipe remains frozen; the literal interpreter command would execute a third-party global-site hook before the author |
| V4 interpreter startup-isolation correction | **MERGED / KIRO EXACT-MAIN PASS** at `a3b56ab` — PR `#351` | Literal `-S`, `sys.flags.no_site == 1`, fourteen-/twenty-member argv and shifted `F002` are preserved; planning merge and review grant no root or execution authority |
| V4 row-zero durability retry correction | **MERGED / KIRO EXACT-MAIN PASS** at `073b19b1` — PR `#353` | The later separately granted `fdf09017…` retry consumed that coordinate: sealed partial `a9ceaa06…` is immutable PAUSE evidence and the sibling final is absent; the merged plan and review themselves granted no setup or execution authority |
| V4 coordinate-parent durability-audit correction | **MERGED / KIRO EXACT-MAIN PASS** at `8e4bb2b` — PR `#355` | Sealed `a9ceaa06…` partial is immutable and its sibling final root is absent; fresh `b7a8ade…/v4.partial` and sibling final roots are absent; the correction permits only exact phase-bound directory handles for the pre-/post-rename parent barriers and grants no setup or execution authority |
| V4 standard-library dependency-link retry correction | **KIRO PASS / RETRY CONSUMED** at `946b469` | Consumed `b7a8ade…/v4.partial` remains immutable PAUSE evidence; the separately granted `816b713…` retry proved the canonical stdlib reader correction and sealed a final root, but that final is rejected by the later receipt-order check and transfers no acceptance |
| V4 self-test receipt control-order retry correction | **MERGED / KIRO EXACT-MAIN PASS** at `c5cb7c7` — PR `#357` | Sealed final tree `d399e356…` is immutable PAUSE evidence despite the process-reported PASS; its receipt orders `W001`–`W042` before `F001`–`F010`. Fresh `946b469…` coordinates remain absent; the merged correction adds only the already-required raw-ID aggregate receipt validator and grants no setup/read/execution authority |
| V4 capability-freeze result binding | **MERGED / KIRO EXACT-MAIN PASS** at `02bf65c` — PR `#359`; tree `291cf777…`, receipt `3b01f77c…` | One process exited zero after a clean baseline and 52/52 controls; exact F-before-W receipt order, 22 events/two nulls, nine durability counters at one, equal 323,536,730-byte forecast/observed writes, 931,274,752-byte peak RSS and zero forbidden access are bound in §§18.44/10.42. Kiro exact-main PASS established the sole accepted v4 author-capability candidate. The process result's `accepted=false` remains historical non-self-acceptance; no real read or author run is authorized |
| One-shot real-author grant boundary | **BOTH GRANTS CONSUMED / FAIL-CLOSED W001 PAUSE** — reviewed plan PR `#361` at `8d1c017`; snapshot PR `#362` at `ff5ce7b`; governing pair `31d4c919…` + `d7f82fbc…` | The first grant stopped before effects. The corrected successor passed preflight, but its sole process failed at `DEPENDENCY_CLOSURE` on W001. All four outputs remain absent; a new planning/review cycle is required before any correction or attempt |
| W001 unresolved-ID grammar correction | **MERGED / KIRO EXACT-MAIN PASS** at `0a250b1` — PR `#363` | Actual packet/disposition IDs use `unresolved_sha256:` while both synthetic producer and accepted validator used `unresolved:sha256:`. The merged plan corrects only that literal, adds the former spelling as a W001 negative case and requires a separately Ryan-granted fresh synthetic capability freeze before any later real-author plan |
| Corrected capability-freeze result binding | **MERGED / KIRO EXACT-MAIN PASS** at `dd4dd39` — PR `#366`; tree `939b8849…`, receipt `920c0e0e…` | Immutable tree `939b8849…`, receipt `920c0e0e…`, ledger `959e64ba…` and six members are bound. Kiro exact-tip PASS satisfied §18.47.3 and exact-main PASS confirmed the merge was byte-identical to overlay `8c27c823…`; the tree is the sole accepted corrected-v4 candidate. Historical `accepted=false` remains non-self-acceptance. Durability counters and peak RSS remain process-attested at 80% confidence; no real read or execution is authorized |
| Corrected one-shot real-author boundary | **PLAN-ONLY / KIRO REVIEW REQUIRED** — §§18.48/10.46 | Kiro must review the exact two-commit plan. Only after a plan PR merges and exact-main is confirmed may Ryan decide whether to issue one fresh two-SHA grant. All four `16dbd79…/491ae60b…/v3(.partial)` output coordinates remain absent and single-assignment |
| Runtime licensing/publication | **PAUSE / NOT AUTHORIZED** | Complete lock, replacement build, final packet, independent licensing PASS and separate Ryan external-action grant |
| R2b content-attestation convergence | **REVIEWED PLAN / NOT AUTHORIZED** | Independent held inventory rotation after all governed edits |
| Corrective evidence and integrated review | **NOT STARTED** | All held corrections must pass supervision |
| Merge | **BLOCKED / Ryan-owned** | Required checks green + safety review + Kiro exact-tip PASS + Ryan decision |
| Gates D/W/D-V/E/F, live data, deployment, promotion | **BLOCKED** | Separate future architecture, review and Ryan grants |

## 5. Your role

**If Ryan sent you here now:** review the exact §§18.48/10.46 semantic parent and
milestone-only overlay. Confirm that the range is two linear merge-free commits based
on PR `#368` merged main `16dbd79…`; only the four Switchboard plans change; the
overlay changes only the milestone plan; accepted corrected tree `939b8849…`, its six
members, literal twenty-member command and five-key environment remain exact; the
packet/disposition identities and four fresh absent output roots are bound; all one-
pass read/write/RSS and zero-access ceilings are unchanged; the prior durability/RSS
evidence remains explicitly process-attested at 80% confidence; and no operational
authority is introduced.

Return binary PASS/FAIL with per-claim confidence. This is a read-only design/scope
review. Do not inspect packet/disposition content, create an output root, execute the
author, open a PR, merge, acquire, build, publish, deploy or run real OpenClaw.

## 6. What remains before merge and before live use

1. Kiro reviews the exact two-commit §§18.48/10.46 plan and returns PASS/FAIL. The
   review grants no input read, root creation, author execution, PR or merge authority.
2. Ryan decides whether to open and squash-merge the reviewed planning PR. After any
   merge, Kiro confirms exact main and the STATUS snapshot is rewritten to reality.
3. Only then may Ryan decide whether to issue one exact two-SHA real-author grant. It
   must bind the reviewed plan SHAs, accepted candidate, immutable inputs, four absent
   roots, exact argv/cwd/environment, one-pass ceilings and stop conditions while
   preserving the prior 80% durability/RSS evidence boundary.
4. Only under that grant may one process read exactly `662,531,209` governed input
   bytes and attempt the unchanged seven-role output transaction once. A result must
   be bound plan-only and independently reviewed before any later gate.
5. A separate exact metadata/acquisition operation packet must name every allowed
   origin/root, method, redirect, parser, byte/request ceiling, checkpoint and fresh
   coordinate. Kiro review and another Ryan grant are required before any request,
   VCS fetch or retained-source read.
6. Codex may then perform only the granted bounded acquisition. An independent
   provenance/licensing reviewer and human counsel inspect the resulting immutable
   evidence. Only a later packet with zero unresolved rows plus independent technical,
   provenance and licensing PASS can become build-eligible.
7. A separately reviewed recipe/build packet must rebuild the host-path-bearing
   components and complete runtime from independently locked inputs, without copying or
   rewriting rejected binaries. Under a separate Ryan grant, a named builder creates
   the three-role replacement set once in fresh disposable roots; Codex independently
   qualifies it across two distinct build prefixes and host-path-negative controls.
8. A plan-only final packet pins every name, size, hash and coordinate. Kiro and the
   independent licensing reviewer inspect the actual final bytes. Only
   after both PASS may Ryan consider a single-assignment publication grant. CI
   admission remains a later separate grant.
9. Ryan separately decides whether to grant the exact held product/test/CI/R2b
   correction.
10. Under those grants, Cursor applies the reviewed plan and stops at each held doctor,
   publisher/recovery, CI and R2b inventory commit; Codex independently inspects and
   issues commit-specific supervision.
11. Codex runs fresh doctor, crash-matrix, ordinary/qualified CI, R2b convergence,
   unchanged Pylint, two M8, seven MCP and durable-evidence verification on the exact
   integration tip and actual GitHub PR merge commit.
12. A focused independent safety/isolation audit reviews publisher recovery and CI
   containment. Kiro reviews the exact integrated tip and evidence.
13. Ryan alone decides whether PR `#342` may merge.
14. Real OpenClaw still requires deliberate update/pin, fresh capability probe, Gate D
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
- No work-item root, packet or result: both prior real-author grants and the corrected
  synthetic-freeze grant are consumed. PR `#366` and Kiro PASS establish only the
  accepted candidate; they grant no real-author authority.
- No packet/disposition content read, output-parent/root creation, source creation,
  capability freeze or author process before a separate real-author plan passes exact-
  tip review, merge and exact-main confirmation and Ryan issues its exact fresh two-SHA
  grant. Tree `939b8849…` and its absent partial sibling remain immutable; no deletion,
  repair, recreation or reuse is authorized.
- No confidence upgrade from byte identity alone: the nine accepted-candidate
  durability counters and peak RSS remain process-attested at 80% until genuinely
  independent evidence is separately reviewed.
- No acceptance of both unresolved-ID spellings, alias, punctuation normalization,
  prefix translation, fallback parser or packet/disposition rewrite. The immutable
  real grammar is exactly `unresolved_sha256:<64 lowercase hexadecimal characters>`;
  the former `unresolved:sha256:` spelling must remain a W001 negative mutation.
- No real packet read through synthetic-only v3 author `8c6dd7e2…`. Corrected-v4 tree
  `939b8849…` is accepted as capability only; a separate reviewed and merged real-
  author plan plus exact Ryan real-run grant remain mandatory.
- No invented packet-tree grammar, root row, directory size/hash, prefixed file digest,
  alternate path order or extra content pass. The exact §18.38 recipe is the sole
  identity route to the immutable 902-member tree `491ae60b…`.
- No v4 Python launch without the exact §18.39 literal `-S` position, fourteen-/twenty-
  member argv arrays and `sys.flags.no_site == 1`; no environment override, wrapper,
  module hiding, `.pth` execution or site-package dependency is an alternative.
- No acceptance, mutation, deletion, copy, source reuse or repair of rejected v4 tree
  `f6936649…`. No event 1 before the fresh setup and governed row-zero file-then-
  directory `fsync` transitions complete exactly once; no later directory flush,
  byte recheck or receipt assertion substitutes for the missing ordering proof.
- No mutation, deletion, chmod, rename, copy, source reuse, execution, repair or
  acceptance of sealed partial tree `a9ceaa06…`. The coordinate parent is never a
  general content-path prefix: only two exact no-follow directory opens, one before
  and one after the atomic rename, may be reviewed for a future grant. No omitted
  parent barrier, wrapper, inherited descriptor or later inspection is equivalent.
- No mutation, deletion, chmod, rename, completion, copy, hard-link, source reuse,
  execution, repair or acceptance of one-file partial tree `99e4939d…`. A stdlib
  module link count greater than one may be accepted only by the exact canonical-
  origin dependency reader in §§18.42/10.40; it creates no authority to enumerate,
  open or infer another name and does not weaken any other single-link rule.
- No mutation, deletion, chmod, rename, copy, hard-link, source reuse, execution,
  repair or acceptance of sealed final tree `d399e356…` or receipt `8d3ecbe0…`.
  Process-reported PASS, 52 individual passing mutants and correct resource counters
  cannot override the unsorted receipt array. A successor must prove exact complete
  raw-ID order `F001`–`F010`, `W001`–`W042` before any governed output write; no
  family concatenation, numeric-suffix sort or post-seal reorder is equivalent.
- No mutation, deletion, chmod, rename, copy, hard-link, source reuse, re-execution,
  self-acceptance or real-input use of tree `291cf777…` or receipt `3b01f77c…`.
  The later W001 failure proves its source is ineligible for real input; only a fresh
  full synthetic freeze and reviewed result can create a corrected candidate.
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
| Architecture | `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` §§18.22–18.48 |
| Execution | `docs/plans/EXECUTION-openclaw-convmem-integration.md` §§10.20–10.46 |
| Milestone overlay | `docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md` M11 |
| Switchboard status | `docs/plans/STATUS-openclaw-convmem-integration.md` |
| Cross-arc R2b status | `docs/plans/STATUS-r2b-capture-auth.md` |
| Implementation pull request | `https://github.com/alanmz-crypto/convmem/pull/342` |
| Replacement plan pull request | `https://github.com/alanmz-crypto/convmem/pull/345` — merged as `5bcc6c7`; Kiro exact-main PASS |
| Work-item plan pull request | `https://github.com/alanmz-crypto/convmem/pull/348` — merged as `d79f03c`; Kiro exact-main PASS |
| Work-item author-contract pull request | `https://github.com/alanmz-crypto/convmem/pull/351` — merged as `a3b56ab`; Kiro exact-main PASS |
| Author-contract status pull request | `https://github.com/alanmz-crypto/convmem/pull/352` — merged as `0f84b4a`; descriptive snapshot only |
| Row-zero durability plan pull request | `https://github.com/alanmz-crypto/convmem/pull/353` — merged as `073b19b1`; Kiro exact-main PASS |
| Row-zero status pull request | `https://github.com/alanmz-crypto/convmem/pull/354` — merged as `6de8845`; descriptive snapshot only |
| Coordinate-parent durability plan pull request | `https://github.com/alanmz-crypto/convmem/pull/355` — merged as `8e4bb2b`; Kiro exact-main PASS |
| Coordinate-parent status pull request | `https://github.com/alanmz-crypto/convmem/pull/356` — merged as `3005206`; descriptive snapshot only |
| Control-order correction pull request | `https://github.com/alanmz-crypto/convmem/pull/357` — merged as `c5cb7c7`; Kiro exact-main PASS |
| Capability-result binding pull request | `https://github.com/alanmz-crypto/convmem/pull/359` — merged as `02bf65c`; Kiro exact-main PASS |
| Capability status pull request | `https://github.com/alanmz-crypto/convmem/pull/360` — merged as `ca0397c`; descriptive snapshot only |
| Real-author grant-plan pull request | `https://github.com/alanmz-crypto/convmem/pull/361` — merged as `8d1c017`; Kiro exact-main PASS |
| Real-author status pull request | `https://github.com/alanmz-crypto/convmem/pull/362` — merged as `ff5ce7b`; Kiro exact-main PASS |
| W001 correction-plan pull request | `https://github.com/alanmz-crypto/convmem/pull/363` — merged as `0a250b1`; Kiro exact-main PASS |
| W001 correction status pull request | `https://github.com/alanmz-crypto/convmem/pull/364` — merged as `4f6266e`; descriptive snapshot only |
| Corrected capability-result binding pull request | `https://github.com/alanmz-crypto/convmem/pull/366` — merged as `dd4dd39`; Kiro exact-tip and exact-main PASS; durability/RSS evidence remains process-attested at 80% confidence |
| Corrected capability acceptance pull request | `https://github.com/alanmz-crypto/convmem/pull/368` — merged as `16dbd79`; Kiro exact-main PASS; acceptance grants no execution |
| Superseded conflicting plan pull request | `https://github.com/alanmz-crypto/convmem/pull/344` |

## 10. Update protocol

Keep this file a current-state snapshot. Overwrite sections 3–6 when the plan is
reviewed, a grant is issued, a held correction lands, evidence changes state, or the PR
merges. Session narrative belongs in Track A. Keep one current milestone-level line.

| Date | Who | Change |
|---|---|---|
| 2026-10-09 | Codex | Added plan-only §§18.48/10.46 for one corrected real-author attempt from PR `#368` merged main `16dbd79`; four fresh outputs are absent, Kiro exact-tip review is next and execution remains Ryan-gated. |

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
complete on merged main `d79f03c`. Work-item schema v2 passed at `dea026c`, but its
freeze preflight stopped before any read/root because candidate-gap and locator
mappings remained implicit. Sections 18.32/10.30 preserve v2 absent and define fresh
schema-v3 mappings, `W001`–`W042` and a six-file synthetic freeze; Kiro passed at
`21f5acc`, but the first governed freeze stopped on baseline `W026` before any JSON,
final root or real read. Sections 18.33/10.31 preserve its one-file partial and define
the fresh collision-free 1,384-edge retry; Kiro passed at `59ae444`, and the separately
granted process produced immutable synthetic freeze tree `65f32f11…` with `42/42`
controls. The frozen source is synthetic-only, so §§18.34/10.32 hold real authoring at
`REAL_AUTHOR_ELIGIBLE=false` and define a fresh v4 capability freeze plus one-pass
real-read contract. Kiro passed that design at `4210977`, but the granted preflight
stopped before root/process creation because the mandatory two-copy lower bound is
143,967,680 bytes and therefore cannot fit under 64 MiB. Sections 18.35/10.33 preserve
the full transaction and all 52 controls under a hard 1-GiB cap with exact
forecast/observed write accounting; Kiro passed at `7fe2752`. The next static
preflight then stopped before root/source/process because the result/receipt hashes
were cyclic. Sections 18.36/10.34 replace only the synthetic result's two binding
values with exact domain-separated predecessor identities; Kiro passed at `3107d6f`.
The next granted preflight stopped before root/author/process/read/write because the
literal real argv required by `F002` was absent. Sections 18.37/10.35 close exactly
the nine-key v4 command contract, fourteen-member synthetic and twenty-member real
argv arrays, distinct cwd values and one order-only `F002` representative; Kiro passed
at `be76abc`. The next granted preflight stopped before root, author, process, input
read or write because the 902-member input packet tree had no reviewed canonical
recipe. Sections 18.38/10.36 bind the exact frozen-collector identity—663 files, 239
directories, strict descendants, closed typed rows, raw UTF-8 path order and compact
sorted-key JSON without a final LF—while preserving the one-pass ceiling and all 52
controls; Kiro passed at `991f488`. The next static preflight stopped before any root,
author, process, read or write because global site initialization would import
third-party `_distutils_hack`. Sections 18.39/10.37 add only literal `-S`, require
`sys.flags.no_site == 1`, close fourteen-/twenty-member argv and shift `F002` slices
mechanically; every schema, environment key, control and ceiling remains unchanged.
PR `#351` merged that complete author contract at `a3b56ab`, and Kiro returned
exact-main PASS. PR `#352` merged the descriptive snapshot at `0f84b4a`. The next
granted v4 process sealed six-file tree `f6936649…`, passed a clean baseline and all
52 controls within every ceiling and performed no real-input/external access, but
acceptance remains `PAUSE` because setup did not prove row-zero file durability before
event 1. Sections 18.40/10.38 preserve that root as immutable rejected evidence and
define fresh absent retry roots plus exact setup and governed file-then-directory
`fsync` ordering. PR `#353` merged that plan at `073b19b1`, and Kiro returned exact-
main PASS; PR `#354` merged its snapshot at `6de8845`. Ryan's separately granted
retry proved row-zero durability and passed all 52 controls, but finalization failed
closed before rename because the audit hook rejected the coordinate-parent directory
open. Sections 18.41/10.39 preserve sealed partial `a9ceaa06…`, keep the sibling final
absent, bind fresh absent `b7a8ade…` roots and define only an exact directory-handle
exception for the pre-/post-rename parent barriers. PR `#355` merged that correction
at `8e4bb2b`, and Kiro returned exact-main PASS; PR `#356` merged the snapshot at
`3005206`. Ryan's separately granted retry proved setup durability but stopped before
any JSON output because the dependency reader applied the general single-link rule to
canonical stdlib `_blake2`, whose regular-file inode has link count two. Sections
18.42/10.40 preserve one-file partial tree `99e4939d…`, keep the sibling final absent,
bind fresh absent `816b713…` roots and permit `st_nlink >= 1` only inside the exact
canonical-origin stdlib dependency reader. Every other reader, all 52 controls and all
ceilings remain unchanged. The granted successor sealed final tree `d399e356…` and
reported `PASS`, but receipt `8d3ecbe0…` orders W controls before F controls, so the
tree remains immutable rejected PAUSE evidence. PR `#357` merged the exact aggregate
receipt-order correction at `c5cb7c7`, and Kiro returned exact-main PASS. Fresh
`946b469…` roots were then consumed by one exact Ryan-granted retry. The sole process
sealed six-file candidate tree `291cf777…`; receipt `3b01f77c…` is exactly F-before-W,
the baseline and all 52 controls pass, forecast equals observed, every durability
counter is one and every forbidden-access counter is zero. PR `#359` merged the exact
§§18.44/10.42 binding at `02bf65c`, and Kiro exact-main PASS established tree
`291cf777…` as the sole accepted v4 author-capability candidate. The process result's
`accepted=false` remains historical non-self-acceptance. PR `#360` merged the
descriptive snapshot at `ca0397c`. Sections 18.45/10.43 now bind the exact accepted
author, twenty-member command, immutable inputs, four absent output coordinates,
ceilings and returned evidence for a possible one-shot run. PR `#361` merged that
exact plan at `8d1c017`, byte-identical to reviewed overlay `d7f82fb`, all six checks
passed and Kiro returned exact-main PASS; PR `#362` merged its reviewed snapshot at
`ff5ce7b`. Two later grants are now consumed: the first stopped before effects, and
the corrected successor launched once but failed closed on W001 after 54,052,776
input bytes, with zero forbidden access and all four outputs absent. Sections
18.46/10.44 isolate the defect to the accepted source's colon-style unresolved-ID
literal, bind the immutable packet's exact `unresolved_sha256:` grammar and require a
fresh synthetic capability freeze before any later real-author plan. PR `#363` merged
that exact plan at `0a250b1`, byte-identical to reviewed overlay `9241543`; all six
checks passed and Kiro returned exact-main PASS. PR `#364` merged the reviewed
snapshot at `4f6266e`. Ryan's separate one-shot synthetic-freeze grant then sealed
tree `939b8849…` with receipt `920c0e0e…`, 52/52 controls, all durability counters
at one and zero forbidden access. PR `#366` merged the exact §§18.47/10.45 binding at
`dd4dd39`, byte-identical to overlay `8c27c823`; Kiro exact-tip and exact-main PASS
established tree `939b8849…` as the sole accepted corrected-v4 capability candidate.
The process result's `accepted=false` remains historical non-self-acceptance. The nine
durability counters and peak RSS remain process-attested at 80% confidence. PR `#368`
merged the acceptance snapshot at `16dbd79`. Sections 18.48/10.46 now bind the exact
corrected author, twenty-member command, immutable inputs, four fresh absent output
coordinates, ceilings and returned evidence for one possible later process. Kiro
exact-tip review is next; this plan authorizes no real read, root or process.
Acquisition, binary
repair, build, implementation, publication, evidence
reruns, merge, real OpenClaw and later gates remain unauthorized.
