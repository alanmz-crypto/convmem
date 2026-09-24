# Adversarial Review Response — ConvMem Switchboard Transition Readiness

**Arc:** ConvMem Switchboard
**Date:** 2026-09-23
**Author:** Claude (adversarial-review lane)
**Responding to:** `CODEX-2026-09-23-switchboard-claude-adversarial-review-handoff.md`
**Reviewed against:** `ARCHITECTURE-openclaw-convmem-integration.md`, `STATUS-openclaw-convmem-integration.md`,
`STATUS-openclaw-watch-coverage.md`, live `site_filter.py`/`read_scope.py`, and
`origin/main` @ `9193f5e` (`feat/2026-09-21-openclaw-convmem-t0-t5`, PR #327)

```text
ARC: ConvMem Switchboard
VERDICT: PREPARE_WITH_CONSTRAINTS

SAFE_NOW:
- Item 1 (choose/freeze OpenClaw version baseline) — AS A DOCUMENTED DECISION ONLY.
  Writing down "we pin 2026.3.2, rollback is X, dependency hashes are Y" touches no
  live file. Do not let "freeze" become "install" — no ~/.openclaw/openclaw.json write,
  no binary swap. That crosses into the explicit STATUS hard stop: "No OpenClaw
  upgrade without separate authorization."
- Item 2 (transition packet: versions/scope/credentials-format/network/filesystem/
  service-ownership/rollback/evidence) — as a draft doc with placeholder values, not
  real secrets, and explicitly labeled non-authoritative.
- Item 4 (define acceptance workload: scoped retrieval, denial behavior,
  prompt-injection-shaped memory, timeout/cancellation, child-agent behavior,
  restart/rollback) — pure test-case authorship, same shape as the fixture tests
  already merged in PR #327 (test_mcp_openclaw_strict.py,
  test_openclaw_strict_packet_contract.py, etc.). No execution required to define it.
- Item 5 (draft Gate D packet: auth/containment/packaging/distribution/permissions/
  provider-model behavior) — as a draft only. See REVIEW_REQUIRED below for the
  trap this item sets.
- Item 6 (design the child-agent inheritance *observation methodology*) — SAFE as
  long as the document defines how you'd prove inheritance from a real dispatched
  run (e.g., check tools/list reachable inside a child ACP session) and explicitly
  does NOT assert an answer. STATUS section 6 already marks this UNANSWERED —
  designing the test is fine; answering it is not, without a real run.
- Item 8 (operational ownership: upgrade/qualification/scope-change/shutdown/
  rollback/promotion RACI) — pure documentation.

REVIEW_REQUIRED:
- Item 3 (disposable staging profile/workspace, synthetic data only) — this is the
  single highest-risk item in the list. "Prepare a workspace" is an action, not a
  document, and the attack surface you named ("staging profile accidentally reads
  real HOME/XDG paths, credentials, workspaces, transcripts") is real: OpenClaw and
  ConvMem both default-resolve paths under the real $HOME
  (~/.openclaw/openclaw.json, ~/.local/share/convmem/read_scope.json — see
  read_scope.py's _SCOPE_FILE). A staging profile built without an explicit,
  reviewed isolation contract (separate synthetic HOME/XDG root, no env-var reuse,
  no symlinks into real data) can silently read or write real state even while
  "only using synthetic data." Owner: write and get sign-off on the isolation
  contract BEFORE creating anything — this can be a design doc, safely, today. The
  workspace itself waits for that sign-off (Kiro or Ryan).
- Item 5's packet, once drafted, must be re-flagged as REVIEW_REQUIRED before any
  value in it is treated as authoritative. A "draft Gate D packet" left unlabeled
  is exactly the failure mode you asked me to attack: "the transition packet
  becomes an unreviewed production configuration or silently chooses Gate D
  values." Mitigation: every value field starts as `TBD — Gate D` until Gate D is
  actually opened.
- Item 7 (repair/merge the bounded folder-watch work if its pytest baseline is
  resolved) — this lives on a different, adjacent arc
  (feat/2026-09-23-subproject-folder-watch, visible in the branch list but not
  read in this review). Merging it under the banner of "Switchboard prep" would
  couple two arcs' approval tracks. Keep it on its own review/merge decision;
  don't fold it into this handoff's authorization.

BLOCKERS:
- LIVE_DATA_OR_PROMOTION_BLOCKER — Gate D (real runtime), Gate W (governed writes),
  Gate D-V (value evaluation), Gate E (pilot), and promotion: none are authorized.
  Confirmed against STATUS §4 and §7 hard stops. Nothing in the 8 proposed items
  requires any of these to be opened, provided the REVIEW_REQUIRED items above are
  actually held to document-only status.
- LIVE_DATA_OR_PROMOTION_BLOCKER — poison-transcript/Chroma upsert crash loop
  (Arc Poison Pill). This session's own pending-reminder state is the freshest
  evidence available: the 12h gate PASSED (14.97 clean hours, 0 faults, HNSW
  validator PASS on both live segments) but stage 2 enable is still
  BLOCKED_ON_RYAN and has not been run; the watcher (stage 3) stays down until
  ≥24h clean. Architecture doc item 10 and STATUS §4/§6/§7 already correctly gate
  transcript capture behind this. Flagging because it means "transcript capture"
  is not just "later phase, not yet started" — it's actively mid-remediation on a
  separate branch (fix/2026-09-20-chroma-upsert-poison-pill) with its own unresolved
  ledger entries (obs_a09dbfa9e237, obs_c1499a660d4f, obs_e8db779df8c3). None of
  the 8 proposed items touch transcript capture, so this doesn't block them — but
  DO_NOT_DO below makes the boundary explicit since both arcs share "OpenClaw" and
  it would be easy to conflate them.

ADDITIONAL_PREPARATION:
- Write the staging-profile isolation contract first (before item 3's workspace).
  Concretely: a synthetic HOME/XDG root that is never a subdirectory of, or
  symlinked from, any real convmem or OpenClaw data path; an explicit denylist of
  env vars that must NOT be inherited (CONVMEM_READ_SCOPE_FILE,
  CONVMEM_DATA_DIR-equivalents, any credential var); and a pre-flight check the
  staging session can run against itself to prove it resolved to the synthetic
  root before doing anything else. This is the item most likely to leak real data
  if skipped, and it costs nothing to write today.
- A short "fail-open inventory" note: the existing site_filter.py fail-open
  default (empty site == match-all, confirmed by direct read of
  unit_matches_site()) is exactly the class of bug the architecture's
  scope-resolution contract exists to close. Worth one line in the transition
  packet's Gate D section noting which currently-fail-open behaviors the strict
  connector must override, so Gate D review has a named checklist instead of
  re-deriving it.

DO_NOT_DO:
- Do not install, upgrade, downgrade, or write config for the real OpenClaw
  binary as part of "freezing" a version baseline — document the choice, don't
  execute it.
- Do not create the staging workspace under real $HOME/XDG paths, or by copying
  real ~/.openclaw or ~/.local/share/convmem contents "for realism."
- Do not let the Gate D packet acquire real credentials, tokens, or get wired into
  any file ConvMem or OpenClaw actually reads at runtime.
- Do not touch convmem-watch, the poison-pill stage 2 timers, or
  fix/2026-09-20-chroma-upsert-poison-pill as part of this prep — that's a
  separate, currently BLOCKED_ON_RYAN decision with its own gate, not Switchboard
  scope.
- Do not merge the folder-watch corrective work under this handoff's authorization
  — it's a different arc's merge decision.
- Do not report M7/M8 fixture-test success (PR #327) as evidence toward Gate D,
  live runtime, or promotion. It qualifies the bounded/synthetic contract only.

NEXT_LANE: Ryan
REQUIRED_NEXT_ACTION: Ryan authorizes items 1/2/4/5/6/8 as document-only prep
(assign to Codex), and separately authorizes writing the staging-profile isolation
contract (item 3's prerequisite) before any workspace is created. Item 7 stays on
its own arc's track. Kiro's already-queued adversarial PASS/FAIL review of the
architecture document itself (STATUS §4/§5, still NOT STARTED) remains the
prerequisite for Phase 0 — this response does not substitute for it.
```

## Handoff boundary

This review recommends no runtime, configuration, credential, network, service,
or production change. Everything marked `SAFE_NOW` is document-authorship work.
The one action item (staging workspace, item 3) is deliberately held at
`REVIEW_REQUIRED` pending an isolation-contract document, which is itself safe to
write now.

I finished: [Arc ConvMem Switchboard] adversarial review of transition-prep readiness
Next step: Ryan authorizes the document-only prep items and the isolation-contract task; Kiro's architecture PASS/FAIL review is still the actual Phase 0 gate
Next lane: Ryan, then Kiro
See my work: this file (`docs/inter-model/CLAUDE-2026-09-23-switchboard-transition-readiness-review.md`)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
