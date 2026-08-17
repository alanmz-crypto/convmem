# Arc Trapdoor Hunt
## Claude review supplement — assertion-store recovery correction

This supplement supersedes the earlier Claude handoff's revision reference.
It supplies the material Claude identified as missing.

### Exact review target

- Branch: `plan/2026-08-15-dependability-provenance`
- Exact pushed revision: `18cf79330be40a043ce32a399308d0761049080e`
- Status at Sol-High handoff: clean and synchronized with upstream
- Scope: planning documents only; no runtime or live-data changes

### Claude's blocking finding

The earlier plan defined monitor-minted assertion IDs and recursive fail-closed
verification, but did not define where the authoritative assertion registry
lives or how that registry survives Restic restore, JSONL export/re-import,
Chroma rebuild, or disaster recovery.

That gap could produce two bad outcomes:

1. A legitimate restore could make the entire corpus appear untrusted because
   parent rows were unavailable.
2. A recovery path could accept caller-supplied IDs as fresh authority and
   recreate the identity-aliasing vulnerability the design was intended to
   prevent.

### What the corrected plan now says

The corrected architecture defines:

- authoritative registry boundary: `CONVMEM_DATA_ROOT/provenance/`;
- assertion IDs and parent commitments as registry authority, not Chroma
  metadata or content-derived `ledger_ids.py` values;
- Restic complete-data-v2 coverage for the registry, its manifest,
  policy/recipe history, JSONL export, and Chroma projection;
- Chroma and JSONL as projections/rebuild surfaces, not independent authority
  stores;
- registry recovery as a distinct Ryan-gated bulk operation;
- recovery of the complete registry directory and graph in a scratch target
  before publication;
- directory-manifest completeness, cross-surface identity/commitment checks,
  policy/recipe availability checks, and generation consistency checks;
- item-by-item JSONL import or Chroma rebuild may populate only quarantined
  staging until the registry and all cross-surface checks pass;
- missing stores, partial snapshots, stale history, truncated files, extra
  unclassified state, and restore/rebuild mismatch remain quarantined;
- recovery never globally rewrites a valid corpus to untrusted merely because
  a store is unavailable, and never elevates recovered rows from caller-supplied
  IDs without verified registry evidence;
- an individual unresolved parent still receives the normal R8 per-assertion
  `untrusted` result.

The main sections to review first are:

1. Architecture § “Authoritative assertion store and recovery boundary”
   (around line 91);
2. Architecture R8.1 “Store recovery is separate from item import”
   (around line 372);
3. the corresponding Execution recovery/Grant boundaries;
4. the VERIFY recovery negative controls.

### Repository evidence for Claude to recheck

The corrected plan asks Claude to verify the recovery design against:

- `ingest.py` — rendered/truncated generation input;
- `distill.py` — second truncation and missing envelope;
- `inter_model_index.py` — caller labels and Chroma-only `source_type`;
- `eval_corpus/reconstruct.py` — canonical metadata allowlist;
- `ingest_dedupe.py` — content-only exact suppression;
- `file_generation_store.py` — immutable metadata validation behavior;
- `evidence.py` — heuristic `source_trust_tier()` classification;
- `backup_workflows.py` and `docs/RECOVER.md` — existing backup/recovery
  surfaces and operational precedent;
- the complete-data-v2 backup architecture — required coverage boundary.

The key question is whether the proposed registry recovery operation is
complete enough to prevent both accidental availability downgrades and
identity-aliasing during real restore/rebuild operations.

### Review-status correction

The prior Sol-High Kiro-role and Copilot-role reviews were persona reviews,
not independent Kiro or Copilot model dispositions. They must not be reported
as independent sign-off. This corrected revision is being supplied to Claude
for independent challenge; actual independent review remains a separate
future gate.

### Nonblocking items now surfaced for Claude

Please also assess:

- whether `trusted` transformer membership should be a locked allowlist backed
  by preservation-contract tests;
- whether recursive verification needs memoized verified-subgraph caching before
  P3 retrieval use;
- whether P2 should split rendering, inter-model indexing, and projection/
  reconstruction into separate grants;
- whether the planned `provenance.py` should be distinguished from the
  existing unrelated `eval_provenance.py`.

### Requested Claude response

Return a verdict tied to exact revision
`18cf79330be40a043ce32a399308d0761049080e`:

- PASS, CONDITIONAL PASS, or FAIL;
- blocking versus nonblocking findings;
- whether the assertion-store recovery boundary closes the original blocker;
- any remaining ambiguity in restore, reconstruction, or publication;
- whether P1/P2/P3 are sufficiently isolated for implementation.

Do not infer that the plan's proposed registry already exists in production.

