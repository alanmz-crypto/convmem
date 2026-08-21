# Operator runbook — CG-2 production activation

**Scope:** CG-2 production activation operations. Design A (first-cutover
rollback bootstrap) is architecture-locked 2026-08-21. This runbook does
**not** authorize production owner activation, fence, pointer publication,
`G_rb`/`G_canary` builds, GC, Shadow, or R2b until Ryan issues the matching
exact grant.

## Required grants (Ryan only)

| Step | Grant | What it unlocks |
|------|--------|-----------------|
| Execute (T1–T5) | **DONE** — Kiro PASS; Ryan grant at execution plan `6a808f1` | Prior implementation on feature branch (merged) |
| Design A Execute | Separate execution plan + Ryan grant (not yet) | Implement Design A APIs / convert-v1 / tests only |
| Legacy-only gateway soak | **DONE** — V8b PASS (grant); soak completion ACCEPTED 2026-08-21 | Production config pointing all owners `LEGACY` through serving repository |
| First generational owner (V8c) | Exact one-shot activation grant naming exact SHA, owner, `G_rb`, `G_canary` | Fence + `publish_first_cutover_active_pointer` for one owner only |
| Canary completion | Separate later Ryan decision + evidence record | Close first-canary window; not implied by V8c PASS |
| Automatic GC / compaction | Independent evidence + sub-grant | Physical deletion of inactive generations |

Silence on squash-merge = squash OK.

## Evidence artifacts

| Artifact | Path |
|----------|------|
| Architecture (Design A lock) | `docs/plans/ARCHITECTURE-cg2-production-activation.md` (restored from `e680ce8`; amended Design A 2026-08-21) |
| Execution plan (prior) | `docs/plans/EXECUTION-cg2-production-activation.md` @ `6a808f1` |
| VERIFY (mechanical + gates) | `docs/plans/VERIFY-cg2-production-activation.md` |
| Formal model map | `docs/plans/formal/cg2/README.md` |
| Property → test map | `cg2_property_map.py` |
| Rehearsal bundle | `cg2_rehearsal.py` (`collect_execute_evidence`) |

## Preflight

```bash
cd ~/Projects/convmem
convmem doctor
convmem brief --stdout-only
git fetch origin && git status
```

Require: `logical_projection` PASS, `source_reconciliation` fresh or WARN only,
no unpushed commits on the implementation branch before PR.

## Design A pre-GATE order (before Ryan V8c)

Do **not** open the V8c GATE until both generations are exact and cold-qualified:

```text
implement Design A
→ build + cold-qualify exact G_rb (convert-v1)
→ build + cold-qualify exact G_canary
→ complete independent review / evidence packet
→ Ryan V8c GATE
→ V8c PASS / one-shot activation grant
→ fence + exact first-cutover operation
→ canary window (no further serving promotion)
→ separate canary completion decision
```

Packet **before grant** must already bind:

- exact `G_rb.generation_id` + `G_rb.manifest_sha256`
- exact `G_canary.generation_id` + `G_canary.manifest_sha256`
- production pipeline fingerprints and source hashes
- embedding provenance
- qualification evidence
- exact implementation SHA

No “fill `G_canary` at cutover.” No post-grant packet amendment to discover the
target. If source / current authority / preconditions change after grant but
before publication, first-cutover **refuses**; that one-shot grant is
stale/unused; require a **new packet + new V8c grant**.

## Pause conditions (do not proceed to soak/canary/cutover)

- Any `logical_projection` FAIL or authority failure in doctor
- `source_reconciliation` stale beyond `max_reconciliation_staleness` (300s default)
- Mixed-mode proof gate FAIL (`authorized_cardinality` or `authority_safety`)
- Unexplained eval/gateway divergence during granted soak
- Missing embedding identity or ambiguous owner/alias state
- Baseline/precondition failure for grant-bound `G_rb` **before** durable fence
  (pause / refuse; no fence, no pointer, no activation)
- Baseline/precondition failure **after** durable fence (owner stays
  `FENCED_NO_POINTER`; never LEGACY; fence monotonic; pause for repair /
  fresh grant as required — do not resurrect LEGACY)
- First pointer would have `previous_generation_id=None` (refuse; Design A)
- Attempted further serving promotion during the first-canary window (refuse)

## First cutover (only after V8c one-shot grant)

1. Confirm packet binds exact `G_rb` and exact `G_canary` and grant names both.
2. Revalidate grant preconditions (source, authority, baseline structure).
3. Publish monotonic fence; then `publish_first_cutover_active_pointer` with
   `expected_active=None`, `previous_generation_id=G_rb`, target=`G_canary`.
4. If cutover fails **before** the fence is durable: refuse; leave no fence.
   If failure is discovered **after** a durable fence: remain
   `FENCED_NO_POINTER`; **never LEGACY**.
5. Do **not** promote a second serving generation for that owner during the
   canary window.
6. GC remains disabled.

## Rollback vs recovery (do not conflate)

| Need | Operation | Notes |
|------|-----------|--------|
| Restore retained prior generation | `rollback_active_pointer` | Fresh-qualify exact retained gen; may proceed after source advance; leave durable reconciliation-required for newer source; fence monotonic; never LEGACY |
| Same-pointer durability repair | `recover_active_pointer` | Exact current pointer bytes only; **never** switches generation |

Do **not** delete physical rows during rollback; GC remains disabled.
Re-run `convmem doctor` and VERIFY V6 checks after either path.

## Rollback posture (first canary — when separately granted)

1. Record active `generation_id` and `previous_generation_id` (`G_rb`) from the
   qualified pointer.
2. Use **`rollback_active_pointer`** to restore exact `G_rb` (not
   `recover_active_pointer`).
3. If live source has advanced past the retained baseline, leave
   reconciliation-required durable and enqueue desired state.
4. Do **not** resurrect LEGACY; do **not** remove the fence.
5. Re-run `convmem doctor` and VERIFY V6 checks.

## V8c vs canary completion

| Gate | Meaning |
|------|---------|
| **V8c PASS** | Complete first-owner packet accepted + exact one-shot activation grant issued |
| **Canary completion** | Separate later evidence record and Ryan decision |

Do **not** treat V8c PASS as canary completion. Do **not** mark V8c PASS in
docs until Ryan issues the grant.

## Mechanical verification (isolated — no live corpus)

```bash
python -m pytest tests/test_cg2_rehearsal.py tests/test_serving_index_repository.py \
  tests/test_mixed_mode_proof.py tests/test_logical_accounting.py \
  tests/test_source_reconciler.py -q
```

Full suite before PR:

```bash
python -m pytest -q
```

## What this runbook deliberately does **not** authorize

- Production configuration change without the matching grant
- Legacy fence or production pointer publication without V8c grant
- Building `G_rb` / `G_canary` without Design A Execute grant
- Activation manifest without V8c grant
- Automatic inactive-generation deletion or Chroma queue surgery
- Shadow / R2b work
