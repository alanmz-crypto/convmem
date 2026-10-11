# Issue #286 — Codex rollout admission design

**Arc: Codex (#286), second live slice after the guarded Kiro route.**
**State:** Kiro design PASS at `9e91973` with six binding conditions (§13). Author:
Claude (Opus 5.5), 2026-10-10.
**Base:** `origin/main` `348ec0b`. No implementation, grant, config change, or
watcher action is authorized by this document.

## 1. Consequence for Ryan

Codex rollouts are the main source of repeated paid re-indexing and of the
largest watcher index children. The guarded live route on `main` (PR #365)
admits only exact-path Kiro sources. This design lets **new** Codex rollouts
use the incremental route from their first index, without listing each new
filename, without bulk-bootstrapping the existing rollouts, and without
weakening the reviewed fail-closed behavior. Pre-activation rollouts stay on
the legacy route exactly as today.

## 2. Evidence (read-only, 2026-10-10)

| Fact | Value | Source |
|---|---|---|
| Watcher spawns by class, Sep 26–Oct 5 | 133 Codex rollout, 35 Kiro, 29 Cursor JSONL (plus 3,315 inter-model docs, #308) | user journal, `convmem-watch` |
| Repeated full re-index | one rollout (`01a0e0cc…`) indexed 44 times; each child 4–5 CPU-min, 9–12 GiB peak | journal scope `memory peak` lines |
| Children at the 12 GiB cap | 3, all Codex rollouts (Sep 27 11:35, 11:41, 16:12) | same |
| Summarizer | `deepseek-v4-flash` (paid) for summarize and distill | live config `[models]` |
| Rollout files | 654; 3.3 GiB total; median 0.9 MiB, p90 8.1 MiB, max 586.8 MiB | file metadata |
| Long-lived rollouts | 64 written more than 24 h after start; 3 more than 7 days; the 586.8 MiB file grew for about 470 h | filename time vs mtime |
| Session identity | 651/654 filename times match the UUIDv7 time of the filename id (local time, <2 min) | filename parse |
| Same-session copies | 3 files (122–160 MiB) carry the 586.8 MiB session's id and `session_meta`, with later filename times; each is an exact byte prefix of the original | prefix hash comparison |
| Indexed state | 646 rollout entries in `processed.json` | `processed.json` |

Interpretation: rollouts are append-only per file, but sessions can live for
days and the same session can appear under a second filename. Neither mtime,
filename time, nor session id alone is a safe admission key.

## 3. Inherited constraints (do not regress)

From `DESIGN-issue-286-live-activation.md` (Kiro PASS `e4fa954`, RC-1–RC-3):

- **RC-1:** unselected sources route legacy; a selected source either
  succeeds or fails visibly (`live_route_refused`, `incremental_jsonl.py:2276`).
  A selected source's refusal must never become a silent legacy rebuild.
- **RC-2:** `CONVMEM_INCREMENTAL_ROOT` and the other isolation variables are
  never live authority.
- **RC-3:** no generic watcher or ingest event can invoke bootstrap.
- Selected live sources need an explicit `embed_dimension` (768 live).
- `force_reindex` and `supersede_on_reindex` are unsupported on the live route.
- Production boundary per source: canonical paths, no symlink components,
  regular owned file opened `O_NOFOLLOW`, role non-overlap.

This design **deliberately relaxes one rule**: "no wildcard or directory-only
grant for the first live slice." The Kiro slice remains exact-path. Codex
rollouts get a bounded *admission rule* in its place, because new
filenames cannot be granted in advance (`config.py:413–425` rejects globs)
and a race-free exact list is impossible (see §6, alternative A).

## 4. Design

### D1. Admission predicate (pure, evaluated at route time)

A path is **admitted** only if all of the following hold. Each check is cheap
and deterministic; any failure means **not admitted**, which routes legacy
exactly as today (RC-1).

1. `detect_format(path) == "jsonl_codex_rollout"`.
2. The canonical path is strictly under the configured canonical `root`, which
   must resolve to `~/.codex/sessions`, with no symlink component (reuse the
   production-boundary path validation).
3. The basename matches
   `^rollout-\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d-<uuid>\.jsonl$`, the uuid is
   version 7, and its embedded time is within 120 s of the filename time read
   as local time. A host timezone change makes new sessions fail this check
   and route legacy, which is the safe direction.
4. The uuid's embedded time is **at or after** `admitted_after`, an explicit
   UTC timestamp in the grant.
5. The first complete line is `session_meta` whose `payload.id` equals the
   filename uuid and whose `payload.timestamp` is within 120 s of the uuid
   time. This check runs on the coordinator's parsed prefix, before any
   provider call; if it fails, the result is a visible refusal (the path
   already passed 1–4), not legacy.

Effects on the observed population:

- Rollouts created before `admitted_after` are never admitted. They stay on
  legacy, so there is no bootstrap and no behavior change.
- Same-session prefix copies fail check 3 (their filename time is later than
  their uuid time) and stay legacy, as today.
- A new session created after `admitted_after` is admitted from its first
  index, and a never-indexed path is `eligible_new_source`
  (`incremental_jsonl.py:411–415`). Its first run is the normal initial
  transform; later appends reuse prior chunks.

### D2. Selection semantics and race closure

`maybe_route_incremental` (`incremental_jsonl.py:2215`) treats
`path_key in live_sources or codex_admission.admits(path_key)` as selected
(`:2247`). Both format gates must accept `jsonl_codex_rollout` for admitted
paths only: the route check (`:2249`) and the coordinator's
`routed_formats` (`:535–537`, used by `decide_eligibility` at `:404`). Kiro
exact-path selection is unchanged.

Race: a rollout created after `admitted_after` must never be legacy-indexed
first, or it becomes `bootstrap_required`. The activation procedure closes
this race:

- Install the config with the watcher stopped.
- Set `admitted_after` to the install time plus a margin (for example 10 min).
- Any index after install uses the same config, so no path that can be
  admitted can have a legacy entry.

If the config is later removed and re-added (rollback, §D8), affected paths
refuse visibly rather than silently.

### D3. Refusal containment in the watcher (required)

Today a selected-source refusal raises in the index child. The watcher's
breaker quarantines only native faults and timeouts
(`watch.py:388`, `:575`), so each later append to the same path respawns a
child that refuses again. This is the #308 pattern, and it hides a coverage
gap.

Required behavior:

- The index child reports a refusal with a distinct, parseable marker
  (`live_route_refused:<outcome>`) or a dedicated exit code.
- The watcher records it as a third failure class with threshold 1:
  - it quarantines the path immediately;
  - it persists the outcome and the refused prefix digest;
  - it never retries on later events.
- `convmem doctor` gains an `incremental_refusals` check listing quarantined
  admitted paths with their outcomes. Any entry makes the check WARN.
- Clearing a quarantine is explicit: an operator action after an exact-path
  bootstrap or a state repair. It is never automatic.

If the #308 terminal-failure fix lands first and covers this class, D3 reuses
it rather than adding a parallel mechanism.

### D4. Paid-call guard for admitted sources

- **Invariant:** transformed chunks are a subset of the frontier computed from
  the checkpoint (the chunks overlapping new messages, plus the final overlap
  chunk). A violation refuses before any provider call.
- **Backstop:** `max_transform_chunks_per_run` (default 20, about 1,000
  messages at size 60 / overlap 10). Exceeding it refuses visibly (D3). This
  bounds paid spend if a first index happens late, for example after watcher
  downtime.

### D5. Source-size ceiling

`complete_prefix_view` reads the whole file into memory, splits it into a
second copy, and retains the prefix (`adapters/jsonl_prefix.py:56`, `:123`,
`:142`). The incremental route reduces model calls, not source I/O or parse
memory. Admitted sources need `max_source_bytes` (default 256 MiB; one of
654 rollouts exceeds it today). Above the ceiling an admitted source refuses
visibly. It does not fall back to legacy, which would be worse. Streaming
parse is out of scope.

### D6. Observability

Every admitted-source run logs one structured line:

- format;
- outcome;
- chunks reused, transformed and pruned;
- provider requests and tokens by provider;
- source bytes;
- elapsed time.

These are already counted by the coordinator; this design adds emission.
Doctor summarizes the last 24 h by format. This is the evidence Ryan needs
to claim paid-call reduction (live-activation design, "Coverage decision").

### D7. Pre-activation sessions

They stay on legacy. Operational guidance at activation: start fresh Codex
sessions rather than resuming pre-activation ones, because a resumed
long-lived session keeps appending to its old, non-admitted file.

An optional follow-up slice (v1.1, not in this design) could generalize
`scripts/bootstrap-incremental-jsonl.py` beyond Kiro (`:31` imports the Kiro
parser; `:433` rejects other formats). It would serve an explicit exact-path
list of long-lived sessions still growing at activation, each under its own
Ryan budget grant. Bulk bootstrap of closed rollouts is rejected (§6 B).

### D8. Rollback

Rollback is: stop the watcher, then remove the admission table. Admitted
sources then fall back to legacy on their next change, which re-indexes the
whole file and makes their checkpoints stale.

Re-enabling later makes those paths refuse visibly (D3), because their
projections no longer match their checkpoints. Recovery is per-path: an
exact-path bootstrap, or a checkpoint retirement procedure. Rollback is
therefore one-way per source, and the activation note must say so.

## 5. Configuration shape (proposal)

```toml
[index.incremental_jsonl]
enabled = true
embed_dimension = 768
live_sources = []                      # Kiro exact paths, unchanged semantics

[index.incremental_jsonl.codex_rollout_admission]
root = "/home/lauer/.codex/sessions"   # canonical; must equal the Codex sessions dir
admitted_after = "2026-10-15T15:00:00Z" # explicit UTC; set at install time plus margin
max_transform_chunks_per_run = 20
max_source_bytes = 268435456
```

Validation fails closed:

- the table present while `enabled` is false;
- a non-canonical or symlinked `root`;
- a naive or unparsable `admitted_after`;
- non-positive limits;
- a missing `embed_dimension`.

## 6. Alternatives considered

- **A. Automatic exact-list writer** (append each new rollout to
  `live_sources`). Rejected: automatic config mutation, a race between
  creation and the first legacy index, and an unbounded list.
- **B. Bulk bootstrap of existing rollouts.** Rejected: roughly a full paid
  re-summarization of 646 indexed rollouts (654 files, 3.3 GiB) for files that mostly
  never change again.
- **C. mtime- or birth-time-based admission.** Rejected: mtime is mutable,
  and birth time is not reliably exposed.
- **D. Filename time only.** Rejected: same-session copies have later
  filename times and would be admitted as new sources.
- **E. Auto-bootstrap on `bootstrap_required`.** Rejected: it violates RC-3
  and makes paid spend event-driven.

## 7. Implementation integration points

| Change | Location |
|---|---|
| Admission settings parse/validate | `config.py:377` (`incremental_jsonl_settings`), next to `live_sources` `:413–428` |
| Admission predicate (pure function + `session_meta` check) | new `incremental_jsonl_codex_admission.py`; called from `incremental_jsonl.py:2247` |
| Format gates for admitted paths only | `incremental_jsonl.py:2249`, `:535–537`; `incremental_jsonl_formats.py:59–80` |
| Transform-subset invariant, chunk backstop, size ceiling | coordinator, before the provider phase |
| Refusal marker in the child; refusal class in the breaker | `incremental_jsonl.py:2276`; `watch.py:274–292`, `:388`, `:575` |
| Doctor `incremental_refusals` and per-format 24 h summary | doctor checks module |
| Per-run structured log | coordinator result emission |

## 8. Test expectations (hermetic: fake providers, temp real Chroma, network denied)

1. Predicate matrix:
   - format, root, symlink component, filename regex;
   - uuid version, uuid-vs-filename skew, `admitted_after` boundary (equal,
     one ms before);
   - `session_meta` id and timestamp mismatch;
   - same-session prefix copy.
2. RC-1 parity: non-admitted rollouts route legacy byte-for-byte; Kiro
   exact-path behavior unchanged; RC-2 and RC-3 tests still pass.
3. New admitted rollout:
   - first run transforms all chunks;
   - an append transforms only the frontier;
   - an unchanged rerun makes zero provider calls (extend
     `tests/test_codex_incremental_jsonl_route.py`).
4. Race: an admitted path with an existing processed entry gives a visible
   refusal and quarantines once, with no respawn on later events and the
   doctor check WARN.
5. Guards: a frontier-subset violation, a chunk backstop overflow and a size
   ceiling overflow each refuse before any provider call.
6. Continuity: a Codex `compacted` record appended mid-session keeps the
   prefix continuous; truncation and rewrite refuse.
7. Rollback then re-enable refuses visibly for previously admitted paths.

## 9. Canary and acceptance

**Stage 1: manual canary, watcher stopped.** Needs a separate Ryan grant
naming the runtime tip, `admitted_after` and the budget.

1. Start one fresh Codex session after `admitted_after`.
2. Run `convmem index --file` on it three times: after creation, after
   further turns, and with no change.
3. Pass when:
   - run 2 transforms at most frontier + 1 chunks;
   - run 3 makes zero provider calls;
   - the checkpoint, both Chroma collections, `processed.json` and the
     export agree on coverage;
   - one non-admitted pre-activation rollout still routes legacy;
   - child peak memory is recorded.

**Stage 2: 24 h watcher canary.** Needs a separate grant. It also requires the
#308 fix and reconciliation of the watch service memory drop-ins
(`zz-openclaw-watch-limits.conf` re-imposes 4G/3G over the 8G mitigation).
Pass when:

- there are zero refusal loops;
- paid calls per admitted append are bounded to its frontier;
- there are no child scopes at 80% or more of their memory cap and no
  service OOM;
- doctor's index and crash gates PASS.

## 10. What not to build

- Bulk bootstrap.
- Generalizing the bootstrap script (v1.1, separate).
- Cursor JSONL, Crush SQLite or Codex `history.jsonl` routing.
- Streaming parse.
- An automatic exact-list writer.
- Any watcher, config or runtime change.
- Any change to chunking, retrieval or dedupe semantics.

## 11. Questions for Kiro

1. Is a time-bounded, identity-checked admission rule an acceptable
   relaxation of the exact-path rule for this second slice?
2. Should a `session_meta` mismatch on an otherwise admitted path refuse (as
   proposed) or route legacy?
3. Is threshold-1 refusal quarantine with operator-only clearing correct?
   Should it be keyed by path or by (path, prefix digest)? (Kiro: by
   (path, prefix digest); see §13.)
4. Are the defaults right (20 chunks per run, 256 MiB), or should Stage 1
   measure them first?

## 12. Gates and owners

1. Kiro: design review of this exact revision.
2. Ryan: implementation grant.
3. Cursor: implementation; Copilot targeted safety audit; Kiro exact-tip
   recheck.
4. Ryan: Stage 1 grant.
5. Ryan: Stage 2 grant.
6. Ryan: activation.

No gate implies the next.

## 13. Kiro design review — binding conditions

Kiro issued **PASS** on exact revision `9e91973` (2026-10-10), verifying the §7
integration points against `origin/main` `348ec0b` and RC-1–RC-3
non-regression. The runtime-data counts in §2 were not independently
reproduced; the code facts behind them were. These conditions bind the
implementation, and the exact-tip recheck at gate 3 must confirm each one:

1. Citation fix: `adapters/jsonl_prefix.py:141` → `:142`. Done in this
   revision.
2. **The check-5 refusal is mandatory and visible.** A path that passes D1
   checks 1–4 but fails the `session_meta` check emits the D3 refusal marker
   and never produces a legacy ingest tuple. This is RC-1 load-bearing.
3. **The quarantine key is (path, prefix digest),** not the path alone,
   reusing the refused prefix digest that D3 persists.
4. **The D3 refusal class lands before or with the admitted route.** A
   `live_route_refused` from an admitted path quarantines terminally:
   threshold 1, no respawn, doctor WARN. If the #308 terminal-failure fix
   lands first, reuse it. The route must not ship while a refusal still
   respawns on each append (gap verified at `watch.py:593`).
5. Stage 1 measures the D4 and D5 limits before Stage 2. The defaults ship
   only as fail-closed backstops.
6. No scope creep beyond §10.

Kiro's answers to §11: (1) the relaxation is acceptable and contained;
(2) a `session_meta` mismatch refuses; (3) threshold-1 quarantine with
operator-only clearing, keyed by (path, prefix digest); (4) ship the defaults
as backstops and measure them in Stage 1.

## TL;DR

- Admit new Codex rollouts by a time-bounded, identity-checked rule (uuid v7
  time at or after `admitted_after`, filename/uuid/`session_meta` agreement,
  canonical root) instead of exact paths. Pre-activation rollouts stay legacy,
  so there is no bulk bootstrap.
- Close the creation race by installing the config before `admitted_after`.
- Make a refusal terminal in the watcher (quarantine, doctor WARN) so it can't
  loop or hide coverage gaps.
- Bound paid spend (frontier-subset invariant, chunk backstop) and memory
  (size ceiling). Measure in a manual canary before any watcher run.
