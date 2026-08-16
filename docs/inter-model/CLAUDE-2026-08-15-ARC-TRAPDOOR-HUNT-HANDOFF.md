# Claude Handoff — Arc Trapdoor Hunt

**Date:** 2026-08-15
**From:** Codex Sol-High planning lane
**To:** Claude — independent architecture review
**Branch:** `plan/2026-08-15-dependability-provenance`
**Review target:** current head of `plan/2026-08-15-dependability-provenance`; reviewer records `git rev-parse HEAD`
**Baseline correction context:** `18cf79330be40a043ce32a399308d0761049080e`

## Purpose

This is an Arc Trapdoor Hunt: look for a failure boundary that the
dependability/provenance architecture appears to close but that recovery,
projection, replay, or operational sequencing can reopen. The arc grew out of
the dependability literature handoff, the TMA-NM provenance/laundering review,
and direct traces of the ConvMem ingest, dedupe, reconstruction, generation,
retrieval, and backup surfaces.

The package is planning-only. It authorizes no runtime code, live corpus or
Chroma mutation, Shadow/R2b operation, CG-2 activation, migration, or external
configuration change.

## Claude's blocker and the correction under review

Claude identified the material missing boundary: the architecture defined
monitor-minted assertion IDs and recursive provenance, but did not define where
the authoritative assertion-identity store persists or how it participates in
backup, restore, and Chroma rebuild. Without that boundary, a valid-looking
ID/commitment could be copied through JSONL or Chroma while the parent graph,
historical policy, or transformer recipe was absent.

The corrected architecture makes the authority boundary:

```text
CONVMEM_DATA_ROOT/provenance/
  authoritative assertion envelopes, IDs, commitments, parent edges,
  root evidence, policy history, recipe history, and directory manifest
```

The exact on-disk encoding remains a P1 implementation decision, but the
boundary cannot move outside the explicit complete-data root or be replaced by
a projection.

Read the normative correction first:

