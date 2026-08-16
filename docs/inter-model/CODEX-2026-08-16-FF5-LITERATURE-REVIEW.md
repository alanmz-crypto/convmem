# Arc Full Fathom Five — Literature Review Packet

## Review target and purpose

This is a review-only packet for ChatGPT, Kiro, or another independent reviewer.
The technical target is the frozen parent roadmap at
[`275ed69`](https://github.com/alanmz-crypto/convmem/commit/275ed69c6c5a9914e4dac558c07edb7da17d028b).
The current branch may contain later revert commits, but its effective planning
tree is verified equivalent to that frozen target.

This packet does not modify the parent architecture and grants no implementation,
migration, activation, data-mutation, cloud-policy, or operational authority.
The governing hierarchy remains:

```text
P0 CI Merge Gate (outside Full Fathom Five)
  → FF1/T1 Trust Baseline
  → FF2/T2 Existing Evidence + Failure-Gap Matrix
  → FF3/T3 Compatibility & Provenance
  → FF4/T4 Security, Privacy & Egress
  → FF5/T5 Operational Envelope
```

The literature is an adversarial lens against those existing contracts. It is not
authorization to add arcs, stages, handoffs, permanent gates, or implementation.

## Literature challenges

1. [Bloomfield & Rushby — *Assurance of AI Systems From a Dependability Perspective*](https://arxiv.org/abs/2407.13948), §1.1: test whether FF1 claims name their system boundary and environmental assumptions, including filesystem, Restic, Chroma, model/provider, and process ownership.
2. [Chen, Deng & Du — *Trusta*](https://arxiv.org/abs/2309.12941): test whether the existing FF1/FF2 claim/evidence matrix can express `claim → assumptions → subclaims → evidence → defeaters` without creating a second document system.
3. [Lin et al. — *A Survey on Long-Term Memory Security in LLM Agents*](https://arxiv.org/html/2604.16548v2), §5: crosswalk Write Authorization, Provenance Visibility, Principal-Scoped Retrieval, Rollbackability, and Verified Forgetting. Distinguish serving exclusion, tombstoning, and physical unrecoverability across backups and retained generations.
4. [Chen et al. — *MemSecBench*](https://arxiv.org/abs/2607.27080): test whether FF4 includes bounded end-to-end trajectories from poison/write through persistence, retrieval, consequence, repair/forgetting, and residue proof.
5. [Tan et al. — *AgentChaos*](https://arxiv.org/abs/2608.06790): require fault-injection evidence to prove that the intended fault reached the intended failure window; an untriggered injection cannot produce PASS.
6. [Jiang et al. — *When Benchmarks Age*](https://arxiv.org/abs/2510.07238v2): test whether FF2 evidence records subject revision, assumptions, and validity triggers so stale proof cannot remain sufficient.
7. [Gupta — *ReliabilityBench*](https://arxiv.org/abs/2601.06112): for stateful operations, test end-state equivalence invariants rather than exact text where textual identity is not the contract.
8. [Cymbler, Guez & Fabre — *Temporal Misgrounding in Legal RAG*](https://arxiv.org/abs/2608.09393): test whether FF3 distinguishes provenance from factual truth and preserves evidence, identity, provenance, and applicability without claiming unsupported temporal truth.

## Fresh Sol-High verdict

Fresh read-only session: `01a00870-4874-7293-a1d2-514dd1a26f92`.
It had read-only repository access and was instructed to return a verdict only.

| # | Disposition | Finding | Smallest bounded clarification |
|---|---|---|---|
| 1 | **STRENGTHEN EXISTING CONTRACT** | FF1 names assumptions and owners, but not one explicit system/environment boundary tuple. | Add system boundary and environmental assumptions to FF1 claim inputs. |
| 2 | **STRENGTHEN EXISTING CONTRACT** | FF1/FF2 have a claim/evidence matrix and defeater material, but not the complete machine-readable dependency relation. | Require `claim → assumptions → subclaims → evidence → defeaters` in the existing FF2 output. |
| 3 | **STRENGTHEN EXISTING CONTRACT** | Provenance visibility, durable acknowledgement, rollback boundaries, and retained audit assertions are bounded; principal isolation and physical forgetting are not claimed. | Add a compact FF3/FF4 crosswalk: covered, deferred, or intentionally not claimed for each primitive. |
| 4 | **STRENGTHEN EXISTING CONTRACT** | Poisoning/laundering cases exist, but not a complete bounded memory lifecycle trajectory with repair and residue proof. | Clarify FF4 security oracles to include a small set of end-to-end trajectories and explicit repair/residue outcomes. |
| 5 | **STRENGTHEN EXISTING CONTRACT** | FF2 requires an oracle and expected failure state, but not proof that an injected fault actually fired. | State that untriggered or untargeted injections are inconclusive, never PASS. |
| 6 | **STRENGTHEN EXISTING CONTRACT** | FF2 recognizes stale evidence, but evidence rows do not uniformly carry revision, assumptions, and validity trigger. | Add those fields and downgrade evidence when its validity trigger fails. |
| 7 | **STRENGTHEN EXISTING CONTRACT** | FF3 has semantic continuity and replay boundaries; FF5 does not explicitly prefer state-equivalence oracles for stateful operations. | Add end-state equivalence for restore/replay/retry/reconstruction/dedupe/migration where appropriate. |
| 8 | **STRENGTHEN EXISTING CONTRACT** | The child provenance design rejects factual-truth claims, but the parent wording still says “preserve truth.” | Replace it with “preserve evidence, identity, provenance, and applicability”; keep temporal validity separate. |

### Review interpretation

The verdict table contains eight bounded clarifications. Sol’s final prose said
“seven”; that is an arithmetic inconsistency in the verdict, not a ninth finding
or a reason to expand scope.

The strongest immediate review findings are #1, #2, #5, #6, and #8 because they
prevent ambiguous assurance claims and false PASS results. #3, #4, and #7 are
also valid wording-level refinements. None authorizes principal isolation,
verified physical deletion, a new stage, or implementation.

## Review boundary

The parent hierarchy remains frozen. These are findings against existing FF1–FF5
contracts, not automatic scope additions. Any future wording revision requires a
separate explicit planning decision and exact-SHA review. No implementation grant
is implied.

**Full Fathom Five parent structure remains frozen; literature findings are review
findings, not scope additions.**
