# [Arc Claude Watch Parity] Implementation Handoff: close Gate 1 real-source smoke gap

**Date:** 2026-09-18
**Author:** Codex planning lane
**For:** Cursor implementation lane, then Ryan for two exact-source grants
**Authorization:** Ryan asked to implement the omitted check, then requested a
handoff to the correct lane. This authorizes bounded **hermetic preparation**;
it does not name a live transcript or authorize reading, indexing, paid calls,
production writes, or watcher action.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `READY_FOR_CURSOR_HERMETIC_PREP`; live preflight and real indexing are `BLOCKED_ON_RYAN` exact-source grants. |
| **Base** | `origin/main` at `aadf137899fc5f4db5062730f6849f4db2bf48b5` at handoff; recheck before work. |
| **Gate 1** | [PR #310](https://github.com/alanmz-crypto/convmem/pull/310) squash-merged on 2026-09-18; Kiro reviewed adapter tip `ab8a9e16ddd64aef55c301caf545f8e743fc33d8`. |
| **Branch** | Start `feat/2026-09-18-claude-gate1-real-smoke` from current `origin/main` in a separate worktree if tracked code is needed. Do not switch the contested shared checkout. |
| **Push status / PR** | This planning handoff is on pushed `plan/2026-09-18-claude-watch-parity`; no smoke implementation branch or PR exists yet. |
| **Ryan gates** | First: name one canonical Claude JSONL path and authorize read-only stat/hash preflight. Second: after a content-free source packet, authorize one exact isolated `index --file` run with output target, cost/time limits, and cleanup disposition. |
| **Track A ingest** | This handoff is not session-chat ingestion. Index the implementing session's own transcript at handoff; report actual success or failure. |

---

## What to build

Close the **unmet end-to-end acceptance item** in the original Gate 1 adapter
spec: one real Claude transcript through `convmem index --file` must report
`files_processed=1` and `units_indexed>0`. First prove that the existing CLI
can run with every mutable target under a fresh scratch root using a synthetic
Claude-shaped fixture and no live provider. If a safe isolated invocation can
be constructed without tracked code, document that exact command and evidence;
otherwise implement the smallest fail-closed launcher and hermetic tests on a
Cursor branch. Stop before any real-source access and return a one-shot grant
packet to Ryan.

**Why this exists:** PR #310 correctly disclosed that no real, paid transcript
was indexed. Its green parser tests and CI establish adapter behavior, not the
actual Track A `index --file` path on a real session. The acceptance gap was
deferred, not passed. Gate 2's isolated incremental route and production watch
promotion are separate work; this smoke must not silently enable either.

---

## Integration point

- `convmem.py:index` calls `_guard_write()` then `ingest.index(force_file=...)`
  and prints `files_processed`, `files_skipped`, `chunks_indexed`, and
  `units_indexed`. It has no `--config` or cost-limit flag.
- `config.py` reads `CONVMEM_CONFIG` at import time. A **new subprocess** must
  receive an explicit scratch config before importing ConvMem; no implicit
  production config/default may be accepted.
- `adapters/claude_session_jsonl.py:is_claude_session_jsonl` requires a
  `.jsonl` file under `Path.home()/.claude/projects`. A scratch copy therefore
  needs an isolated `HOME` and the same relative path shape; do not weaken
  detection to make the test pass.
- `config.example.toml` lists `chroma_dir`, `processed_log`, `units_export`,
  `sources.inventory`, incremental state, and optional shadow paths. The
  writer lock defaults under `HOME/.local/share/convmem/locks`; verify **all**
  actual writes, locks, caches, and output paths are scratch-confined before
  any real run.

---

## Specification

### Inputs and phases

1. **Hermetic feasibility now:** synthetic Claude JSONL fixture only; fresh
   scratch root, scratch `HOME`, absolute `CONVMEM_CONFIG`, disabled watch and
   incremental routing, no production credentials or network. Demonstrate the
   real CLI dispatch, not just `parse()`. Use deterministic local test doubles
   if needed; state clearly what provider behavior they do **not** prove.
2. **Read-only live preflight later:** only after Ryan names one exact canonical
   source path and authorizes stat/hash. Bind canonical path, alias, regular-file
   and no-symlink status, device/inode, size, mtime, and SHA-256. Do not emit
   transcript text or parsed messages. Recheck identity after hashing; abort on
   drift. Return the content-free packet without indexing.
3. **One-shot real smoke later:** only after Ryan approves that packet and
   specifies the scratch output target and numerical provider/time/size limits.
   Copy the granted bytes read-only into scratch `HOME/.claude/projects/...`,
   revalidate source identity/digest and copy digest, run exactly one
   `convmem index --file <scratch copy>` in the isolated subprocess, and capture
   only exit code, counts, source/copy digests, cost counters, and scratch-path
   assertions. If the CLI cannot enforce the approved bounds or prevent
   production writes, **stop**; do not fall back to the default config or a
   production corpus run.

### Behavior and output contract

- Before invoking the CLI, fail closed on inherited production config paths,
  network/provider credentials not authorized for the run, output/lock aliases,
  source symlink/nonregular file, digest/size/identity drift, or insufficient
  scratch space. Do not stop or modify the active watcher.
- Do not use `--force` or `--supersede`; use a fresh scratch processed log so a
  replay cannot be mistaken for the first-run acceptance result.
- A PASS requires `files_processed=1`, `files_skipped=0`, `units_indexed>0`,
  an exact-source/copy digest match, and proof that production Chroma,
  processed log, exports, config, locks, and watcher were unchanged. If a
  genuinely nonempty source yields zero units, report the failure; do not
  swap sources or loosen hygiene without Ryan's direction.
- Evidence is content-free. Never print transcript content, summaries, Chroma
  documents, embeddings, environment values, credentials, or full provider
  responses. Report actual provider use/cost separately from hermetic tests.
- Remove scratch copies only under the grant's explicit cleanup disposition;
  no broad deletion target or unapproved retention.

### Constants

No new production format or route constant is needed. Keep the default route
and `KIRO_ROUTE_FORMATS` unchanged.

---

## What NOT to build or run

- No live transcript listing, opening, parsing, stat/hash, or copy until Ryan
  names an exact file and grants the read-only preflight.
- No real `convmem index --file`, paid provider call, production Chroma/ledger
  write, or live-source canary until the **second** one-shot run grant.
- No `[sources].paths`, `[watch].extra_paths`, watcher/service, adapter,
  `incremental_jsonl.py`, `incremental_jsonl_formats.py`, or Arc Codex change.
  If the merged adapter needs correction, stop and return a separate finding.
- No Gate 2 prefix/spec implementation and no claim that this Gate 1 smoke
  proves incremental append safety or authorizes automatic capture.

---

## Test expectations

Cursor should verify hermetically, with `tmp_path` and subprocess isolation:

1. A valid Claude-shaped synthetic source reaches the merged adapter through
   the actual CLI and produces the expected nonzero count under controlled
   transforms; an unsupported neighbor fails rather than silently no-oping.
2. Missing/wrong `CONVMEM_CONFIG`, production-like target paths, symlink or
   nonregular source, source/copy drift, and provider/network leakage refuse
   **before** any mutable production path can be reached.
3. A zero-unit run is FAIL, not PASS; a reused processed entry cannot satisfy
   first-run acceptance. Evidence contains counts/digests only.
4. Existing Claude adapter tests still pass. `git diff --check` and repo Python
   quality gates pass for any new launcher/tests. No live file or provider is
   needed for this preparation phase.

---

## Acceptance criteria

- [ ] Cursor returns a reproducible, hermetic isolated CLI procedure or a
      minimal reviewed launcher with tests; no live source was touched.
- [ ] Static and runtime isolation checks show every mutable path under fresh
      scratch, with no production credentials/network during hermetic proof.
- [ ] Ryan receives a content-free exact-source preflight request and later a
      separate one-shot run packet; neither grant is inferred from this doc.
- [ ] Only after the real run: `files_processed=1`, `units_indexed>0`, and
      source/production invariants are evidenced; otherwise mark `NOT_RUN` or
      FAIL, never "Gate 1 fully verified."
- [ ] Gate 2 Execute and production watch promotion remain separate Ryan gates.

---

## Branch convention

If tracked code is needed: `convmem work start feat claude-gate1-real-smoke
--worktree` from current `origin/main`; push every commit with an explicit
`branch:refs/heads/branch` refspec. Do not open a PR until the hermetic packet
passes review and Ryan authorizes PR disposition. If no code is needed, return
the exact safe procedure and evidence without creating a branch.

---

## Related files

| What | Path |
|---|---|
| Original Gate 1 acceptance | `docs/inter-model/CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` on `origin/main` |
| Merged adapter | `adapters/claude_session_jsonl.py`; `adapters/detect.py` on `origin/main` |
| CLI/config seam | `convmem.py`; `ingest.py`; `config.py`; `config.example.toml`; `runtime_guard.py` |
| Arc current state | `docs/plans/STATUS-claude-watch-parity.md` on planning branch |
| Gate 2 plan, separate | `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md` |

---

## Leaving / picking up checklist

**Codex (leaving):** commit this handoff with current STATUS/LATEST; push the
planning branch; report the tip and Track A outcome.

**Cursor (picking up):** run session-start checks, read the arc brief, verify
merged Gate 1 and config seams, prepare only the hermetic path, then stop for
Ryan's named-source grant. Do not treat a source path in chat as the second
indexing grant.

**TL;DR [Arc Claude Watch Parity]:** Gate 1 code is merged; its original
real-transcript `index --file` acceptance remains untested. Cursor prepares a
safe isolated smoke path now. Ryan must separately name the file, authorize
read-only fingerprinting, and then grant one bounded real run.
