# Cursor handoff — bounded local Copilot writer trace

**Arc: Codex**

- **Date:** 2026-09-18
- **Author:** Codex coordination lane
- **For:** Cursor evidence lane
**Authorization:** Ryan explicitly granted the bounded local trace on 2026-09-18. This is a preliminary subset of E0, not Copilot eligibility or an E1–E4 Execute grant.

## Resume state

| Field | Value |
|---|---|
| State | `READY_FOR_CURSOR_LOCAL_TRACE` |
| Planning branch | `plan/2026-09-17-generalize-append-cursor` |
| Kiro-reviewed plan | `53e7b42500728f439bd7f8a1662227e7a08015b7` |
| Landed shared base | `origin/main` at or after PR #307 squash commit `d657767d9351ce4c49e584ec14dfb0a7b8d9e77b` |
| PR | None for this Copilot proposal |
| Ryan gate | The local trace below is granted. Hosted-client proof, E1–E4, PR, bootstrap, canary, and activation require separate decisions. |

## Purpose

Observe how the installed GitHub Copilot CLI writes a fresh `events.jsonl`
session while using a local model. A destructive writer action can reject the
candidate early. A clean local trace is preliminary evidence only: it does not
prove that the hosted-client writer follows the same path or finish full E0.

Read the [current-state brief](../plans/STATUS-generalize-append-cursor.md)
and [E0 plan](../plans/EXECUTION-generalize-append-cursor.md) first. The shared
scanner and registry are on `main`; the planning checkout predates their merge.

## Authorized resources and actions

1. Use installed Copilot CLI **1.0.86** and a locally installed Ollama model.
   Check versions read-only before starting. Run with `COPILOT_OFFLINE=true`,
   a loopback-only local provider URL, `--no-auto-update`,
   `--disable-builtin-mcps`, and `--no-custom-instructions`. Keep the process
   in a temporary empty workspace outside the repo. If local-only operation
   cannot be established, stop without switching to hosted inference.
2. Create one new, unique temporary directory with the prefix
   `/tmp/convmem-copilot-e0-local.`. Set `COPILOT_HOME` inside it; keep the
   temporary workspace and trace evidence there too. Refuse to reuse an
   existing directory or a pre-existing Copilot session. Do not read or index
   existing user sessions.
3. Use only short inert prompts with no tool, shell, file, or code request.
   Observe native **create → append → resume → compact → close** actions.
   At most **six model-using actions total**, counting any model-backed
   compaction, and at most **15 minutes of client activity**. Stop when either
   bound is reached. Attempt rotation only if the CLI offers a native action
   within those bounds; do not induce rotation by editing files yourself.
4. After each action, capture the actual session path, device/inode, size,
   selected-prefix SHA-256, file SHA-256, and whether the prior bytes remain
   identical. Record `workspace.yaml` existence/content digest and the
   `session.start` id/fallback observation. Inspect complete-line and partial
   final-line boundaries. Keep any raw transcript in the temporary directory;
   report only needed metadata and short redacted evidence excerpts.
5. Inspect local or published writer implementation only if available without
   additional provider actions. State explicitly when writer code is not
   available. Return the CLI version, action-by-action measurements, whether
   rotation was observed, and an evidence-limited finding to Ryan. Preserve
   the chat through Track A at handoff.

**External cost ceiling:** zero GitHub-hosted or other external model calls;
zero external provider spend. Loopback calls to the local Ollama provider are
the only model calls granted. The Copilot CLI credit-limit flag is a soft
limit and is **not** a cost control for this grant.

## Stop conditions and non-grants

Stop immediately on any attempted external provider/auth request, inability
to enforce local-only operation, unexpected tool execution, source-byte
rewrite/truncation/replacement, or a metadata change that cannot be bound to
the session. Report the violating action and observed bytes. A negative trace
may support `NO_COPILOT_ROUTE`; a positive local trace must be reported as
**preliminary**, with hosted writer parity and any unobserved rotation still
open. Do not substitute Cursor or Codex JSONL if Copilot fails.

This grant permits temporary trace files only. It grants no tracked code,
test, plan, runtime configuration, registry, provider, Chroma, watcher,
bootstrap, production source, live canary, or activation change. Do not run
E1–E4 or open a PR from this trace. The later Copilot shared-code writer remains
unassigned.

## Handoff result

Return a compact action table with measurements and a verdict limited to:
`NO_COPILOT_ROUTE` with violating bytes, `LOCAL_TRACE_INCOMPLETE` with reason,
or `LOCAL_TRACE_CONSISTENT` with hosted parity and unobserved actions listed.
Ryan decides whether any further E0 proof is worth a separate hosted-client
grant. Kiro's plan PASS at `53e7b42` granted no operation; this explicit Ryan
grant is the sole authority for the local trace.

**TL;DR:** [Arc Codex] Cursor may run one bounded offline local Copilot writer
trace in temporary resources. A clean result is preliminary evidence, not
Copilot route eligibility or an implementation grant.
