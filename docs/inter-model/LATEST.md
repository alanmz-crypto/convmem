# Latest cross-model handoff (single pointer)

**Updated:** 2026-09-18

This file is intentionally short. It routes a new session to current state; it
is not a status log, decision ledger, or archive. For live corpus and service
state, run `convmem brief --stdout-only`. For project and arc state, use the
cross-arc snapshot and the linked arc brief below.

## Current routing

- **Trapdoor Hunt / issue #286 — S0–S3 main integration (READY_FOR_RECHECK):** reviewed implementation `506afc1…` on `feat/2026-09-17-issue-286-incremental-index` remains unchanged. Integration onto `origin/main` (`18f63db…`) was performed and pushed on `feat/2026-09-17-issue-286-main-integration`; last code commit `5f142e2…` (not the review tip). Prior exact tip `e99856e…` received Kiro PASS (S0–S3 contract) and Copilot FAIL (documentation acceptance). **Next:** fresh Copilot and Kiro exact-tip reviews on `git rev-parse origin/feat/2026-09-17-issue-286-main-integration` after fetch; **no PR** until Ryan authorizes after those reviews. Resume from [`CURSOR-2026-09-17-issue-286-main-integration-handoff.md`](CURSOR-2026-09-17-issue-286-main-integration-handoff.md). No S4, S5, production indexing, watcher/config change, merge, or #268 OOM-closure claim is authorized.
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
- **Ingest cost + silent-failure correctives (2026-09-17, ad-hoc):** a Claude
  session traced the DeepSeek spend and found two defects and one gap.
  (1) `watch_skip_reason` short-circuited on a stale path hash and never reached
  the content-hash check `ingest.py` actually gates on, so nine
  `docs/inter-model/*.md` files whose content was already indexed under a
  Copilot audit copy re-spawned index subprocesses ~1,900x/day; fixed and
  verified live (49 spawns/hr to ~0). (2) `convmem index --file` reported
  `files_processed=0` with **exit 0** for any file no adapter recognizes, and a
  402/401 provider refusal ground through every remaining chunk with 15s of
  retry sleep each — the real cause of the 900s watch timeouts; both now fail
  loudly. Branch `fix/2026-09-17-watch-skip-hash-parity`, **`READY_FOR_PR`**,
  pushed, no PR opened (PR Steward's lane). (3) **There is no Claude Code
  adapter**, so the Track A step `CLAUDE.md` tells every Claude session to run
  has been ingesting nothing; resume from
  [`CURSOR-2026-09-17-claude-transcript-adapter-handoff.md`](CURSOR-2026-09-17-claude-transcript-adapter-handoff.md),
  state `NOT_STARTED`, **`BLOCKED_ON_RYAN`** on two gates.
  Live config changed under Ryan's direct instruction this session:
  `~/.codex/history.jsonl` soft-excluded (it was 56% of the serving corpus and
  94% of provider traffic) and its `[sources]` entry narrowed to
  `~/.codex/sessions`. **Open Ryan decisions:** whether to purge the 44,770
  units that file left behind, and whether `llm.py:45` should fall back locally
  on provider failure rather than only on a missing key.
- **Trapdoor Hunt / issue #268 — exposure-window probe plan:** PR #303
  squash-merged as `5c103aa…` after Copilot and Kiro PASS, replacing the main
  brief scans with one projected stream. A post-merge hermetic diagnostic
  confirmed an approximately 2x reduction at 58,825 units but isolated the
  remaining envelope-sized allocation in
  `doctor._exposure_window_probe()`'s full `ReadonlyUnitStore` read. Kiro
  returned unconditional PASS on the narrow projected-read plan at exact tip
  `5672ee9`. The Cursor handoff is prepared but remains `BLOCKED_ON_RYAN`;
  resume from
  [`CURSOR-2026-09-15-watch-oom-bound-exposure-probe-execute-handoff.md`](CURSOR-2026-09-15-watch-oom-bound-exposure-probe-execute-handoff.md)
  and the reviewed plan in
  [`EXECUTION-watch-oom-bound-exposure-probe.md`](../plans/EXECUTION-watch-oom-bound-exposure-probe.md).
  No implementation, production access, watcher/config/exclusion change,
  source re-inclusion, or Arc Codex P2 progression is authorized.
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
