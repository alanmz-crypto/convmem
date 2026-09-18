# ARCHITECTURE — Generalize the append cursor by proven format capability

**Arc: Codex** · **State: draft for Kiro review; no Execute or activation grant** · 2026-09-17

Companion: [execution plan](EXECUTION-generalize-append-cursor.md) and
[current-state brief](STATUS-generalize-append-cursor.md). This packet answers
the [Claude planning handoff at `439b5fc`](https://github.com/alanmz-crypto/convmem/blob/439b5fc/docs/inter-model/CODEX-2026-09-17-generalize-append-cursor-handoff.md),
which lives on a separate pushed branch. Baseline inspected: `origin/main`
`18f63db`.

## 1. Decision and scope

**Yes, the coordinator's mechanism can be generalized, but JSONL syntax or an
adapter's `parse()` method alone is insufficient eligibility.** The current
Kiro coordinator binds format identity, complete-prefix parsing, source and
sidecar continuity, chunk identity, prepared replay, and two-collection
rollback. Extend it through a *closed, versioned adapter capability registry*,
one approved format at a time. The registry is code authority; configuration
can only turn an approved route off. A broad `eligible_formats` config list
would allow an unreviewed format to inherit authority claims it cannot prove.

The first proposed format is **Copilot `events.jsonl`**, contingent on writer
evidence and prefix/legacy parity. Its parser already provides canonical
messages and session metadata, and it is outside the Codex history/rollout
proposal for issue #286. If the evidence gate fails, stop: this plan does not
silently substitute Cursor or Codex. The current Kiro route remains the
regression oracle, default off. No production source, provider, watcher,
exclusion, config, or activation action follows from this design.

## 2. Candidate decision record

| Detected format | Evidence available now | Disposition |
|---|---|---|
| `jsonl_kiro_session` | `adapters/kiro_session_jsonl.py:151` returns a `CompletePrefixView`; production coordinator and fault/replay tests already target it. | Existing route; preserve behavior. |
| `jsonl_codex_rollout` | Local adapter reads `~/.codex/sessions/**/rollout-*.jsonl`; [OpenAI's rollout recorder tests](https://github.com/openai/codex/blob/main/codex-rs/rollout/src/recorder_tests.rs) exercise append, while [rollout persistence](https://github.com/openai/codex/blob/main/codex-rs/rollout/src/lib.rs) also exposes compression/materialization. Append in a normal writer path does not establish a permanent path/inode contract. | Separate Trapdoor Hunt issue #286 draft at `6b62f0f` already plans this. Do not duplicate or grant it here. |
| `jsonl_copilot_session` | Local adapter reads per-session `events.jsonl` and `workspace.yaml`; [GitHub's CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference) calls it an event log used for resume. This does not promise no rewrite, truncation, or sidecar change. | First *candidate*, still ineligible until a controlled writer/resume/rotation trace and parser parity pass. |
| `jsonl_cursor` | `adapters/jsonl_chat.py` parses agent transcripts, but `detect.py` recognizes any JSONL path containing `agent-transcripts`; no writer or lifecycle contract is documented in the inspected repo. | Excluded until exact path scope and append/rewrite behavior are independently established. |
| `jsonl_codex_history` | The handoff records a rolling, prompts-only file; the 3,281-line cost source has been excluded from watch/index. Its selected prefix can disappear as old entries age out. | Excluded. No append-cursor eligibility or savings claim. |
| `jsonl_claude_session` | No adapter exists. Its separate Cursor handoff has independent gates. | Excluded; a future adapter could implement this same capability after its own review. |

SQLite, markdown, and other formats are out of scope. A snapshot of a growing
file is evidence of growth, not proof that its writer never rewrites it.
Before eligibility, capture the installed writer version and a controlled
trace of create, append, resume, compaction, rotation, and close; compare
device/inode, complete-prefix bytes/hash, size, and sidecar values at each
step. Inspect upstream writer code where available. If any step rewrites, the
route must either refuse/rebuild under a separately granted cost policy or
remain ineligible. Runtime continuity checks remain required even after a
writer trace passes, since clients can change behavior later.

## 3. Shared seam

`adapters/jsonl_io.py` currently yields dictionaries and skips bad lines; it
cannot report complete byte boundaries or accepted-record ranges. Add one
low-level *read-only* complete-line scanner there, accepting an already
captured byte prefix and returning raw line ranges and parse outcomes. It
must never decide which records are messages. Each eligible adapter owns a
versioned `parse_complete_prefix(snapshot, raw=...)` equivalent that maps
records into the **same ordered canonical messages as its legacy `parse()`**,
with accepted-message byte ranges and declared sidecar dependencies.

The coordinator owns one registry entry per reviewed format:

```text
format id → legacy parser identity + prefix parser + contract version
          + snapshot filename + sidecar capture/revalidation rules
```

It selects the entry only after normal `detect_format()` and `get_parser()`
agree. It never falls through to a generic JSONL parser. A missing method,
unlisted format, mismatched parser, unsupported sidecar, or invalid prefix
returns a refusal before model calls or projection writes. Preserve the Kiro
adapter's public `CompletePrefixView` and current outputs as a compatibility
boundary; a new shared scanner may sit beneath it only after exact Kiro parity
tests. The existing coordinator, not `watch.py`, continues to own state,
replay, writer/pruner use, and processed publication.

For Copilot, `workspace.yaml` can affect `session_id` and workspace, while a
`session.start` event can supply fallback values. Capture the sidecar (or its
absence) with the same selected source prefix, bind the canonical fields and
content digest to the checkpoint, and revalidate before commit. A change in
effective metadata invalidates reuse; a changed sidecar digest may conservatively
require rebuild even if effective fields match. This is a cost trade-off, not
a reason to ignore metadata. A source file lacking a final newline contributes
only the preceding complete prefix; the trailing bytes remain pending.

## 4. Authority and failure contract

1. Source JSONL plus parser-relevant sidecars are input authority. A committed
   checkpoint is processing/recovery authority. Prepared artifacts, Chroma,
   export, dedupe logs, and `processed.json` are derived followers.
2. State ID, checkpoint, prepared key, and transform fingerprint bind exact
   canonical path, detected format, adapter contract version, sidecar identity,
   chunk settings, prompts/models/embedding, provenance, dedupe, and relevant
   implementation revision. Kiro, Copilot, Codex, and Cursor cannot share
   state or cache by accident.
3. Before reusing history, prove the prior *complete prefix* is still byte
   identical and source generation is continuous. A selected prefix may gain
   a pure append; replacement, truncation, interior rewrite, rotation, or
   changed parse-relevant sidecar requires `rebuild_required` or refusal with
   the previous checkpoint intact. Size or matching tail alone never proves
   continuity. Revalidate the selected prefix immediately before checkpoint
   publication.
4. Every complete raw line is classified as emitted or intentionally skipped
   by its adapter. Malformed complete lines follow explicit legacy parity;
   invalid UTF-8, ambiguous parsing, or disagreement between prefix and legacy
   parsers fails closed. A partial final line is never counted as skipped.
5. Recompute the overlap frontier from canonical message offsets, preserve
   unchanged historical artifact IDs, and build a complete physical keep set
   across **both** Chroma collections. Prepared outputs are fsynced before any
   write. Crash replay validates cached inputs/format/fingerprint and never
   calls a provider twice for an already applied transform. Exact before-images
   restore both collections and affected sidecars if replay cannot be proven.
6. Existing sources with processed entries or Chroma rows but no checkpoint
   remain `bootstrap_required`. No `processed.json` hash is treated as a
   complete projection proof. Bootstrap/rebuild has a separate Ryan cost grant.
7. The flag remains absent/false by default, and `CONVMEM_INCREMENTAL_ROOT`
   isolation remains mandatory for this Execute. The normal watcher path is
   unchanged. No live canary, source adoption, or activation is implied.

The current implementation has literal Kiro format/contract constants,
Kiro-only snapshot names, and a `session.json` revalidation path in
`incremental_jsonl.py` (`:42`, `:526–600`, `:1287–1300`, `:1512`). The
registry must replace all of these assumptions together. Changing only the
eligibility comparison would produce a false continuity claim.

## 5. Cost and performance claim

With the current `chunk_size=60`, `chunk_overlap=10`, starts advance by 50
messages. For the handoff's 3,281-message **historical example**, a full pass
creates 66 chunks and about 132 summarize/distill calls. With a valid
checkpoint and one complete appended message, the existing final chunk is
the frontier, so the analogous incremental pass normally transforms one
chunk: about two such calls, or 130 fewer (98.5%). This is an illustrative
per-touch transform saving, **not** a forecast for Copilot or rollout traffic.
The 3,281-line Codex `history.jsonl` is already excluded, so this plan saves
zero additional calls on that file. Copilot source sizes, touch rates, and
eligibility have not been measured; aggregate savings cannot yet be stated.
One-time bootstrap may pay the full transform cost and must be measured and
authorized separately.

The first implementation still reads, hashes, and snapshots complete prefixes
at multiple ingest boundaries. It promises historical *transform* reuse, not
O(tail) file reads or a watcher memory fix. A later tail-only I/O route needs a
separate source-mutation authority design.

## 6. Relationship to issue #286 and review decision

The pushed [issue #286 architecture](https://github.com/alanmz-crypto/convmem/blob/plan/2026-09-17-issue-286-incremental-index/docs/plans/ARCHITECTURE-watch-incremental-index.md)
and companion execution plan already propose Codex history/rollout work under
**Arc Trapdoor Hunt**. This packet does not review, supersede, merge, or grant
that work. Its overlap is the need for a versioned complete-prefix contract
and fail-closed coordinator; Kiro and Ryan should choose one owner for any
eventual shared-code change before either Execute. In particular, the #286
draft includes Codex *history*, whereas this packet excludes it because the
new handoff reports rolling behavior and production exclusion. That factual
conflict needs resolution before any Codex-format implementation.

**Kiro review request:** Is the closed registry plus per-adapter prefix
contract sufficient to preserve Kiro authority/replay while adding one
proven Copilot format? Does the writer-evidence gate establish enough to make
Copilot eligible? Is another per-format sidecar or projection invariant missing?
Return PASS/FAIL and conditions on this exact revision. Kiro review does not
authorize Execute; Ryan decides whether to grant the bounded first slice.
