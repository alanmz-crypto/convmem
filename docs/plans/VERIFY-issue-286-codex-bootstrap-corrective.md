# [Arc Codex #286] Verification stub — existing Codex rollout bootstrap

**State:** NOT RUN. Planning companion only; no implementation or live-readiness verdict.
**Author:** Codex, 2026-10-18.
**Direction:** [architecture](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md), Kiro PASS at `e0e91bd32f96bce1f8c109a84005ed547d8655ff`; Ryan approved direction in conversation.
**Tasks and contracts:** [execution plan](EXECUTION-issue-286-codex-bootstrap-corrective.md).
**Implementation subject SHA:** NOT IMPLEMENTED. **PR:** none authorized.
**Template:** [VERIFY-TEMPLATE.md](VERIFY-TEMPLATE.md), adapted as an unfilled check list.

## Consequence and scope

Cursor's later authorized work must prove that one exact Codex rollout can be
adopted with bounded paid attempts and recoverable source-only changes while
compatible unrelated writers continue. These proofs do not authorize a live
run. A1 stays parked, and A2 remains stopped.

Scope is the execution plan's T1–T5 only. No production paths, provider calls,
watcher controls, quarantine release, deployment, PR, or global restore belongs
to this mechanical verification. All initial results below are **NOT RUN**.

## Verification design

- **Independent oracle:** parent-owned authoritative-file/foreign-byte snapshots,
  expected format/path hashes, intercepted transport counts, and externally
  controlled process barriers. Receipts are compared to the oracle.
- **Failure injection:** kill before/after each fsync/atomic publication and
  coordinator transition; fail fsync/replace; force lock races and timeouts;
  interleave foreign writes between initial attempt and recovery.
- **Negative controls:** wrong Kiro state identity; third invocation; missing
  permit-before-send; missing legacy commit check; exit-91 deferral; stale
  processed restore; substituted rollback authority; foreign-line normalization.
- **Dual paths:** exact bootstrap/identical-grant recovery; direct index and
  watcher subprocess/parent; legacy and incremental; Chroma and sidecars;
  owner, disjoint writer, unscoped writer, and incompatible writer.

## V0 — Authority, baseline, isolation, and review inputs

**NOT RUN.** Record Ryan's exact Execute grant, reviewed plan SHA, implementation
base/tip, clean worktree, Python environment, externally enforced network and
filesystem isolation, and failure-log redirection before imports.

Execute must record `gate_applicability`, `reason`, `subject_tip_sha`,
`bugbot_reviewed_sha`, `result`, `finding_disposition`, and `authority_reference`
under `EXECUTE-TASK.md`. Runtime/concurrency changes require the later PR-native
review gate. No PR is currently authorized; absent evidence is a pending merge
gate, never an exemption or an invented PASS. An applicable SHA mismatch is FAIL.

## V1 — Format, grant, and v1 compatibility (T1)

**NOT RUN.** Exact v2 schema/hash vectors; state-directory equality; descriptor
identity; all Codex admission checks; rejected history/cross-format/alias and
invalid grants; byte-compatible v1 hashes, Kiro dispatch, and supersession.

## V2 — Read-only preflight (T1)

**NOT RUN.** Zero provider/embedding attempts; unchanged protected files and
metadata; no lock/cache/state directory creation; blockers and proposed counts
only. Positive and refused preflights both satisfy the no-write oracle.

## V3 — Authority crash matrix (T2)

**NOT RUN.** Concurrent claims; reservation with consumed initial invocation
but no mirror/transaction; identical-grant recovery; corrupted/rolled-back
authority; terminal receipt/release windows; ordinal 3 denied. Record every
durable boundary and both sides, with independent authority/count observations.

## V4 — Provider permits and caps (T2)

**NOT RUN.** Permit fsync before send; retry/lost-response accounting; preserved
cumulative cap; prepared reuse; provider-binding/no-fallback checks; Ollama
observation; nested outer/operation permit composition and either-gate denial.
Production guard composition is a separate operational gate, not inferred from
a fake outer-permit implementation.

## V5 — Complete writer mediation (T3)

**NOT RUN.** Fill the execution plan §5 inventory with exact entrypoints,
preparation and commit checks, scope/locks, tests and results. Prove same-source
races in both orders, disjoint progress, pending reservation after death,
unscoped maintenance refusal, protected retry/authority cleanup, bounded waits,
and no paid calls under C1. Missing coverage is FAIL.

## V6 — Watcher/CLI deferral (T3)

**NOT RUN.** Typed signal/exit mapping; deferred path requeue/backoff; unchanged
retry/quarantine state; no false success; malformed/mismatched signal refusal;
terminal-authority race; ordinary unreserved `bootstrap_required` still follows
the existing refusal path. Test actual subprocess and parent handling. Existing
quarantine remains intact.

## V7 — Prefix, commit, and recovery (T4)

**NOT RUN.** Selected-prefix-only chunks after append; replacement/truncation
refusal; real temporary Chroma both-collection crash points; original rollback
hash retained; checkpoint/follower/receipt recovery without new transforms;
source-only processed merge and byte-exact preservation of foreign export/dedupe
records, including malformed/blank lines and concurrent foreign updates.

## V8 — Integrated results and independent sign-off (T5)

**NOT RUN.** Record exact commands/exit codes/counts and evidence paths for V1–V7,
boundary-probe and negative-control failures, applicable static checks, v1
regressions, and full command-to-receipt/command-to-watcher integration.

Report separately: hermetic mechanical result, independent Kiro verdict at the
implementation subject SHA, pending PR-native review, and live readiness.
Applicable skipped proofs cannot yield mechanical PASS. Verifier performs no
corrections or cleanup. Review findings go through the established lane route.

## Ryan gates — not mechanical PASS rows

- Exact implementation authorization: **PENDING**.
- Kiro execution-plan review: **PENDING**.
- Later PR/review/merge and deployment authority: **PENDING**.
- Outer-budget enforcement, compatible writer rollout, health diagnosis and
  fresh baseline, verified backups/source disposition, refreshed numeric A1
  grants: **PENDING** under execution plan §7.
- A1 live execution: **PARKED / NOT AUTHORIZED**. A2: **STOPPED**.

## Evidence log (fill after Execute)

Subject SHA / runner / date / command / exit code / result / independent oracle
reference / residual owner: **NOT RUN**. Do not paste transcript or prompt
content. Keep actual implementation evidence here rather than a new audit log.

**TL;DR:** [Arc Codex] This is an unexecuted verification map for T1–T5. Neither
the stub nor future hermetic PASS grants production execution.

<!-- src: ./VERIFY-TEMPLATE.md — evidence and review-gate structure -->
<!-- ref: ./EXECUTION-issue-286-codex-bootstrap-corrective.md, ./ARCHITECTURE-issue-286-codex-bootstrap-corrective.md — scoped contracts -->
