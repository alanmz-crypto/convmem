# Latest cross-model handoff (single pointer)

**Updated:** 2026-09-18

This file is intentionally short. It routes a new session to current state; it
is not a status log, decision ledger, or archive. For live corpus and service
state, run `convmem brief --stdout-only`. For project and arc state, use the
cross-arc snapshot and the linked arc brief below.

## Current routing

- **Trapdoor Hunt / issue #286 — shared seam MERGED:** Ryan squash-merged
  [PR #307](https://github.com/alanmz-crypto/convmem/pull/307) to `main` as
  `d657767d9351ce4c49e584ec14dfb0a7b8d9e77b` after Kiro and Copilot
  PASSed exact head `19d34a5e235bf436803ad8a2f15427fa9a84ef88` and all
  six CI checks passed. The merged registry/scanner and fresh isolated Codex
  routes are now the base for later work. This merge grants no S4/S5,
  production indexing, watcher/config, issue #268 closure, Arc Codex P2,
  bootstrap, or activation.
- **Arc Codex — append-cursor format extension planning:** Kiro PASSed the
  original conditional Copilot `events.jsonl` plan at `9e2d0ef`. The
  post-#286-merge revision on this branch now reuses the landed
  `incremental_jsonl_formats.py` registry and `adapters/jsonl_prefix.py`
  scanner; Kiro returned a written targeted PASS at exact plan tip `53e7b42`
  against merged code `d657767`.
  The [architecture](../plans/ARCHITECTURE-generalize-append-cursor.md),
  [bounded Execute proposal](../plans/EXECUTION-generalize-append-cursor.md),
  and [current-state brief](../plans/STATUS-generalize-append-cursor.md) are
  the reviewed basis for Ryan's preliminary local E0 trace grant.
  [Cursor's bounded trace handoff](CODEX-2026-09-18-copilot-e0-local-trace-handoff.md)
  gives the exact temporary resources, client actions, six-action/15-minute
  bound, zero external provider spend, observations, and stop conditions.
  [Codex-to-Codex ownership handoff](CODEX-2026-09-18-append-cursor-ownership-handoff.md)
  records Ryan's selection of the authoring Codex Sol-medium lane as
  coordination owner. The shared-code base is settled by the merge; Ryan must
  name a Copilot implementation writer in a later grant. Ryan granted only
  the preliminary offline local-provider trace. Installed Copilot CLI 1.0.86
  has a 30-credit minimum **soft** session limit; the local trace avoids
  external inference but cannot by itself prove hosted writer parity.
  Cursor returned the bounded local trace: prior bytes remained exact prefixes,
  but the inode changed on every action and the last action made an unexpected
  `read_agent` tool call. The merged coordinator treats an inode change as
  `source_replaced_or_rotated`, so this is **not an E0 PASS** for the proposed
  transform-reuse route. Kiro's targeted read-only recheck confirmed that
  decisive finding. Its additional claim that changing `workspace.yaml` digests
  independently block reuse needs correction: the merged sidecar digest check
  compares against the current run's snapshot, and no digest is stored in the
  checkpoint for cross-run comparison. Ryan now decides whether to stop under
  the current contract or authorize revised-E0 planning. No hosted trace or
  further Execute is authorized. Evidence:
  `/tmp/convmem-copilot-e0-local.farpf1dl/analysis.json` and five snapshots.
  Conditions: E3 must prove Copilot `session_id`/YAML precedence and the chosen
  sidecar invalidation rule. Copilot writer proof remains a hard E0 gate;
  no implementation, bootstrap, live canary, or activation is authorized.
  When merging with the 2026-09-17 R2b corrective's LATEST edit, keep both
  routing bullets.
- **Trapdoor Hunt / issue #268 — exposure-probe MERGED; NEXT GATE = §9.7
  post-merge measurement (BLOCKED_ON_RYAN):** PR **#305** squash-merged as
  `ef4a7dd…` on 2026-09-17 (Copilot audit + Kiro review + Claude advisory PASS on
  reviewed tip `ee97911`). The standing exposure-window probe now reads the
  projected ten-field metadata iterator on `main`. **Next action:** Cursor runs
  the plan §9.7 hermetic end-to-end `ingest.index(force_file=...)` memory-floor
  comparison of merged `main` vs baseline `5c103aa` — **requires a Ryan Execute
  grant to start.** Spec ready in
  [`CURSOR-2026-09-17-exposure-probe-postmerge-measurement-handoff.md`](CURSOR-2026-09-17-exposure-probe-postmerge-measurement-handoff.md);
  context in
  [`KIRO-2026-09-17-exposure-probe-postmerge-handoff.md`](KIRO-2026-09-17-exposure-probe-postmerge-handoff.md).
  **Live 12.5 GiB watcher OOM remains OPEN; do not declare #268 closed.** No
  watcher/config/exclusion change, production access, or Arc Codex P2
  progression without that evidence (§9.8, Ryan only).
- **Arc Codex — Kiro JSONL production integration:** the reviewed, hermetic
  coordinator and live-safe canary runtime are on `main` through squash-merged
  PR #301 (`8983a6fc…`) and remain disabled. Kiro's post-merge audit PASSed the
  final tree. A fresh 68-message source freeze at packet tip `27518aa…` also
  received Kiro PASS, but no executable grant or digest was issued. Grant-packet
  progression is paused while issue #268's shared watch-child OOM is narrowed
  and reviewed. PRs #302/#303/#305 removed three demonstrated allocators; the
  §9.7 post-merge end-to-end memory comparison remains pending. No Claude
  re-review, live source, Gate 0, P2 run,
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
