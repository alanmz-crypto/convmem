# Review Packet: Arc Codex JSONL Production Canary P2

**Date:** 2026-09-11  
**Author:** Codex (planning/handoff lane)  
**For:** Kiro (design review) → Ryan (disposition)  
**Authorization:** Ryan, 2026-09-11 — prepare the P2 packet only

> **Arc: Codex. This is not an executable grant.** Packet preparation found a
> concrete implementation contradiction: the merged P1 harness correctly
> denies production paths and hard-refuses P2 execution. No grant JSON or
> digest is issued because the current runner could not consume it safely.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `BLOCKED_ON_KIRO` — source eligible; P2 capability seam not implemented |
| **Branch** | `docs/2026-09-11-codex-jsonl-p2-grant-packet` |
| **Tip SHA** | use the exact pushed branch tip reported in the Codex handoff |
| **Push status** | pushed to origin after commit |
| **PR** | not opened; Ryan-gated |
| **Ryan GATE** | No P2 authorization yet. Kiro first reviews this contradiction and corrective design. |

## Product consequence

The dedicated Kiro transcript is now the right size for the reviewed two-chunk
canary, but the merged P1 code cannot execute that canary. Issuing a digest now
would create false authority: the validator rejects the named live source and
production followers, while the launcher always refuses a non-preflight run.

The safe next decision is whether to add a separately reviewed, default-off P2
capability seam. The existing scratch `IsolationBoundary` and P1 hermetic
behavior must remain unchanged.

## Exact frozen source candidate

Codex measured the closed transcript read-only with
`adapters.kiro_session_jsonl.parse_complete_prefix()`. No indexing, source
write, Chroma access, provider call, configuration change, or watcher action
occurred.

