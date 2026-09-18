# [Arc Claude Watch Parity] Implementation Handoff: Gate 2 isolated Claude JSONL route

**Date:** 2026-09-18

**Author:** Codex planning lane

**For:** Kiro design review, then Cursor implementation after authorization

**Authorization:** Ryan confirmed new arc Claude Watch Parity on 2026-09-18;
this authorizes planning, not Execute, live-source access, or watch activation.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `READY_FOR_KIRO_REVIEW` (plan only) |
| **Branch** | `plan/2026-09-18-claude-watch-parity` |
| **Tip SHA** | Resolve `origin/plan/2026-09-18-claude-watch-parity` after fetch; review the exact pushed tip, not a moving local checkout. |
| **Push status** | Pushed planning branch; confirm with `git status --short --branch`. |
| **PR** | Not opened; plan review precedes implementation and PR disposition. |
| **Ryan GATE** | Bounded Execute grant after Kiro plan PASS; separate exact-source canary grant; later production-route and watch/source promotion. |
| **Track A ingest** | Codex full session rollout to be indexed at handoff; no `logs/*.md` artifact created. |

---

## What to build

After the Gate 1 on-demand Claude adapter lands, extend it with a complete-prefix
view and register `jsonl_claude_session` in the existing incremental format
registry. Add `ISOLATED_CLAUDE_FORMATS` to the isolated route and prove the route
with focused tests and one separately authorized, read-only live-source canary.
Stop at content-free evidence for Kiro review. Claude remains outside production
routing and watch/source configuration throughout this Execute slice.

**Why this exists:** Claude transcripts are append-heavy. The Gate 1 adapter
revives manual Track A indexing, but watching the directory before incremental
reuse is proved would repeatedly transform old content. One previously watched
prompts-only source accounted for about 56% of serving units. The isolated
route tests Claude's byte and content contract without exposing production
state to that cost.

