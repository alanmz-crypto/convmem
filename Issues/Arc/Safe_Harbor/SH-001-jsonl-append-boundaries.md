# SH-001 — Recovery can corrupt JSONL at a missing final newline

**Arc:** Safe Harbor · **Status:** open, static finding; not reproduced · **Priority:** P2

Codex, 2026-10-25. Source at `1a686753d8fd1b710883050e8a4f9c45b7ae1e26`; same relevant code in inspected `origin/main`. **Confidence: 95% in the code-path conclusion**, not incident likelihood. Local implementation issue affecting T4's event/export completion contract.

## What can go wrong

A complete final JSON object without its newline is accepted by the readers, but the writers concatenate the next object without first separating it. An interrupted append or an externally produced valid final record can therefore turn the next recovery into a corrupting write. The command can report completion before a later read discovers the malformed combined line.

## Source trace

- [conflict_events.py:137](../../../conflict_events.py#L137): `load_events()` uses `splitlines()` and JSON parsing; it does not require a terminal newline. Recovery's additional validator receives already-parsed objects, so it cannot detect the missing delimiter (`propose_decision.py:184–197,805–810`).
- [conflict_events.py:117](../../../conflict_events.py#L117): `append_event_durable()` appends `json.dumps(event) + "\n"` directly. The ordinary append helper at line 60 has the same framing assumption.
- [propose_decision.py:782](../../../propose_decision.py#L782): export completion concatenates preserved raw lines and the new row. The parser at lines 730–744 accepts a last complete object with no newline; `observe.export_projection_records()` does too (`observe.py:162`).
- [propose_decision.py:885](../../../propose_decision.py#L885): after publishing export and APPROVED, recovery returns its action without reloading either resulting JSONL stream.

For example, accepted bytes ending in `{"old":1}` become `{"old":1}{"new":2}\n`. File fsync makes those bytes durable; it does not make them valid JSONL.

Two separate cases need coverage: a nonterminal approval with available durable intent and an unterminated final event; and a missing target export row following an unrelated complete-but-unterminated export row. No malicious actor or concurrent writer is required once that input exists.

## Existing evidence misses this boundary

[The publication fault worker](../../../tests/_safe_harbor_t4_publication.py#L51) injects a partial event using the first 23 characters. That is malformed JSON and correctly refuses. It does not cover a complete object with only the record delimiter missing. This audit did not establish that production currently contains such a tail.

## Bounded resolution

Validate append framing under the existing locks **before Chroma/export effects**. For the authoritative event log, preserve the current fail-closed/no-automatic-tail-repair policy: an unterminated tail should stop for review. Give exports an explicit policy too: either refuse before mutation or preserve a valid last object with a separator in the atomic replacement. Never concatenate objects or discard a tail.

**Proposed isolated evidence, not run:** exercise both real recovery cases above; assert no successful malformed publication, no speculative event append or duplicate APPROVED, and unchanged bytes on refusal. Retain successful newline-terminated controls and the existing malformed-tail control.

## Selected validation and correction scope — 2026-10-25

**Selected by Codex at Ryan's request. October 25 shutdown checkpoint: validation only is assigned to Cursor, queued until Ryan resumes.** Codex supervises scope and reviews the returned evidence. No Cursor session has started, no proof has run, and runtime correction remains ungranted. The runtime-change proposal below is not part of the validation grant. The [issue index](README.md#shutdown-checkpoint--start-here) is the resume entry point.

### Validation before correction

Use an isolated worktree from a pinned current-main revision. Keep the existing Safe Harbor pre-import bootstrap, clean fixture environment, pinned backend/tool identities, network refusal and production-path exclusions. Extend the existing T4 tests; do not run the default suite against the workstation's home/config.

Exercise these through the real admitted recovery path, inspecting durable effects independently:

1. Valid durable intent and APPROVAL_STARTED, with a complete final event object missing only its newline. Demonstrate the old reader/writer path accepts the tail and joins the next event onto it.
2. A recovery that must add an export row, with an unrelated complete final export object missing only its newline. Demonstrate the old path joins the new row onto it.
3. Newline-terminated equivalents complete successfully, with parseable export/events and exactly one terminal APPROVED. Retain malformed-JSON and uncertain-publication controls.

Record each case separately. If either source finding does not reproduce, return that discrepancy and its actual effects; do not change runtime to satisfy a presumed failure.

### Proposed correction — not authorized by the validation assignment

For this first slice, choose **refusal before Chroma mutation** for a nonempty, unterminated event log or export. Preserve the original bytes and report the specific framing problem. Do not truncate, insert a newline into existing production evidence, rewrite history, or infer rollback. An empty export remains a supported case where otherwise valid; an empty event log cannot supply missing approval authority.

Check framing before the native mutation, under the existing governed/export serialization as applicable. Recheck at publication where necessary so an append cannot rely on a stale framing check. Preserve the existing native/export lock order and file/directory durability requirements. A later publication refusal must retain honest partial/unknown-completion reporting.

**Compatibility cost:** a complete final JSON object without its terminator will require investigation even though a tolerant reader can parse it. This deliberately trades that narrow input compatibility for a small, fail-closed correction. General import formatting and automatic tail repair are outside this slice.

Expected runtime surface: `propose_decision.py`, the T4 event helpers in `conflict_events.py`, and `observe.py` only if a shared export-reader precondition is needed. Extend existing T4 publication/refusal tests and their workers. Do not change unrelated reader semantics, approval policy, Restic/target binding, quarantine/release, backend code, lint baseline, or live-test exclusions. Return any additional dependency before widening the scope.

### Acceptance evidence and stop

The corrected cases must refuse before native effects, preserving Chroma content/vectors, export bytes and proposal lifecycle. Successful controls must still complete and survive a fresh-process read. Restore the old framing behavior in a test-only negative control and show that the independent parse/effect assertion detects it. Record interpreter/backend, exact candidate, commands, exits and evidence limitations.

For the queued validation, return the pinned source, test/harness diff, exact commands, per-case observed effects and controls, exits and limitations; then stop before runtime correction. The corrected-case acceptance requirements above apply only if a later correction is authorized. SH-002–SH-004, PR creation/comments, hosted CI, merge, deployment, services, production corpus operations, backups/restores, initializer execution and manual session indexing are outside this slice.

<!-- ref: ./README.md — shutdown checkpoint and validation-only assignment -->
<!-- ref: ./SH-002-revision-export-retry.md — separate partial-export retry case -->
<!-- src: ../../../conflict_events.py, ../../../propose_decision.py, ../../../observe.py, ../../../tests/_safe_harbor_t4_publication.py -->