| Field | Frozen observation |
|---|---|
| Source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Accepted messages | **68** (reviewed baseline window: 61–109) |
| Device / inode | `66306` / `23609783` |
| Size / complete boundary | `224318` / `224318` bytes |
| Complete-prefix SHA-256 | `1d76d2cceb523429f0865ea3db7b7a779a283219a8b43d92d02c41e0a4d7aa4e` |
| Metadata | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/session.json` |
| Metadata device / inode / size | `66306` / `23609784` / `1272` bytes |
| Metadata SHA-256 | `34cb1c5d89ef0475164269c4c86982e524db675d9a376c3c8f6a57b413f465a0` |
| File checks | both regular, canonical, non-symlink; source stable during read |

This identity is a candidate binding, not enduring authority. Any source or
metadata change before final grant issuance requires a fresh read-only freeze
and a different digest. Do not reopen or index the session.

## Merged code revision inspected

| Item | Value |
|---|---|
| Current `origin/main` / `current_code_revision()` | `9cf6a89ae66b008742ab95dee2af2c30beedd317` |
| P1 harness merge | PR #296, merge `907c828`, final Kiro-reviewed head `40b8c11` |
| P1 status synchronization | PR #297, merge `9cf6a89` |

## Concrete contradiction discovered during packet preparation

This is not a defect in the completed P1 evidence: P1 was explicitly hermetic.
It is a missing transfer seam between the reviewed P1 and P2 phases.

1. `incremental_jsonl_canary.validate_grant()` defaults to
   `known_production_roots()` and rejects the grant source, metadata, overlay,
   and every resource under a guarded production root.
2. `ProductionCanaryBoundary.from_grant()` applies the same production-root
   denial to all eleven mutable resource roles. Passing an empty override does
   not disable it because the implementation uses `forbidden_roots or
   known_production_roots()`.
3. `scripts/run-jsonl-production-canary.py` permits only `--preflight-only`.
   Every non-preflight invocation raises `canary_p2_unauthorized`.
4. The current `gate0_preflight()` checks the grant/revision/digest, one watcher
   probe, overlay existence, and false/false configuration. It does not yet
   implement the complete twelve-part P2-T2 Gate 0.
5. The module provides tested grant, capsule, fault, serving, chunking, and
   coordinator helpers, but the launcher does not orchestrate P2-T3 through
   P2-T6.

Therefore a grant naming the exact source above and the production ConvMem
followers must fail before P2. Bypassing `known_production_roots()` at the call
site would weaken the reviewed safety boundary and is not acceptable.

## Candidate grant field map — unissued

The following freezes what is already reviewable. It is deliberately not JSON
and has no SHA-256 because material fields and executable support are absent.

### Fixed candidate fields

- Schema: `1`; run once: `true`.
- Code revision: `9cf6a89ae66b008742ab95dee2af2c30beedd317`
  (or a later separately reviewed P2-capability revision).
- Source and metadata: exact identities in the table above.
- Accepted-record ceiling: `110`; append epochs: `6`; immutable prefix: `true`.
- Proposed maximum byte boundary: `355390` (current boundary plus 128 KiB),
  fail-closed before accepting a larger append. Kiro must accept or revise this
  before a final digest.
- Models: summarize/distill `llama3.1:8b` digest `46e0c10c039e`; embedding
  configured alias `nomic-embed-text`, canonical tag
  `nomic-embed-text:latest`, digest `0a109f422b47`; loopback
  `127.0.0.1:11434`. Gate 0 must re-prove installation and exact digests.
- Initial ceilings: summarize/distill/summary-embed/unit-embed `2/2/2/16`.
- Append ceilings: `1/1/1/8`; replay ceilings: `0/0/0/0`.
- Whole-run ceilings: `8/8/8/64`.
- Fault selectors: `summary_upsert`, `unit_upsert`, `units_prune`,
  `checkpoint_publish`, `dedupe_reconcile`.
- Expected new-source pre-state: no checkpoint or generation, no processed
  entry, and zero rows in both source-scoped collections.

### Planned production resources — not inspected or authorized in this phase

- Chroma: `/home/lauer/.local/share/convmem/chroma`
- Incremental state: `/home/lauer/.local/share/convmem/incremental-jsonl`
- Export: `/home/lauer/.local/share/convmem/knowledge_units.jsonl`
- Dedupe root: `/home/lauer/.local/share/convmem`
- Processed log: `/home/lauer/.local/share/convmem/processed.json`
- Writer lock: `/home/lauer/.local/share/convmem/locks/chroma_writer_gate.lock`
- Source lock:
  `/home/lauer/.local/share/convmem/locks/source/fc38a9e06cba5d32d167d4417ebb963e27f39b15d6af6f83c48c6dc012a70866.lock`
- Export lock:
  `/home/lauer/.local/share/convmem/knowledge_units.jsonl.lock`
- Processed lock: `/home/lauer/.local/share/convmem/processed.json.lock`
- Attestations: `/home/lauer/.local/share/convmem/writer_attestations`
- Census: `/home/lauer/.local/share/convmem/writer_census`

These are architecture-derived candidate paths, not fresh Gate 0 evidence.

### Fields that must remain unissued

- expiration and one-shot nonce;
- exact temporary overlay path and digest;
- exact evidence directory;
- rollback capsule path and verified digest;
- fresh zero-adoption/processed/checkpoint/state proof;
- watcher, process, writer, lock, attestation, and census proof;
- fresh local-model manifests;
- fresh restic backup identifier; and
- final grant JSON and SHA-256.

Filling any of these before the P2 capability seam is reviewed and implemented
would produce a digest for a runner that cannot execute it.

## Recommended corrective design

Choose a positive P2 capability boundary, not an exception to the P1 denial:

1. Keep `IsolationBoundary`, P1 validation defaults, normal CLI routing,
   persistent configuration, and watcher behavior unchanged.
2. Add an explicit P2 grant mode/schema whose only authority is the exact
   SHA-256-bound source and eleven resource roles. No ambient production-root
   permission and no caller-supplied empty forbidden-root bypass.
3. Make the launcher require that P2 mode, exact digest, unexpired nonce, clean
   reviewed revision, and successful full P2-T2 preflight before exposing any
   mutation stage.
4. Implement all twelve Gate 0 checks and P2-T3–T6 orchestration behind the
   canary module's existing deep interface.
5. Prove the correction hermetically with production-shaped temporary paths;
   tests must show P1 still denies production and P2 refuses every resource not
   named exactly by the grant.
6. Stop at pushed evidence for Kiro review. Do not perform the live run in the
   corrective implementation grant.

Alternative disposition: stop P2. Reinterpreting the canary as temporary
followers would not exercise the production storage/lock/serving seam named by
the reviewed plan and should require an explicit architecture change.

## Kiro review questions

1. Does the merged harness lack the executable P2 transfer seam described
   above?
2. Is a separate positive P2 capability mode the least-worst correction while
   preserving P1's production denial?
3. Is the proposed 128 KiB append byte envelope appropriately bounded alongside
   the hard 110-message and six-epoch ceilings?
4. Must the complete grant JSON/digest wait for a corrected, reviewed code
   revision and fresh Gate 0 facts?
5. Should Ryan authorize a hermetic corrective implementation pass, or stop the
   canary arc?

## Scope firewall

This packet authorizes nothing operational. Do not:

- create or consume a nonce or executable grant;
- run `--preflight-only` against production;
- access production Chroma or sidecars;
- query or modify processed/checkpoint/state authority;
- call or pull models, contact non-loopback network, or use paid providers;
- run `convmem index`, edit the source, start the watcher, or change config;
- implement the corrective seam before Ryan's separate Execute grant;
- open a PR without Ryan's instruction; or
- continue from any later canary evidence to activation.

## Related files

| Purpose | Path |
|---|---|
| Reviewed architecture | `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` |
| Reviewed execution plan | `docs/plans/EXECUTION-codex-jsonl-production-canary.md` |
| P1 evidence | `docs/plans/VERIFY-codex-jsonl-production-canary.md` |
| Current arc state | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Current routing | `docs/inter-model/LATEST.md` |

## TL;DR

- The dedicated source is eligible and frozen at 68 accepted messages.
- No executable P2 grant is issued: merged P1 rejects the exact live resources,
  the launcher hard-refuses P2, and full P2 Gate 0/orchestration is absent.
- Kiro should review the narrow positive-capability correction; Ryan then
  decides whether to authorize a hermetic corrective implementation pass or
  stop P2.
