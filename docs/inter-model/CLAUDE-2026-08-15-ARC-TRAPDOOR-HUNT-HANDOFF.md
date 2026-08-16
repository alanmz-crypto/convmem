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

- [V4g–V4j: registry scope, manifest completeness, bulk recovery, and safe missing-store behavior](../plans/VERIFY-dependability-provenance.md)
- [V8h–V8l: missing store, partial snapshot, stale policy/recipe history, and restore/rebuild mismatch](../plans/VERIFY-dependability-provenance.md)
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
