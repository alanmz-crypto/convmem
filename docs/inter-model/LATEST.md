# Latest cross-model handoff (single pointer)

**Updated:** 2026-09-13

This file is intentionally short. It routes a new session to current state; it
is not a status log, decision ledger, or archive. For live corpus and service
state, run `convmem brief --stdout-only`. For project and arc state, use the
cross-arc snapshot and the linked arc brief below.

## Current routing

- **Trapdoor Hunt / issue #268 — bounded export compaction:** Cursor Execute
  C0–C7 is on `fix/2026-09-13-watch-oom-bounded-export-compaction`. Copilot
  audit FAILed exact tip `b2735c4a81599061786b965c9c7841035ed621e7`. A bounded
  corrective for findings 1–5 (no-op identity, descriptor-safe SQLite scratch,
  post-chmod fsync, mostly-unique rewrite RSS, LATEST/hash refresh) preserves
  that FAIL tip as an ancestor. Next: Copilot re-audit of the new exact tip.
  No PR, live compaction, watcher/P2, grant, merge, or activation. Plan:
  [`EXECUTION-watch-oom-bounded-export-compaction.md`](../plans/EXECUTION-watch-oom-bounded-export-compaction.md).
- **Arc Codex — Kiro JSONL production integration:** the reviewed, hermetic
  coordinator and live-safe canary runtime are on `main` through squash-merged
  PR #301 (`8983a6fc…`) and remain disabled. Kiro's post-merge audit PASSed the
  final tree. A fresh 68-message source freeze at packet tip `27518aa…` also
  received Kiro PASS, but no executable grant or digest was issued. Grant-packet
  progression is paused while issue #268's shared export-compaction OOM is
  corrected and reviewed. No Claude re-review, live source, Gate 0, P2 run,
  replacement grant/digest, new P2 PR, or activation is authorized.
  Resume from
  [`STATUS-codex-jsonl-production-integration.md`](../plans/STATUS-codex-jsonl-production-integration.md).
- **Project baseline:** verify the current `origin/main` tip from Git before
  comparing branches or attributing work to the baseline. This pointer routes
  project and arc state; it is not a Git-ref authority. Read [`STATUS.md`](STATUS.md)
  for active versus closed arcs and the next authorized action.
- **R2b Capture Authorization:** v2 I1–I3 implementation and Corrective IX
  integration are on `main` (PR #264). Live capture, duration acceptance,
  packet/grant, and I4–I8 remain separately gated. Read
  [`STATUS-r2b-capture-auth.md`](../plans/STATUS-r2b-capture-auth.md).
- **Naturalistic product-value evaluation:** G1–G5 methodology, the accepted
  V2-01C bounded authority/compatibility package, and V2-02C source-backed
  capability derivation are on `main`. V2-02C landed through normal merge PR
  #284 at `4650c8d54aa13db361d91f73337fde4adba58fe6`, preserving reviewed tip
  `a64df8fc7fe98c66b2d44180846242429f502534`. Issue #277 remains deferred
  security-testing debt; V2-03C and G6 remain Ryan-locked. Read
  [`STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md).
- **Recovery Authority:** T1–T3 are on `main`; T4 is not authorized and V4k
  remains blocked on the separately governed CG-2 reference-v2 closure. Read
  [`STATUS-recovery-authority.md`](../plans/STATUS-recovery-authority.md).

## Resume order

1. Run `convmem doctor`, then `convmem brief --stdout-only` and
   `convmem unresolved`.
2. Read this pointer and [`STATUS.md`](STATUS.md).
3. If an arc applies, read its `docs/plans/STATUS-<slug>.md` brief.
4. Open only the dated handoff explicitly linked by that status or by the
   current task. Do not scan the inbox by mtime or resume from an old packet.

## Historical material

The previous long pointer is preserved as
[`LATEST-2026-08-30.md`](../archive/inter-model/LATEST-2026-08-30.md). Closed
debates, research packs, and handoff bundles remain in this tree for provenance;
they are not active work unless current routing links them. See
[`README.md`](README.md) for the active-inbox and archive rules.

## Handoff maintenance

When current routing changes, update this file with the new state and one link;
put full evidence in the dated handoff or arc brief. Keep superseded history in
its existing archive/reference location. Use
[`HANDOFF-TEMPLATE.md`](HANDOFF-TEMPLATE.md) for new cross-model handoffs.

## Jargon TL;DR

| Term | Meaning |
|---|---|
| `origin/main` | The pushed GitHub baseline used as the repository’s recovery reference. |
| R2b | The separately governed capture-authorization path for a continuously mutating source. |
| G6 | The Ryan-gated prospective naturalistic product-value study freeze. |
| T4 | The next Recovery Authority execution stage; it is not currently authorized. |
| V4k | A Recovery Authority verification item blocked on CG-2 reference-v2 closure. |
| Ryan-locked | A state that may be reviewed or prepared but cannot advance without Ryan’s explicit grant. |