The Gate 1 adapter and the landed incremental substrate are prerequisites, not
implementation tasks in this plan. At this plan's `origin/main` base
(`d657767`, PR #307), the substrate is landed and the Claude adapter is absent.
Recheck both immediately before Cursor starts; do not implement against an
unreviewed Gate 1 adapter or revive the earlier in-flight #286 state.

---

## Integration point

- `adapters/claude_session_jsonl.py`: add
  `parse_complete_prefix(filepath, *, raw: bytes | None = None)` using the
  Gate 1 adapter's **same** record-to-message mapper and
  `adapters/jsonl_prefix.py`'s `complete_prefix_view`. A small mapper extraction
  inside the Claude adapter is allowed if Gate 1 did not already expose one.
- `incremental_jsonl_formats.py`: import the Claude adapter and register one
  `IncrementalFormatSpec` with `format_id="jsonl_claude_session"`,
  `adapter_module="adapters.claude_session_jsonl"`,
  `adapter_contract_version="claude-complete-prefix-v1"`, `tool="claude"`,
  `parse_complete_prefix=claude_session_jsonl.parse_complete_prefix`, and
  `snapshot_basename="session.jsonl"`. There is no sibling metadata file.
- In that registry only, add
  `ISOLATED_CLAUDE_FORMATS = frozenset({_CLAUDE.format_id})` and union it into
  `ALL_ISOLATED_FORMATS`. Keep `KIRO_ROUTE_FORMATS` exactly
  `frozenset({"jsonl_kiro_session"})`. The existing `isolated_codex=True`
  selector is a historical name for the isolation-root route; preserve its
  call sites in `incremental_jsonl.py` for this slice. Default
  `routed_formats()` must still return the Kiro-only set.
- `claude_incremental_canary.py` and
  `tests/test_claude_incremental_canary.py` may reuse the safety sequence in
  `CODEX-2026-09-09-jsonl-incremental-live-source-canary-execute.md`.
  Use the existing production `IncrementalJsonlCoordinator` **inside** a fresh
  `IsolationBoundary`; the older scratch engine and its hard-coded Kiro source,
  `messages.jsonl`, and `session.json` are not Claude execution surfaces.

No change to `incremental_jsonl.py` or Arc Codex's canary/STATUS/plan files is
part of this plan. If implementation discovers a necessary core change, stop
and return the concrete conflict to Codex/Kiro/Ryan for a revised grant.

---

## Specification

### Inputs and prerequisites

1. Gate 1 `adapters/claude_session_jsonl.py` and `detect.py` registration are
   merged and Kiro-reviewed. `detect_format()` identifies a Claude session as
   `jsonl_claude_session`; `get_parser()` points to that module's `parse`.
2. A Claude source has the shape
   `~/.claude/projects/<project-slug>/<session-uuid>.jsonl`; no sibling metadata
   is needed. For tests and canary copies, use an isolated `HOME` beneath the
   scratch root and reproduce that relative `.claude/projects/...` shape so
   normal format detection runs on the copy.
3. The isolated route uses a fresh root, scratch-only Chroma/state/config/locks,
   deterministic local transforms, and no production credentials or network.
   No actual Claude source is selected by this plan. A later Ryan one-shot
   grant must name one canonical file, alias, expected size, SHA-256, and source
   identity before any live-source read.

### Prefix and content contract

1. Select only the largest newline-terminated byte prefix. Return
   `CompletePrefixView` with canonical messages, one byte range per emitted
   message, a `RawLineOutcome` for **every** complete line, the boundary and
   prefix digest, and source device/inode. Leave a trailing partial line for a
   later append.
2. Use exactly the same Claude mapping for `parse()` and
   `parse_complete_prefix()`. Emit only user and assistant speech. Exclude
   `isSidechain: True`, non-message records, assistant `thinking`, `tool_use`,
   and `tool_result` blocks. For block lists, join `text` blocks only.
3. Remove `<system-reminder>...</system-reminder>` including injected
   `CLAUDE.md`, git, and memory context; remove
   `<local-command-caveat>`, `<command-name>`, `<command-message>`,
   `<command-args>`, and `<local-command-stdout>` wrappers **with their
   contents**. Drop an otherwise empty message. Keep ordinary text outside
   those wrappers, timestamps, session id, and workspace as Gate 1 defines.
4. Blank, malformed JSON, non-object, sidechain, non-message, and hygiene-only
   complete lines receive skipped outcomes, never emitted ranges. Preserve the
   coordinator's fail-closed invalid-UTF-8 behavior for a complete line; do
   not hide it as a successful parse.
5. Treat content-hygiene behavior as part of
   `claude-complete-prefix-v1`'s transform fingerprint. If that mapper changes
   after evidence, revise the contract version and rebuild/review accordingly.

### Isolated route and replay

1. Assert `get_format_spec("jsonl_claude_session")` selects the Claude mapper
   and that the default routed set excludes Claude and both Codex formats.
   Under the existing explicit isolation root, the isolated union includes
   Kiro, Codex, and Claude.
2. Exercise `IncrementalJsonlCoordinator.from_isolated_boundary` with the
   normally detected scratch Claude file. A first run builds authority; an
   unchanged replay makes zero transform calls; an append transforms only the
   overlap frontier and new accepted messages; clean rebuild authority matches
   the incremental result exactly.
3. A partial record cannot advance the complete boundary. Interior rewrite,
   truncation, source replacement/rotation, and transform-fingerprint change
   take declared fallback or rebuild-required paths without silently reusing
   stale prepared outputs. A pre-existing processed entry takes the existing
   bootstrap-required path unless separately authorized.
4. Repair missing summary and unit projections through the existing replay
   rules. A second-source sentinel survives every source-scoped prune. Reuse
   the current coordinator's checkpoint, journal, lock, and writer contracts;
   no Claude-specific state machine is added.

### Live-source canary pattern (separate Ryan grant)

Build the harness and hermetic tests in Cursor's isolated Execute slice; run
against one real Claude transcript only after Ryan grants the exact resource.
The canary follows the Kiro live-source precedent with Claude-specific source
shape and **no** `session.json` requirement:

The watch service was active at planning time (`convmem doctor`, 2026-09-18).
A live canary cannot pass Gate 0 in that state. Ryan must arrange an inactive
watcher window or another suitable host separately; Cursor must not stop the
service under this plan.

1. **Gate 0 before imports/writes:** from a stdlib-first launcher, confirm the
   watcher is inactive or abort if indeterminate; reject symlinked/nonregular
   sources, path/size/digest drift, production path aliases, inherited
   credentials or config defaults, network access, and any mutable path or
   lock outside the fresh scratch root. Do not start or stop services.
2. **Read-only capture:** open the granted file with no-follow/close-on-exec
   semantics where available; bind canonical path, device/inode, exact size,
   full digest, and complete-prefix digest. Copy the complete prefix atomically
   and fsync under the scratch `HOME`; revalidate the live descriptor/path and
   prefix before constructing Chroma. An append or identity change outside
   the exact grant aborts. Never mutate the live file.
3. **Scratch matrix:** full-source baseline, unchanged replay, staged append,
   partial line, mutation/truncation/rotation/fingerprint fallbacks, repair,
   unrelated-source sentinel, and exact clean-rebuild equality across both
   Chroma collections, active projection, and checkpoint authority. Use
   deterministic fake transforms and record transform/reuse counters and
   `max_units_in_flight`; do not claim constant memory or watcher RSS.
4. **Crash/replay:** subprocess exit at every declared durable coordinator,
   capture, and real-Chroma authority transition. A transition inventory must
   fail if any declared point lacks a case. Every replay converges to clean
   authority. Note that Chroma has no atomic cross-collection commit;
   checkpoint-governed replay is the tested recovery mechanism.
5. **Evidence:** record only source alias/path/identity/size/times/digests,
   selected boundaries and counts, scratch and isolation checks, modes,
   counters, transition names, exit codes, authority digests, and equality
   booleans. Do not print or commit transcript text, parsed messages, Chroma
   documents, embeddings, environment values, or credentials. Remove scratch
   copies after evidence extraction.

The canary PASS is evidence for a Ryan promotion decision, not a grant to add
Claude to the production route, sources, or watcher.

### Output / contract

- Claude's prefix parser returns `CompletePrefixView`; for a complete valid
  fixture, `parse(path) == parse_complete_prefix(path).messages` exactly.
- `FORMAT_SPECS` contains Claude, and `ISOLATED_CLAUDE_FORMATS` contains only
  `jsonl_claude_session`; default `routed_formats()` remains Kiro-only.
- Cursor produces
  `docs/inter-model/VERIFY-claude-watch-parity-gate2.md` with commands, exact implementation
  revision, focused test results, content-free canary evidence or a clearly
  marked `NOT_RUN` live-source gate, and known limits. Kiro reviews its exact
  pushed revision before Ryan considers promotion.

---

## What NOT to build or run

- No edits to `[sources].paths`, `[watch].extra_paths`, service/timer config,
  `KIRO_ROUTE_FORMATS`, or production activation flags.
- No `incremental_jsonl.py` core change, new watcher path, chunking/retrieval
  change, historical backfill, `--supersede` policy change, or Arc Codex file
  edit. Only the Claude adapter and `incremental_jsonl_formats.py` may change
  the production code surface in this slice.
- No sidechain/subagent capture or `thinking`/`tool_use`/`tool_result` content.
- No live-source read, production Chroma/ledger/index mutation, provider call,
  network call, or actual `convmem index --file` canary before a named Ryan
  grant. Hermetic fixture tests are allowed after Execute authorization.
- No PR, merge, or claim of watch readiness from plan approval alone. Stop at
  isolated evidence and Kiro review; Ryan owns the later promotion plan.

---

## Test expectations

Focused fixtures, not live transcripts, should cover:

1. `tests/test_claude_session_jsonl.py` (Gate 1 regression) and a new Claude
   prefix test: detection, canonical output, wrapper removal including repeated
   multiline `CLAUDE.md` injection, text-only assistant blocks, sidechain and
   non-message exclusion, empty-message drop, malformed/blank outcomes, full
   byte-range coverage, prefix digest, and partial-line completion.
2. A new Claude route test modeled on
   `tests/test_codex_incremental_jsonl_route.py`: production exclusion with
   the isolation root absent; isolated eligibility; first/unchanged/append
   counters; exact clean-rebuild equality; bootstrap-required, mutation,
   truncation, replacement, fingerprint, repair, and second-source cases.
   Assert Kiro and Codex routing behavior is unchanged.
3. `tests/test_claude_incremental_canary.py`, modeled on
   `tests/test_scratch_jsonl_live_source_canary.py`: exact-source and path
   checks fail before Chroma construction; source is opened read-only;
   network/credentials/production locks are denied; source-derived scratch
   matrix and subprocess fault coverage are complete; evidence is content-free.

Run those focused files plus the existing Kiro/Codex prefix and route tests,
then `python -m compileall -q` and `python -m pylint` on touched Python files,
and `git diff --check`. Record exact commands/results in `VERIFY`. A separate
static diff check must show `KIRO_ROUTE_FORMATS`, production config, watcher,
and `incremental_jsonl.py` unchanged. A live canary run is separately recorded
and never counted as a substitute for hermetic tests.

---

## Acceptance criteria

- [ ] Gate 1 adapter is merged and reviewed before Claude prefix work starts.
- [ ] Legacy and complete-prefix Claude parsers share one mapper and agree on
      complete valid fixtures; every complete line has a covering outcome and
      emitted messages have matching byte ranges.
- [ ] Injected `CLAUDE.md`/local-command boilerplate, sidechains, thinking,
      tool use/results, and empty messages never enter output or canary evidence.
- [ ] Claude has one `IncrementalFormatSpec` and its own isolated set; default
      production eligibility remains Kiro-only, including with no isolation
      root in the coordinator and ingest dispatch.
- [ ] Isolated append/replay work is frontier-bounded and agrees exactly with
      clean rebuild authority; partial, fallback, repair, crash, and
      second-source cases pass.
- [ ] Canary Gate 0 and exact-source capture fail closed; all mutable paths and
      locks stay under a fresh scratch root; no network/provider/credential or
      production collection is used.
- [ ] A granted live canary, if Ryan authorizes one, emits only content-free
      evidence and passes the matrix and transition-coverage assertion. If not
      authorized, mark it `NOT_RUN`; do not claim promotion readiness.
- [ ] Focused tests, compileall, pylint, and diff check pass; `VERIFY` records
      exact results and limitations. No `incremental_jsonl.py`, Arc Codex,
      production-route, config, or watcher change appears in the diff.
- [ ] Cursor branch is committed and pushed after each commit, then stops for
      exact-tip Kiro review. Ryan alone decides later promotion.

---

## Branch convention

Plan: `plan/2026-09-18-claude-watch-parity` (this pushed document). After Gate
1, Kiro plan PASS, and Ryan Execute authorization, Cursor starts from the then
current green `origin/main` with `convmem work start feat claude-watch-parity
--worktree` (or a resume branch named in the grant). Push every commit using an
explicit `"$branch:refs/heads/$branch"` refspec. Do not switch the shared
checkout. No PR is authorized by this planning handoff; Ryan squash-merges by
default if a later PR is requested.

---

## Related files

| What | Path |
|---|---|
| New arc brief | `docs/plans/STATUS-claude-watch-parity.md` |
| Gate 1 adapter spec | `docs/inter-model/CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` (shared checkout; not on this branch at plan time) |
| Gate 1 decision brief | `docs/inter-model/KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md` (shared checkout; not on this branch at plan time) |
| Sequencing handoff | `docs/inter-model/KIRO-2026-09-18-claude-watch-parity-next-steps-handoff.md` (untracked in shared checkout at plan time) |
| Kiro live-source canary pattern | `docs/inter-model/CODEX-2026-09-09-jsonl-incremental-live-source-canary-execute.md` |
| Prefix and route registry | `adapters/jsonl_prefix.py`; `incremental_jsonl_formats.py` |
| Current isolated-route tests | `tests/test_codex_jsonl_prefix_adapters.py`; `tests/test_codex_incremental_jsonl_route.py` |
| Arc Codex boundary | `docs/plans/STATUS-codex-jsonl-production-integration.md` (read-only) |

---

## Leaving / picking up checklist

**Codex planning lane (leaving):**

- [x] Arc brief and both Active STATUS lists updated on a dedicated plan branch.
- [x] This plan and `LATEST.md` top routing pointer prepared for Kiro review.
- [ ] Commit and push this exact plan revision; index the full Codex chat.

**Kiro review lane (picking up):**

- [ ] Fetch the plan branch and review its exact tip, this plan, and the arc
      brief; return PASS or specific conditions in writing.
- [ ] Keep implementation, live-source access, and promotion gates distinct.

**Cursor implementation lane (after Kiro PASS and Ryan Execute grant):**

- [ ] Read this plan and the reviewed Gate 1 adapter before the first edit.
- [ ] Build only isolated Claude prefix/route/canary surfaces and focused tests.
- [ ] Push evidence and stop for Kiro exact-tip review.

**TL;DR [Arc Claude Watch Parity]:** Gate 2 planning defines an isolated Claude
prefix/spec and a separately granted live-source canary. Production routing and
watch paths remain unchanged until Ryan reviews evidence and promotes them.
