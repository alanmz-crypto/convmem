# Latest cross-model handoff (single pointer)

**Updated:** 2026-09-21

This file is intentionally short. It routes a new session to current state; it
is not a status log, decision ledger, or archive. For live corpus and service
state, run `convmem brief --stdout-only`. For project and arc state, use the
cross-arc snapshot and the linked arc brief below.

## Current routing

- **Arc Poison Pill / convmem indexer SIGSEGV (ACCEPTED 2026-09-21 — hardening-only):** the indexer, `refine` and the watcher parent were all dying
  with SIGSEGV/SIGABRT from 2026-09-18. All Chroma writers were stopped **and disabled** (they
  survive reboot) at 2026-09-20T09:57:02-05:00. Read-only forensics found **no structural
  corruption** in either quarantined index or in the live index as it stood two minutes before the
  07:20 crash. Ryan restored Intel defaults (PL2 was unenforced at 4095 W against a correct 253 W
  PL1; XMP off). An upsert matrix on isolated scratch copies then returned **15/15 CLEAN —
  300,000 update-in-place upserts** across default threads, `num_threads=1`, and nine concurrent
  readers, excluding the chroma #6895 thread-race hypothesis. Evidence now favours a **platform**
  cause: 78% of pre-fix faults on CPUs 4/8/10 (including both Turbo Boost Max favoured cores) and
  unrelated programs faulting (udevadm at boot, `git` SIGBUS, chrome, electron). **Ryan adopted the BIOS-misconfiguration
  assumption on 2026-09-20** and work resumes under it, staged and gated — see
  [`EXECUTION-poison-pill-resume.md`](../plans/EXECUTION-poison-pill-resume.md) for the pre-registered
  proof (≥6 loaded hours clean = credible, ≥24 h = accepted) and the tripwires that revoke it.
  **First reading in, 2026-09-21:** 14.97 clean loaded hours — 0 kernel faults, 0 core dumps, 0
  machine-check events — and the §4.2 structural validator returns PASS on both live segments. That
  clears §3's ≥6 h bar, so the fix is **credible** and stage 2 may be entered; it is **not** the
  ≥24 h that would make it accepted, so the watcher stays down. Today's rollback point is fresh
  (`8034fe4d…`, offsite `a344fdc3…`), retiring §2.2's eleven-hour gap.
  **Next:** **ACCEPTED 2026-09-21 (Ryan authority).** Ryan waived the literal ≥24 h bar and accepted
  the ~18 h 40 m writer-loaded clean window (0 crashes this boot, 0 since the 05:11 unfreeze, §4.2
  structural OVERALL PASS on both live segments under load; Q1–Q3 ruled by Kiro). Writers are all
  running normally. Arc **downgraded to hardening-only** — the §7 backlog (circuit breaker, crash
  accounting, enforceable writer-lease per Q3, validator → `scripts/`, on-demand snapshot, export
  drift) remains in **Cursor's lane** and does not block operation. Decision recorded in
  [`EXECUTION-poison-pill-resume.md`](../plans/EXECUTION-poison-pill-resume.md) §8. Resume from
  [`KIRO-2026-09-21-poison-pill-12h-gate-handoff.md`](KIRO-2026-09-21-poison-pill-12h-gate-handoff.md)
  (state `ACCEPTED — hardening backlog open`); prior phase C
  [`KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md`](KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md);
  arc brief [`STATUS-chroma-upsert-crash.md`](../plans/STATUS-chroma-upsert-crash.md).
  **CLOSE-OUT ANCHOR (resume here):**
  [`KIRO-2026-09-21-poison-pill-closeout-handoff.md`](KIRO-2026-09-21-poison-pill-closeout-handoff.md)
  — single durable list of all open future work (8-item hardening backlog, all Cursor lane,
  non-blocking) + what's resolved (do not re-investigate) + the parked GPU arc `obs_68435fbdab34`.
  The Kiro session that ran this arc is closed permanently.
  Arc: Poison Pill.
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
