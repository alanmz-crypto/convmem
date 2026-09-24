# Arc ConvMem Switchboard — historical Astra review supersession closeout

Codex completed this supersession check on 2026-09-24 at Ryan's request to finish the older review without disturbing Switchboard. The September 20 Stage 1 review is preserved unchanged as historical evidence. Its BUILD-blocked verdict applies to its original planning revision, not automatically to later Switchboard revisions.

**Disposition: supersession reconciliation complete.** Later architecture and bounded implementation incorporate the original remedies. Actual runtime qualification, production admission, final integration acceptance, and demonstrated product value remain obligations of the existing Switchboard gates. This archive creates no new implementation task, authority, acceptance, or execution grant.

The original two-stage review protocol is preserved accurately: Stage 1 was completed and sealed; the separately requested Message 2 history challenge was never performed in this session. This closeout is a subsequent supersession check, not a claim to have completed that retrospective comparison. Do not reopen an obsolete build packet merely to finish its historical procedure. A specifically requested retrospective Stage 2 can still use the untouched seal.

## What was superseded

The original reviewed plan was 9b106b908b944f8bd4c3f417b576dc13884f2503. Its report hash is fc402286dbb720f3752613e3fe982c4542b168eda9609416b1dd4c51eff5c979.

The successor [architecture explicitly cites that exact report hash](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L28) and replaces the disputed contracts. The bounded fixture implementation was accepted historically at 8010fb060c2edc29e1b09d7a30b1a1da2689d489. This check independently inspected selected implementation and test source at preserved integration revision 9c6421a6891fd8a861a51f4fed410f541b53148c and retained machine-readable test artifacts for that exact revision.

The remote branches advanced during inspection: the planning branch moved from b55de5b43475595c08a00a4b1b5d2ef2aebd9796 to 67d4f5aa62415f3550fbc56a760374cf3c19ee23; the implementation branch moved from 9c6421a6891fd8a861a51f4fed410f541b53148c to 54811dd1c4fd42d84b4800baf18551d9affc25f6. Both later tips were confirmed against the remote. Selected critical functions were then compared at the later implementation tip. Several helpers were refactored, so older test acceptance is expressly not transferred to the newer tip. This is a dated snapshot, not a live status file.

## Disposition of all six findings

### F1 — authority continuity and rollback

**The old contract is superseded; the bounded remedy exists in code.** The current architecture requires cumulative authority, whole-publication compare-and-swap, and serving-only rollback to the exact current authority. In the inspected implementation, the publisher compares the entire publication digest, rejects a rollback with another authority manifest, snapshot, or semantic contract, preserves original expiry, and advances the epoch.