- [Authoritative assertion-store and recovery boundary](../plans/ARCHITECTURE-dependability-provenance.md#authoritative-assertion-store-and-recovery-boundary)
- [R8.1 — Store recovery is separate from item import](../plans/ARCHITECTURE-dependability-provenance.md#r81--store-recovery-is-separate-from-item-import)
- [Execution P1 provenance policy and recovery requirements](../plans/EXECUTION-dependability-provenance.md#p1--stage-1a--canonical-policy-and-representation)
- [Verification contract](../plans/VERIFY-dependability-provenance.md)

## Recovery and rebuild contract

The corrected plan requires:

1. The complete-data-v2 Restic snapshot covers the provenance registry,
   directory manifest, policy/recipe history, JSONL export, and Chroma
   projection under one explicit data-root snapshot. A legacy
   `convmem-chroma` snapshot is not provenance-store backup.
2. The registry manifest proves required files/objects, counts, canonical
   digests, policy/recipe history, and the complete assertion graph.
3. JSONL and Chroma are export/rebuild and retrieval projections. They cannot
   mint, preserve, or elevate assertion identity when the registry is absent.
4. Registry recovery is a distinct Ryan-gated bulk operation. It restores the
   whole registry directory to scratch, verifies the manifest and graph, then
   atomically publishes one recovered store generation. It is not ordinary
   item-by-item `convmem add`, JSONL re-import, Chroma rebuild, or dedupe.
5. Before publication, recovery verifies file/object hashes, ID uniqueness,
   ID/commitment agreement, every parent edge, historical policy and recipe
   availability, and registry↔JSONL↔Chroma identity/commitment agreement.
6. Missing or partial store recovery leaves live authority unchanged. The
   recovered projection remains quarantined or explicitly untrusted with an
   observable `provenance_store_unavailable` degraded state. A caller-supplied
   ID never elevates a recovered row.

The required negative controls are listed in the verification package:

- [V4g–V4j: restore-preflight path classification, separate validator, completeness, and bulk recovery](../plans/VERIFY-dependability-provenance.md#v4--representation-continuity)
- [V8h–V8l: missing/partial registry, stale history, and restore/rebuild mismatch controls](../plans/VERIFY-dependability-provenance.md#v8--laundering-and-lifecycle-faults)
- [R8: recursive missing-parent/history/cycle/mismatch behavior](../plans/ARCHITECTURE-dependability-provenance.md#r8--recursive-verification-fails-closed)

## Code evidence map for re-trace

Claude previously verified the repository claims. Please recheck the relevant
surfaces against the review target:

- [`ingest.py`](../../ingest.py) — `render_chunk()` truncates the consumed view;
  chunk metadata currently selects one `source_type`.
- [`distill.py`](../../distill.py) — distillation truncates again and
  normalization currently drops the provenance envelope.
- [`inter_model_index.py`](../../inter_model_index.py) — `source_type` and
  `author_model` are caller-supplied; the claim reaches Chroma metadata but not
  the exported unit.
- [`eval_corpus/reconstruct.py`](../../eval_corpus/reconstruct.py) — the
  reconstruction allowlist omits current provenance fields.
- [`ingest_dedupe.py`](../../ingest_dedupe.py) — exact content equality can
  suppress an independent incoming assertion.
- [`file_generation_store.py`](../../file_generation_store.py) — immutable
  metadata validation is omission-tolerant unless required keys are added.
- [`evidence.py`](../../evidence.py) — `source_trust_tier()` is retrieval
  priority, not authenticated provenance integrity.
- [`backup_workflows.py`](../../backup_workflows.py) — existing Restic
  complete-data/legacy profile boundary and restore workflow surface.
- [`docs/RECOVER.md`](../RECOVER.md) — current Tier-1 recovery guidance,
  complete-data-v2 classifications, and Chroma/JSONL rebuild semantics.

## Review-history clarification

The prior Sol-High review messages used Kiro-role and Copilot-role personas for
design/audit simulation. They are **not independent Kiro or Copilot sign-offs**.
The planning package still requires same-SHA Kiro design disposition, targeted
Copilot safety/isolation disposition, and Ryan's architecture lock. Claude's
review is an additional independent architecture input, not a replacement for
those lanes.

## Final literature pass — evidence seeds, not imported architectures

The following short selections were read with nearby context. They are evidence
seeds for the ConvMem contracts, not designs to import. Confirmations are kept
separate from the planning corrections below.

### Confirmations retained without redesign

- [Saltzer, Reed & Clark, *End-to-End Arguments in System Design*](https://web.mit.edu/saltzer/www/publications/endtoend/endtoendA4.pdf), PDF p. 2: “only with the knowledge and help of the application.” This confirms that Restic, filesystem, and Chroma health cannot replace application-level provenance validation; the plan already keeps that validator separate.
- [W3C PROV-DM §2](https://www.w3.org/TR/prov-dm/) and [PROV-CONSTRAINTS abstract](https://www.w3.org/TR/prov-constraints/): “entities and activities” and validation of a “consistent history.” ConvMem already keeps assertion identity, producer/activity, responsibility/assurance, derivation, provenance history, and validation distinct without adopting PROV/RDF.
- [Green, Karvounarakis & Tannen, *Provenance Semirings*](https://www.cis.upenn.edu/~plclub/propr/greg-slides.pdf), slides 6–10 / [PODS paper](https://dl.acm.org/doi/10.1145/1265530.1265535): “Which input tuples contribute to the presence of a tuple in the output?” This confirms that derivation annotations cannot be replaced by content equality; existing V5a–V5f cover the required independent-assertion behavior.
- [in-toto, USENIX Security 2019](https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias): “cryptographically ensures the integrity of the software supply chain.” This is a scope boundary only; no signatures, transparency log, PKI, or supply-chain attestation is imported.

### Corrections made from the probes

- [TUF §1.5.2 and §2.1.3](https://theupdateframework.github.io/specification/latest/) says the snapshot role “prevents mix-and-match attacks” and separately defines rollback protection. Recovery now selects one immutable generation/manifest commitment, rejects individually valid mixed generations, and requires a separate Ryan rollback grant for an older valid generation.
- [Pillai et al., OSDI 2014](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai) notes that application correctness is “highly dependent on subtle behaviors” of persistence. P1 and V4l now require crash interruption at every durable write/publication boundary to leave only the prior complete authority generation or one complete verified replacement.
- [Chandy & Lamport, *Distributed Snapshots*](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/Determining-Global-States-of-a-Distributed-System.pdf), printed p. 69 §3.1, requires a “meaningful” global system state. V4k makes a mixed-generation registry/JSONL/Chroma composite an explicit quarantine negative control.
- [RFC 8785 abstract and §3.2.3/§3.2.4](https://www.rfc-editor.org/info/rfc8785/) describes an “invariant format” and deterministic property sorting. P1 and V4a now require a versioned ConvMem canonicalization profile with golden vectors across implementations/library changes; JCS is not adopted wholesale.
- [RFC 9562 §5.4](https://www.rfc-editor.org/info/rfc9562/) specifies UUIDv4’s “122 bits total” random payload. Architecture, execution, and V5g now use precise UUIDv4 wording rather than promising 128 random payload bits.

### Remaining literature boundary

The literature does not establish factual truth, authenticated ConvMem origin,
or downstream action enforcement. Runtime implementation, crash injection,
canonicalization vectors, authenticated channels, and any rollback operation
remain future work under separate Ryan grants. The exact review binding remains
non-self-referential: the reviewer records `git rev-parse HEAD` at review time;
the final pushed SHA is reported outside this file.

## What Claude should return

Review the current branch head and return:

1. the exact SHA from `git rev-parse HEAD`;
2. strict `PASS`, `CONDITIONAL PASS`, or `FAIL`;
3. blocking and nonblocking findings separately;
4. whether the corrected persistence/recovery boundary closes the assertion-
   store blocker;
5. any remaining Arc Trapdoor failure involving restore, rebuild, partial
   snapshots, stale policy/recipe history, or caller-supplied identity; and
6. the smallest planning correction required if the boundary is still
   incomplete.

Do not modify runtime code, live data, Chroma, Shadow, R2b, CG-2, or external
configuration during review.

**TL;DR:** Review the authoritative registry and R8.1 first, then test whether
Restic restore and Chroma/JSONL rebuild can reopen the assertion-identity
trapdoor. Kiro/Copilot persona reviews recorded earlier are not independent
sign-offs.

I finished: Claude Arc Trapdoor Hunt handoff
Next step: Claude reviews the current branch head and returns an exact-SHA verdict
Next lane: Claude
See my work: this handoff file
