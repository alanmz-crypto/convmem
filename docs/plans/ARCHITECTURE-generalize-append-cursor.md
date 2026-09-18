# ARCHITECTURE — Generalize the append cursor by proven format capability

**Arc: Codex** · **State: Kiro PASS at `9e2d0ef`; post-merge reconciliation for targeted recheck; no Execute or activation grant** · 2026-09-18

Companion: [execution plan](EXECUTION-generalize-append-cursor.md) and
[current-state brief](STATUS-generalize-append-cursor.md). This packet answers
the [Claude planning handoff at `439b5fc`](https://github.com/alanmz-crypto/convmem/blob/439b5fc/docs/inter-model/CODEX-2026-09-17-generalize-append-cursor-handoff.md),
which lives on a separate pushed branch. The original review inspected
`origin/main` at `18f63db`. This revision reconciles the plan with issue #286,
squash-merged through [PR #307](https://github.com/alanmz-crypto/convmem/pull/307)
as `d657767d9351ce4c49e584ec14dfb0a7b8d9e77b` on `main`.

## 1. Decision and scope

**Yes, the coordinator's mechanism can be generalized, but JSONL syntax or an
adapter's `parse()` method alone is insufficient eligibility.** The current
coordinator binds format identity, complete-prefix parsing, source and
sidecar continuity, chunk identity, prepared replay, and two-collection
rollback. Issue #286 has now landed the *closed, versioned adapter capability
registry* and complete-line scanner on `main`. Extend that reviewed seam by
one approved format at a time. The registry is code authority; configuration
cannot introduce a format, and isolated routes require their explicit boundary.
A broad `eligible_formats` config list
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
| `jsonl_kiro_session` | `adapters/kiro_session_jsonl.py` provides a `CompletePrefixView`; production coordinator and fault/replay tests target it. | Existing route; preserve behavior. |
| `jsonl_codex_rollout` | Issue #286 added a complete-prefix adapter and an isolated route on `main`. [OpenAI's rollout recorder tests](https://github.com/openai/codex/blob/main/codex-rs/rollout/src/recorder_tests.rs) exercise append, while [rollout persistence](https://github.com/openai/codex/blob/main/codex-rs/rollout/src/lib.rs) also exposes compression/materialization. | Existing isolated #286 route; this plan grants no production use or change to it. |
| `jsonl_copilot_session` | Local adapter reads per-session `events.jsonl` and `workspace.yaml`; [GitHub's CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference) calls it an event log used for resume. This does not promise no rewrite, truncation, or sidecar change. | First *candidate*, still ineligible until a controlled writer/resume/rotation trace and parser parity pass. |
| `jsonl_cursor` | `adapters/jsonl_chat.py` parses agent transcripts, but `detect.py` recognizes any JSONL path containing `agent-transcripts`; no writer or lifecycle contract is documented in the inspected repo. | Excluded until exact path scope and append/rewrite behavior are independently established. |
| `jsonl_codex_history` | Issue #286 added a complete-prefix adapter but restricts its route to fresh isolated sources. The observed production `~/.codex/history.jsonl` is rolling, prompts-only, and excluded from watch/index; its selected prefix can disappear as entries age out. | Keep the existing isolated route separate. Production history remains excluded, with no Copilot-plan savings claim. |
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

Issue #286 already added a read-only complete-line scanner in
`adapters/jsonl_prefix.py`, with `CompletePrefixView`, accepted-message byte
ranges, and per-line outcomes. `adapters/jsonl_io.py` remains the whole-file
legacy iterator. Reuse the landed scanner; do not create a second one. It
reports raw line outcomes but leaves message classification to each adapter.
The proposed Copilot adapter must own a versioned
`parse_complete_prefix(snapshot, raw=...)` equivalent that maps records into
the **same ordered canonical messages as its legacy `parse()`**, with declared
sidecar dependencies.

The landed `incremental_jsonl_formats.py` registry records:

```text
format id → expected legacy adapter module + prefix parser + contract version
          + tool + snapshot filename + optional sidecar path
```

The coordinator checks normal `detect_format()` and `get_parser()` dispatch
against the expected adapter module, then calls the registered prefix parser.
The proposed Copilot entry must preserve that check. An unlisted format,
mismatched parser, unsupported sidecar, or invalid prefix must refuse before
model calls or projection writes. Preserve the now-landed Kiro and isolated
Codex routes as regression oracles. The coordinator, not `watch.py`, continues
to own state, replay, writer/pruner use, and processed publication.

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

The merged coordinator retains Kiro constants as defaults but obtains the
active format, contract version, snapshot filename, and optional sidecar path
from `IncrementalFormatSpec`. Its route allowlist still defaults to Kiro and
adds Codex only under `CONVMEM_INCREMENTAL_ROOT`. A Copilot entry must update
both the code-owned registry and isolated route policy without widening the
normal production route. Changing only the allowlist would still produce a
false continuity claim.

## 5. Cost and performance claim

With the current `chunk_size=60`, `chunk_overlap=10`, starts advance by 50
messages. For the handoff's 3,281-message **historical example**, a full pass
creates 66 chunks and about 132 summarize/distill calls. With a valid
checkpoint and one complete appended message, the existing final chunk is
the frontier, so the analogous incremental pass normally transforms one
chunk: about two such calls, or 130 fewer (98.5%). This is an illustrative
per-touch transform saving, **not** a forecast for Copilot or rollout traffic.
The observed 3,281-line production Codex `history.jsonl` is already excluded, so this plan saves
zero additional calls on that file. Copilot source sizes, touch rates, and
eligibility have not been measured; aggregate savings cannot yet be stated.
One-time bootstrap may pay the full transform cost and must be measured and
authorized separately.

The first implementation still reads, hashes, and snapshots complete prefixes
at multiple ingest boundaries. It promises historical *transform* reuse, not
O(tail) file reads or a watcher memory fix. A later tail-only I/O route needs a
separate source-mutation authority design.

## 6. Relationship to issue #286 and review decision

The [issue #286 architecture](https://github.com/alanmz-crypto/convmem/blob/d657767d9351ce4c49e584ec14dfb0a7b8d9e77b/docs/plans/ARCHITECTURE-watch-incremental-index.md)
and companion execution plan landed under **Arc Trapdoor Hunt** through PR
#307. This packet reuses their shared registry and scanner; it does not grant
or modify the isolated Codex routes. The apparent history conflict is now
bounded: #286 permits fresh isolated Codex history sources, while the observed
rolling production `~/.codex/history.jsonl` stays excluded. Copilot E0 still
must prove its own writer behavior before a Copilot route can be considered.

**Targeted Kiro recheck request:** Does this post-merge reconciliation reuse
the landed registry/scanner and preserve the prior E0 hard gate, Kiro/Codex
route isolation, sidecar authority, and fail-closed replay? Does Copilot need
any additional per-format sidecar or projection invariant before Execute?
Return PASS/FAIL and conditions on this exact revision. Kiro review does not
authorize Execute; Ryan decides whether to grant the bounded first slice.
