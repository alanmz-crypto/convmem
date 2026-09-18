# EXECUTION — One-format append-cursor extension

**Arc: Codex** · **State: proposed; Kiro review and Ryan Execute grant required** · 2026-09-17

Companion: [architecture](ARCHITECTURE-generalize-append-cursor.md). This plan
does not authorize implementation, a provider call, live-source indexing,
configuration change, bootstrap, canary, watcher action, or activation.

## 1. Intended result and boundary

The proposed first result is default-off transform reuse for **fresh, isolated
Copilot `events.jsonl` sources** after a valid checkpoint and a verified pure
append. The source prefix is still read and hashed. Existing Kiro behavior,
the normal whole-file legacy route, chunking, prompts, scoring, retrieval,
writer/provenance governance, and Arc Codex P2 remain unchanged.

Codex history/rollout work belongs to the separately pushed Trapdoor Hunt
issue #286 draft until Ryan assigns a common code owner. Cursor and Claude
formats are out of this Execute. A review PASS on this plan is not the
authorization to work on any of them.

## 2. Proposed slices and required evidence

| Slice | Cursor deliverable after Ryan grant | Exit evidence and stop rule |
|---|---|---|
| E0 — writer eligibility | Document installed Copilot CLI version and controlled create, append, resume, compaction, rotation, close trace on temporary sessions; inspect writer implementation where available. Observe source bytes, inode, size, selected-prefix hash, and `workspace.yaml` after each action. | If path reuse rewrites/truncates selected bytes, or metadata cannot be bound, stop before routing. Do not label Copilot append-only from one current file. |
| E1 — parser capability | Add shared complete-line scanner and Copilot-specific complete-prefix view; retain legacy `parse()` output and Kiro prefix API. Bind `workspace.yaml` or its absence, `session.start` fallback, exact raw line ranges, and canonical messages. | Legacy/prefix parity on complete prefixes; malformed/partial/invalid UTF-8 and metadata-change oracles; no provider or Chroma call. |
| E2 — closed coordinator registry | Add one versioned Copilot entry to an explicit registry and route only after normal detect/parser identity agrees. Generalize Kiro-only source ID, snapshot/replay, metadata, fingerprint and result-format constants. Keep default off and isolation-root guard. | Kiro suite unchanged; wrong format/parser/sidecar fails before writes; no source or cache cross-use. |
| E3 — hermetic transaction proof | Exercise fresh Copilot source, one-message append, overlap boundary, rewrite/rotation, malformed line, replay faults, and full-generation prune in isolated temporary state with fake providers and real temporary Chroma. | Complete-prefix coverage and exact canonical/full-rebuild projection parity; both collections and followers converge or restore; zero historical transform calls on verified append; measured bytes read and peak RSS reported separately. |
| E4 — handoff | Publish VERIFY evidence and exact pushed tip for Kiro code review. | Stop at review. No PR or live progression unless Ryan separately directs it; no bootstrap or activation. |

E0 is a hard eligibility gate. If it fails, return a written `NO_COPILOT_ROUTE`
finding with the violating writer action and observed bytes. Replanning for a
different format requires a fresh Ryan scope decision. E1 may be explored as
read-only parser work only if the Execute grant explicitly permits it after an
E0 failure.

## 3. Hermetic verification matrix

| Case | Required oracle |
|---|---|
| Complete append at and around 50-message step / 60-message window boundaries | All selected raw lines accounted for once; final old chunk and new windows rebuilt; stable prior chunks reuse validated artifacts. |
| Partial last line then completion; valid final line without newline | No premature checkpoint advance or skipped accepted message. |
| Blank, ignored, malformed complete, invalid UTF-8, and non-message events | Prefix parser equals defined legacy behavior on complete input; ambiguity refuses; raw byte coverage remains auditable. |
| Sidecar create/edit/remove, `session.start` fallback, and changed canonical context | Snapshot/revalidation detect semantic or digest change; no stale message metadata is reused. |
| Same-size interior rewrite, truncate/regrow, atomic replacement with matching tail, inode reuse | Prior-prefix hash and generation checks refuse reuse; no checkpoint advance from false append. |
| Changed parser version, chunk settings, model, embedding dimension, provenance/dedupe contract | Prepared cache and checkpoint cannot be reused under mismatched fingerprint. |
| Crash after prepared fsync, first write, each collection prune, checkpoint, export/dedupe, processed publish | Replay uses exact durable artifacts with no second model call, or restores exact before-images; both Chroma collections and sidecars agree. |
| Existing processed entry/rows without checkpoint; corrupt cache; wrong parser; path outside isolated root | `bootstrap_required` or fail-closed refusal with zero paid calls and no source/projected mutation. |
| Flag absent/false; Kiro source; concurrent attempts | Existing default and Kiro behavior preserved; source lock serializes a single generation. |

Use only fixture files, fake providers, network denial, and an explicitly
temporary mutable root. Run focused parity and fault suites first. Run the
repo-wide suite on a clean worktree outside the shared repository root for
regression attribution. The 2026-09-17 clean `origin/main` `18f63db` baseline
was **1 failed, 2527 passed, 2 skipped** in 1361.61s; the single deterministic
failure was `tests/test_eval_golden.py::GoldenEvalTests::test_golden_questions`
(6/10 below bar 8), unrelated to incremental indexing. It is not a green
baseline, and this plan does not retune it. Require zero new failures against
a freshly verified clean-main baseline, not a copied count from a polluted
shared checkout. The locked `.claude/worktrees/agent-…` inside ROOT produced
82 of 83 phantom R2b constructor sites; never run R2b inventory verification
from that shared checkout.

## 4. Model-call accounting and adoption

For a source with `N > 0` canonical messages, window 60 and step 50, a full
pass has `1 + ceil(max(0, N - 60) / 50)` chunks. At two paid summarize/distill calls per
chunk, the handoff's *historical* `N=3281` example yields 132 calls. A
verified one-message append after its checkpoint normally transforms one
frontier chunk (two such calls), saving 130 calls for that **example**.
Copilot's actual message counts and edit rate are unmeasured. E3 reports
observed calls and bytes, without extrapolating a fleet total. The excluded,
rolling `~/.codex/history.jsonl` yields no incremental savings here.

Existing-source adoption is **not E0–E4**. A processed hash or existing
Chroma rows do not prove complete source-to-projection coverage or durable
prepared outputs. Any adoption needs a separate exact-source proof or a
one-time full rebuild with measured provider cost, Kiro review, and Ryan's
specific bootstrap grant. No live setting is changed by E0–E4.

## 5. Review and Ryan decision point

1. Kiro reviews the exact planning tip, including the Copilot writer-evidence
   gate, metadata sidecar, Kiro compatibility, replay, and #286 boundary.
2. Ryan decides whether to authorize Cursor for E0–E4 and names the isolated
   resources and stop conditions. A grant for E0 alone is valid.
3. Cursor returns an exact-tip implementation and VERIFY packet to Kiro.
4. Ryan separately decides PR, bootstrap, canary, and activation steps under
   their existing Arc Codex gates. None is granted by this plan.

**TL;DR:** [Arc Codex] One additional format is feasible only after its writer
and parser prove the complete-prefix contract. Copilot is the conditional
first candidate; E0 failure ends the proposed Execute without a substitute.
