# Latest cross-model handoff (single pointer)

**Updated:** 2026-09-24

This file is intentionally short. It routes a new session to current state; it
is not a status log, decision ledger, or archive. For live corpus and service
state, run `convmem brief --stdout-only`. For project and arc state, use the
cross-arc snapshot and the linked arc brief below.

## Current routing

- **Arc Poison Pill — Part B write guard MERGED ([#338](https://github.com/alanmz-crypto/convmem/pull/338), `d521281`), watcher deployed (Claude, 2026-09-24):**
  every production Chroma write now runs under a crash-containment guard. `.worktrees/runtime-main` was fast-forwarded,
  restore points were created (332 MB in `~/.local/share/convmem/chroma.write-guard/`), and `doctor` reports
  `chroma_write_guard` PASS. Part C says platform: a per-core probe at matched clocks produced 2 crashes and 1 silent
  miscalculation on CPU 8 in 12 minutes, and none on CPU 2. **Still open (Ryan):** refine, reconcile, monitor, the
  `convmem` CLI and the editors' MCP servers run `~/Projects/convmem`, so they get the guard only once that checkout runs
  merged code or is repointed. Also open: CPU mitigation (clock cap or offlining cores) and an Intel RMA. See
  [`CLAUDE-2026-09-24-chroma-upsert-containment-handoff.md`](CLAUDE-2026-09-24-chroma-upsert-containment-handoff.md).
- **Arc Poison Pill — recurrence 2026-09-23, containment fix MERGED ([#328](https://github.com/alanmz-crypto/convmem/pull/328), squash-merged as `81efa35` on `main`):**
  A native-fault crash (`convmem-watch` → `convmem index --file LATEST.md`, SIGSEGV/GP fault)
  recurred 2026-09-23 08:58 CDT, the same signature the arc's 2026-09-21 acceptance was meant to
  close. Hardware/BIOS telemetry for this recurrence is clean; root cause is **not** reopened by
  this work. At Ryan's direction, Claude built (rather than handed to Cursor) the two already-scoped,
  non-blocking hardening backlog items — per-file quarantine + global circuit breaker, and a
  `native_crash_gate` doctor check distinct from `ingest_degraded`. CI initially failed pylint's
  complexity gate and three content-identity pins (watch.py T0 canary hash; two R2b v2
  governed-route line/revision registries) that the line-shift and content change legitimately
  invalidated — all fixed as mechanical, verified refreshes (snippets checked before updating; R2b
  inventory regenerated via its own `write_v2_inventory_file()`, not hand-edited). All 6 CI checks
  passed before merge. No Switchboard file was touched (verified via `git diff --stat` before
  merge). **Root-cause reopening (this recurrence vs. the 2026-09-21 platform-only acceptance) has
  a bounded stop rule** (applied 2026-09-24 via
  [`DECISION-REVIEW-GUARDRAILS.md`](DECISION-REVIEW-GUARDRAILS.md), replacing an earlier open-ended
  "wait for Switchboard" framing): whichever comes first — 7 days of `doctor`'s `native_crash_gate`
  reporting 0 crashes, or a second native-fault recurrence within that window — triggers the
  investigation, independent of Switchboard's state. Background:
  [`CLAUDE-2026-09-23-poison-pill-circuit-breaker-handoff.md`](CLAUDE-2026-09-23-poison-pill-circuit-breaker-handoff.md)
  (see "root-cause reopening: bounded stop rule" section for the full Pattern/Evidence/Level/
  Decision-value writeup).
  **Next:** nothing pending on this specific fix; check `native_crash_gate` against the stop rule
  starting 2026-10-01 (7 days after merge) or immediately on any new native-fault crash.
- **ConvMem Switchboard — Claude adversarial review of transition-prep readiness delivered
  (2026-09-23):** Responding to Codex's handoff
  ([`CODEX-2026-09-23-switchboard-claude-adversarial-review-handoff.md`](CODEX-2026-09-23-switchboard-claude-adversarial-review-handoff.md)),
  Claude classified the eight proposed prep items — most SAFE_NOW as documents only; the
  disposable staging workspace held at REVIEW_REQUIRED pending an isolation-contract doc; the
  folder-watch merge kept on its own arc's track. No runtime/config/credential change made or
  recommended. Verdict and full findings:
  [`CLAUDE-2026-09-23-switchboard-transition-readiness-review.md`](CLAUDE-2026-09-23-switchboard-transition-readiness-review.md).
  Kept for provenance: at the time this review was written, Kiro's architecture PASS/FAIL was
  still pending; it has since **PASSED** at exact overlay tip `d1ca459` — see
  [`STATUS-openclaw-convmem-integration.md`](../plans/STATUS-openclaw-convmem-integration.md) for
  current state, which supersedes this bullet's framing.
- **Decision and Review Guardrails (opt-in doc) — MERGED (2026-09-24):**
  Kiro design review PASS, no blockers, two non-blocking amendments applied
  (charter link demoted to an "Optional lenses (not team policy)" sub-bullet;
  doc's Roles section defers to the charter role table). PR
  [**#329**](https://github.com/alanmz-crypto/convmem/pull/329) merged to
  `main` as `4418774`. No further action; nothing wired into any
  always-loaded surface — see
  [`DECISION-REVIEW-GUARDRAILS.md`](DECISION-REVIEW-GUARDRAILS.md) to invoke
  it going forward.
- **Arc OpenClaw Watch Coverage — W0–W6 MERGED / LIVE; full coverage still
  blocked:** implementation PR `#322` merged at `dc79eeb` and the separately
  authorized live activation passed retrieval, exclusion, governance, and
  service-health checks. The service remains pinned to the clean runtime
  worktree at that commit. OpenClaw planning PR `#327` later added five reviewed
  planning files; watch-closure PR `#331` merged as `2e50ec3`, classifying them,
  refreshing stale admitted-file hashes, and restoring a byte-exact manifest
  audit without advancing production. **Next:** any runtime-worktree promotion
  remains separately authorized. Full `WATCH_COVERAGE=PASS` still waits for accepted
  T0–T5 bytes, matching hashes, and a later controlled promotion. See
  [`STATUS-openclaw-watch-coverage.md`](../plans/STATUS-openclaw-watch-coverage.md)
  and [`VERIFY-openclaw-watch-coverage.md`](../plans/VERIFY-openclaw-watch-coverage.md).
- **Claude Gate 1 smoke retirement — MERGED / CLOSED:** issue [#317](https://github.com/alanmz-crypto/convmem/issues/317) found six blockers confined to the optional smoke harness. PR [#330](https://github.com/alanmz-crypto/convmem/pull/330) removed that harness and squash-merged as `e2148b2`; Kiro's post-update carry-forward review passed the updated branch tip and merged commit. The supported on-demand Claude adapter remains unchanged, and issue #317 is closed. Any future real-source containment smoke requires a new design and Ryan grant.
- **Claude Watch Parity — CLOSED (`NO_GATE2_ROUTE`):** Gate 1 on-demand Claude indexing remains supported. Ryan closed the automatic Gate 2 route after three Security Review FAIL tips (`10322a6`: six findings; `52bdc02`: ten; `95ef122`: three). Kiro is stood down. No live canary, production route, watcher/source/service change, or activation occurred. Experimental plans and tips are preserved under `milestone/claude-watch-parity-*` tags. Issue #317 retired the optional Gate 1 smoke harness after its own Security Review FAIL; any future real-source containment smoke requires a new design and Ryan grant. See [`STATUS-claude-watch-parity.md`](../plans/STATUS-claude-watch-parity.md); do not resume Gate 2 from its tagged branches.
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
  loudly. Branch `fix/2026-09-17-watch-skip-hash-parity`. **R2b blocker
  RESOLVED (2026-09-18); branch is GREEN at tip `f8dfbb1` and awaiting a
  Ryan force-push.** Not a logic regression — R2b binds an authority-content digest
  over governed modules. A clean-worktree investigation disproved the
  original "one coordinate" premise: the branch was 24-red on the nine R2b
  files at its pristine tip (main clean 110/110), from 8 governed
  coordinates that drifted (`convmem.py` +15 x5, `ingest.py` +25/+46/+46)
  when commit `38421fc` inserted lines without regenerating the two
  inventory artifacts. Under Ryan's option **R2**, the branch was rebased
  onto `origin/main` (`d657767`) and **both** inventories refreshed against
  the result (`incremental_jsonl.py` inventory coordinate already correct —
  runtime untouched, no Arc Codex change). New tip **`f8dfbb1`** received
  **Kiro exact-tip PASS** (nine focused R2b files 110/0 in a clean
  worktree; delta = 3 correctives + 2 inventory JSONs + the one-line
  `640`->`655`). **Next:** the rebase made the remote non-fast-forward;
  **Ryan publishes `f8dfbb1` with an exact-SHA `--force-with-lease`
  (force-push reserved to Ryan by protocol)**, then PR stewardship needs
  its own grant. Diagnosis + investigation in
  [`KIRO-2026-09-18-r2b-rebind-blocker-corrected-handoff.md`](KIRO-2026-09-18-r2b-rebind-blocker-corrected-handoff.md).
  (3) **The Claude Code
  adapter** (the Track A step `CLAUDE.md` tells every Claude session to run
  has been ingesting nothing): **Gate 1 APPROVED by Ryan 2026-09-18 —
  Option 2 (adapter only, on-demand `index --file`); Gate 2 auto-capture
  stays closed** (recorded to ledger, relates-to `dec_prop_20260623_161428_c311`).
  Decision brief:
  [`KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md`](KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md);
  implementation spec (Kiro-reviewed, Cursor lane) in
  [`CURSOR-2026-09-17-claude-transcript-adapter-handoff.md`](CURSOR-2026-09-17-claude-transcript-adapter-handoff.md).
  **Build stays behind the green base** — proceeds once `f8dfbb1` is pushed.
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