Evidence: [publication contract](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L1106), [current CAS guard](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/strict_projection_publisher.py#L700), [current rollback implementation](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/strict_projection_publisher.py#L1732), and retained whole-publication CAS tests at the preserved revision.

Limit: this inspection does not establish every recovery path or transfer acceptance across the current lint refactor. Those checks belong to final M11 verification and later live-recovery qualification. The test named test_rollback_refuses_foreign_authority_and_does_not_renew_expiry only exercises a genesis refusal; its name alone was not counted as proof of the full rollback claim.

### F2 — narrowing a query could create a false pass

**The old contract is superseded; the bounded remedy exists in code.** The authoritative reducer operates over the complete bound. Query selectors filter display rows without recomputing their state. The current unresolved predicate retains conflicts and current observations whose canonical verification state is not pass; ineligible checks contribute inconclusive rather than disappearing.

Evidence: [canonical state contract](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L1009), [current reducer and predicate](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/strict_evidence_state.py#L1273), and [display-only unresolved filtering](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/strict_projection.py#L3447).

Limit: the new reducer is split into helpers. A selected-source comparison is not a complete semantic-equivalence proof; current-tip acceptance remains with M11.

### F3 — provenance commitments overclaimed byte verification

**The old claim is superseded; grounding and conservative assurance exist in the bounded implementation.** The new contract separates commitment validity, byte grounding, capture class, and transformer authority. Code decodes and hashes supplied blobs, authenticates exact receipt bytes against issuer inventory, rejects contradictions, and weakens assurance for missing evidence. Synthetic fixture capture is not represented as a real historical invocation.

Evidence: [grounding and capture contract](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L823), [current blob validation](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/strict_grounding.py#L448), [receipt authentication](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/strict_grounding.py#L346), and [assurance derivation](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/strict_grounding.py#L630).

Retained tests include missing-grounding degradation, original-admission freeze, changed bytes, and exact receipt membership. Actual production capture remains unqualified and is a dependency of later production enrollment; it is not a completed part of this finding.

### F4 — lifecycle, concurrency, retirement, and release

**The incomplete design was replaced; actual host containment remains open at Gate D.** The architecture now assigns retirement to an external controller and a systemd/cgroup boundary, defines control messages, stable slots, clocks, and release ordering. The bounded code exercises controller/supervisor state machines through test adapters. Production entrypoints explicitly refuse runtime_not_qualified; an inner supervisor cannot attest its own empty domain.

Evidence: [lifecycle contract](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L1462), [outer containment owner](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L1549), [controller refusal](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/openclaw_activation_controller.py#L310), and [supervisor refusal](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/openclaw_activation_supervisor.py#L80).

Owner and closure: the existing Switchboard runtime-design/verification lane must produce actual manager, process-tree, credential, cancellation, clock, restart, and empty-domain evidence under a separate Ryan grant and Kiro-reviewed packet. Fake tests do not close that gate.

### F5 — ambient configuration, dependencies, and persistence

**The weak activation contract was replaced; actual runtime packaging and isolation remain open at Gate D.** The revised contract specifies a reviewed immutable distribution, fixed working directory, private persistence, explicit endpoints, and an outer network/privilege boundary. The fixture-only implementation and fail-closed production entrypoints prevent its mock launch policy from silently becoming production qualification.

Evidence: [selected isolation boundary](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L1565), [activation configuration](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L2598), and [Gate D acceptance boundary](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L2920).

Owner and closure: the existing runtime lane must pin or deliberately update OpenClaw, qualify its actual capabilities and complete distribution, and prove the effective tool/prompt/configuration/network/persistence inventory before activation. No installed OpenClaw test was run here.

### F6 — approval automatically ingests instead of separate approved-file add

**Still unresolved in production; explicitly assigned to Gate W.** The revised architecture selects separate governance approval and Ryan-run approved-file ingestion. It expressly acknowledges that the current CLI does not yet implement this behavior. Inspection of the later integration code confirms that the legacy approval path still calls approve_and_ingest by default. Closing this archive must not be mistaken for fixing that mismatch.

Evidence: [selected approval/admission contract](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L1820), [still-existing legacy automatic ingestion](https://github.com/alanmz-crypto/convmem/blob/54811dd1c4fd42d84b4800baf18551d9affc25f6/convmem.py#L1348), and [separate Gate W](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L2975).

Owner and closure: before production lineage enrollment, the existing coordinator must obtain the separate Gate W execution packet, Kiro sign-off, and Ryan grant. Cursor/Grok implements within that grant; independent verification must prove all approval/add/recovery/watch/index routes preserve the new contract. No legacy writer change belongs to this archival task.

## Remaining work already carried by Switchboard

- **M11 current-tip integration acceptance:** the current coordinator retains final Pylint, full pytest, repeated M8/MCP evidence, and exact-tip Kiro conformance. The later lint/refactor commits require their own evidence. The old Message 2 wait is not a new dependency for this work.
- **Gate D runtime:** actual OpenClaw authentication, distribution, containment, effective inventory, and restart/revocation evidence. Read-only source inspection and fake tests cannot pass it.
- **Gate W and Gate E production:** governed ingestion, qualified capture/enrollment, live binding completeness, latest-history recovery, and separately authorized live use remain pending.
- **Gate D-V value:** the [matched ConvMem-off/on experiment](https://github.com/alanmz-crypto/convmem/blob/67d4f5aa62415f3550fbc56a760374cf3c19ee23/docs/plans/ARCHITECTURE-openclaw-convmem-integration.md#L2954) remains required, including net owner effort and useful website outcomes. Value is still unproven.
- **Later capabilities:** child-agent inheritance, ACP, synthesis, external channels, and transcript capture keep their separate observation/design/integrity gates. This archive adds none to the current implementation scope.

These are existing obligations, not newly delegated tasks. The current Switchboard coordinator keeps the active handoff; Kiro retains design/conformance review; Ryan retains execution, live-data, merge, and promotion decisions. No parallel implementation writer or separate corrective project is created.

## Evidence actually checked

- Rechecked the original archive and report SHA-256 values and retained them byte-for-byte.
- Inspected current normative contract sections, selected source, and test bodies from exact Git revisions; stored their identities in supersession-evidence.json.
- Parsed both retained M11 M8 JUnit files and canonical outcome records at 9c6421a. Each reports 238 strict passes and 115 legacy passes, with one skip and four deselections. The retained cross-run artifact reports 29 Node passes; manifests and canonical outcome bytes match across both runs. The separate MCP JUnit reports 60 entries, corresponding to the recorded 54 tests plus six subtests, with no failures/errors/skips.
- Inspected the selected-function changes through 54811dd. Several exact ASTs match; reducer and grounding helpers were refactored. This is limited source evidence, not full conformance certification.
- Verified the remote revision identities using GitHub's API and git ls-remote. Sandboxed SSH initially rejected a system configuration file's ownership; the authorized outside-sandbox read succeeded. The mismatch in observed revisions is recorded above.

No implementation, runtime, model, live-corpus, or acceptance test was run for this closeout. Existing test records were read, not recreated. No original Stage 2 packet was opened. No product code, active architecture/execution/STATUS document, shared checkout branch, deployment, or approval was changed. The only repository additions are this standalone archival packet on its own documentation branch.

Evidence classifications: supersession of the original contracts and the existence/content of retained artifacts are **Proven**. The presence of bounded corrective mechanisms is **Strongly supported** by selected source and retained tests. Full correctness of the evolving integration tip and actual runtime/live safety remain **Unknown**, subject to the existing gates. Incremental web-development value remains **Unproven**.

## Preservation and use

- stage1-sealed.zip is the unchanged original Stage 1 archive. SHA-256: 0c879aa9a8fc59a6290c099f2d1eff4d32bf81665adea8ae465093ca1bef3ea9.
- stage1-seal.json is the unchanged seal. SHA-256: e57be341cbfb7c44cd44720f2be20fa5def07e4b627573ea019fa410f9405e15.
- The report inside the ZIP remains fc402286dbb720f3752613e3fe982c4542b168eda9609416b1dd4c51eff5c979. Relative evidence links resolve after extracting the archive. Do not edit that historical report to make its verdict appear current.
- supersession-evidence.json records this closeout's exact revisions, selected source hashes, retained evidence hashes, test-count summaries, and limits. SHA256SUMS covers the archive packet files; it is an integrity check, not an authority signature.

The separate archive branch is a remote backup and reading location. No merge is required for preservation and no PR or external message is sent by this closeout. A later handoff can link directly to this README rather than copying obsolete review conclusions into current truth.

I finished: [Arc ConvMem Switchboard] Historical-review supersession reconciliation and archival packet.
Next step: The existing Switchboard lane completes its current-tip acceptance and separately gated future work.
Next lane: Current Switchboard coordinator, Cursor/Grok, Kiro, and Ryan under their existing authority.
See my work: this README, with the unchanged sealed evidence beside it.

**TL;DR:** [Arc ConvMem Switchboard] The original build-blocked packet was superseded by revised contracts and bounded implementation. Actual runtime, production admission, final integration acceptance, and product value remain explicit existing gates. This closes the historical reconciliation without declaring those obligations finished or authorizing work.
