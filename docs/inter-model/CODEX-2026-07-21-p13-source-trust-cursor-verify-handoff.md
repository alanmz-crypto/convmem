# Codex → Cursor: create the P1.3 source-trust VERIFY plan

**From:** Codex  
**To:** Cursor  
**When:** 2026-07-21  
**Assignment:** Create and mechanically fill the P1.3 verification plan. Do not change implementation code, merge either PR, or declare the arc closed.

## Artifact context

| Who / what | Exact artifact | When / state | Why it matters | How to use it |
|------------|----------------|--------------|----------------|---------------|
| Cursor — approved P1.3 execution-plan and Codex-handoff docs PR | [#77](https://github.com/alanmz-crypto/convmem/pull/77), tip `b4853eff826aecd3575e889b27607ddc8384f3a7` on `docs/2026-07-21-p13-source-trust-handoff` | Open, green, ready for Ryan | Defines locked scope, tiers, pipeline order, eval gate, and out-of-scope work | Treat `docs/plans/EXECUTION-2026-07-21-source-trust-ranking.md` on this branch as the scope authority |
| Codex — P1.3 implementation PR | [#78](https://github.com/alanmz-crypto/convmem/pull/78), code tip `aecf5d3285992f887991400ca813c6a2066345c1` on `feat/2026-07-21-source-trust-ranking` | Open draft; GitHub pylint PASS | Implements the approved post-fusion source-trust policy | Verify this immutable revision; if the PR tip changes, stop and retarget every check before issuing evidence |
| Ryan — source-trust approval | `dec_prop_20260722_013340_dc60`, related to `dec_prop_20260707_014137_02d1` | Approved before implementation | Authorizes the locked 1.0 default and strong source tiers | Cite as decision authority; do not renegotiate the design in Verify Planning |
| Main base for implementation | `b4af44f64fdc05c955857423ac42c364ee931111` | PR #78 base after #75/#76 | Fixed comparison point for lint and retrieval evaluation | Use as the base revision, not a later moving `main`, when reproducing the implementation gate |

## Required phase initialization

Read and follow:

- `docs/PLANNING-PROTOCOL.md`
- `docs/planning/VERIFY-PLANNING.md`
- `docs/plans/VERIFY-TEMPLATE.md`
- `docs/builder-reference/manning-builder-digest.md`
- `docs/CODEX-DEEPSEEK-VERIFY.md`

Emit this before Verify work:

```text
Planning Status

Phase:        Verify Planning
Characters:   Independent Reviewer, Test-First Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro or Ryan-named lane (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust Codex chat claims alone
```

Answer the Planning OS four-question invariant explicitly. Cursor is the mechanical evidence runner, not the independent signer.

## Required output and placement

Create:

```text
docs/plans/VERIFY-source-trust-ranking.md
```

Start from `docs/plans/VERIFY-TEMPLATE.md`. The preferred placement is Cursor's existing PR #77 branch so the VERIFY plan and its canonical EXECUTION plan stay together. Verify that checkout is clean and that PR #77 still points at `b4853eff…` before editing; do not overwrite unrelated changes. Keep implementation PR #78 unchanged.

The VERIFY document must contain:

- scope-lock table;
- numbered V0…Vn checks, each with PASS / FAIL / SKIP and one-line evidence rules;
- exact mechanical, independent-signoff, and Ryan-GATE lanes;
- evidence log naming implementation SHA, runner, and ISO-8601 timestamp;
- independent Kiro (or Ryan-named lane) PASS/FAIL slot at the same implementation revision;
- explicit stop state: `Stop: Await Ryan GATE`.

## Scope lock seed

| In scope | Out of scope |
|----------|--------------|
| Source tiers and first-match precedence | Changing tier magnitudes or default weight |
| Trust application after fusion and before truncation | Evidence-graph boost changes |
| Final `retrieval_rank` after priority merge and postfilters | New ranking modules or broad refactors |
| Conditional compact/MCP trust diagnostics | Adding trust data to ordinary ask citations |
| Fixed-base golden comparison and ksweep-class smoke | Updating the committed golden fixture |
| Exact PR #78 code revision and green checks | Live `~/.config/convmem/config.toml` mutation |
| Chat remains tier 0 without ledger identity | Crush `ksweep-routing` sunset or P2 refine work |

## Checks the VERIFY plan must define

### V0 — Preconditions and immutable subject

- Run `convmem doctor`, `brief --stdout-only`, and `unresolved`.
- Prove PR #78 is open against `main`, and record exact head `aecf5d3285992f887991400ca813c6a2066345c1` plus base `b4af44f64fdc05c955857423ac42c364ee931111`.
- Prove the verification checkout is at the exact implementation SHA.
- Record GitHub check state. A later SHA invalidates evidence collected for `aecf5d3…`.

### V1 — Tier policy and omission contract

- Steering: `source_type == kiro_steering` or `.kiro/steering/` path → `0.15`.
- Ledger: explicit supported `ledger_kind`, or supported type/kind paired with `ledger_id` → `0.12`.
- Inter-model: `source_type == inter_model_doc` or `docs/inter-model/` path → `0.08`.
- Chat / other → `0`; a chat-distilled `type=decision` without ledger identity must remain tier 0.
- First match wins: steering beats ledger/inter-model; ledger beats inter-model.
- `source_trust_boost` is omitted, not emitted as zero, when trust is skipped or effective boost is zero.

### V2 — Pipeline order and score authority

Prove the implemented order is:

```text
CrossEncoder → score-only fusion → source trust → truncate top_k
  → merge ledger-priority hits → postfilters → final retrieval_rank 1..n
```

- `_fuse_retrieval_ranks` must not assign lasting `retrieval_rank`.
- Trust must see the full fused candidate pool before truncation.
- Returned ranks must be contiguous and assigned after postfilters.
- `apply_evidence_rerank` must continue to use `rank_fusion_score`; trust changes admission/order, not evidence-graph meaning.

### V3 — Trace and citation boundaries

- `QueryUnitTrace.source_trust` captures the trust-ordered stage.
- Ask compact trace and MCP search payload include `source_trust_boost` only when present.
- Ordinary ask citations do not include `source_trust_boost`.
- Raw-mode trace marks source trust skipped.

### V4 — Code placement and regression contracts

- Helpers `source_trust_tier`, `source_trust_boost`, and `apply_source_trust` live in `evidence.py`.
- No `source_trust.py`, `query_result_filters.py`, or other new leaf ranking module exists.
- `config.example.toml` documents `source_trust_weight = 1.0`; live config remains untouched.
- Run the focused tests at the exact subject SHA:

  ```bash
  python -m pytest tests/test_evidence_rerank.py tests/test_rerank_contract.py \
    tests/test_query_search_harden.py tests/test_ask_trace.py \
    tests/test_mcp_rerank_scores.py -q
  ```

- Run the full suite and the repository's JSON pylint regression gate against base `b4af44f…`.

Codex observed 39 focused tests + 8 subtests, 756 full tests + 99 subtests, and a green CI pylint check. Treat those as leads to reproduce, not as Cursor evidence.

### V5 — Fixed-base retrieval evaluation

- Generate a fresh `/tmp` baseline using base revision `b4af44f…` and `scripts/eval-retrieval.py --update-baseline` with a `/tmp` baseline path only.
- Immediately compare implementation revision `aecf5d3…` against that same `/tmp` baseline.
- Fail on any new P@k regression.
- Prove `tests/fixtures/golden_queries_baseline.json` is byte-unchanged.
- Record P@1, P@k, MRR, and per-query flips; do not require exact Codex numbers because the live corpus can drift between runs.

Codex's same-session comparison moved P@k `75.0% → 87.5%` and MRR `0.6667 → 0.7292`, with no P@k regression. Reproduce independently.

### V6 — Incident-specific ksweep smoke

- From the exact implementation checkout, query `ksweep-deploy` with `QueryUnitTrace` enabled.
- Require the real Kiro steering source to rank ahead of chat and show `+0.15`.
- Require ordinary chat rows to have no `source_trust_boost`.
- Require final ranks to be contiguous after all result filters.
- Do not reindex or mutate the corpus to manufacture a PASS; if the prerequisite steering source is missing, report FAIL/SKIP honestly and stop for Ryan.

Codex observed `/home/lauer/GitClones/willowyhollow-dev/.kiro/steering/ksweep-deploy.md` at final rank 1. This is a reproduction target, not pre-approved evidence.

### V7 — Isolation and negative assertions

- No committed golden update.
- No live config write.
- No evidence-boost magnitude change.
- No ordinary-citation schema change.
- No Crush routing sunset.
- No implementation cleanup by Cursor while verifying. A defect produces FAIL and a separate revision; the verifier does not silently fix it.

### V8 — Independent sign-off and Ryan GATE

- Request Kiro or a Ryan-named independent lane to issue written PASS/FAIL against the same exact implementation SHA.
- Independent verifier performs no cleanup or correction.
- Cursor does not self-sign, merge, record a ledger conclusion, or declare the arc closed.
- Ryan owns the final GATE and both merges.

## Evidence already available for orientation only

- PR #78 commit: `aecf5d3 Improve retrieval by trusting authoritative sources`.
- PR #78 GitHub pylint: PASS in 5m34s.
- Codex full suite: 756 passed, 99 subtests.
- Codex focused suite: 39 passed, 8 subtests.
- Codex retrieval comparison: no P@k regression; P@k 87.5%; MRR 0.7292.
- Codex ksweep smoke: steering P@1, chat unboosted, final ranks contiguous.
- Codex session Track A was indexed; search `P1.3 PR 78 source trust verification` for the implementation narrative.

None of these lines is a substitute for Cursor's mechanical evidence or independent sign-off.

## Handoff completion

After writing and mechanically filling the VERIFY artifact:

1. Commit and push every commit on Cursor's docs branch with the repository's explicit refspec rule.
2. Index the VERIFY file with `convmem index --file <exact-path>` and index Cursor's full session transcript (Track A).
3. Do not run `convmem record`; Ryan did not request a record block.
4. Stop at `Await Ryan GATE` with branch, commit, push status, mechanical verdict, and independent-signoff status.

**TL;DR:** Cursor should create and mechanically fill `VERIFY-source-trust-ranking.md` against immutable implementation SHA `aecf5d3…`, independently reproduce the tier/pipeline/eval/ksweep contracts, request same-SHA independent sign-off, and stop without code changes or merge.
