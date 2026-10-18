# [Arc Codex #286] Verification stub — existing Codex rollout bootstrap

**State:** T1 mechanical gates V0–V2 **PASS** (hermetic). V3–V8 **NOT RUN**. v2 live execution remains **closed**.
**Author:** Codex, 2026-10-18.
**Direction:** [architecture](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md), Kiro PASS at `e0e91bd32f96bce1f8c109a84005ed547d8655ff`; Ryan approved direction in conversation.
**Tasks and contracts:** [execution plan](EXECUTION-issue-286-codex-bootstrap-corrective.md).
**Execution authority:** Ryan granted Cursor T1–T5 and hermetic verification after Kiro plan PASS at `9423900`; see the [Execute handoff](../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md).
**Implementation subject SHA:** `5d5ec91ad6d1b8e8f7258675508e1612552ae01a` (includes T1 hermetic harness + this evidence). **PR:** none authorized.
**Template:** [VERIFY-TEMPLATE.md](VERIFY-TEMPLATE.md), adapted as an unfilled check list.

## Consequence and scope

Cursor's later authorized work must prove that one exact Codex rollout can be
adopted with bounded paid attempts and recoverable source-only changes while
compatible unrelated writers continue. These proofs do not authorize a live
run. A1 stays parked, and A2 remains stopped.

Scope is the execution plan's T1–T5 only. No production paths, provider calls,
watcher controls, quarantine release, deployment, PR, or global restore belongs
to this mechanical verification. V0–V2 rows below are filled from hermetic Execute evidence. V3–V8 remain **NOT RUN** until dependent tasks land.

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

**PASS (hermetic, T1 scope).** Prior pytest runs on commit `439b851` without the boundary worker are **not** claimed as hermetic evidence.

| ID | Check | Result |
|----|-------|--------|
| V0a | Ryan Execute grant for Cursor T1–T5 + hermetic verification | PASS — [Execute handoff](../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md) |
| V0b | Reviewed execution plan SHA | PASS — `942390001bca407c1c28e9972c443ee7612e1c1b` |
| V0c | Implementation code baseline (handoff pin) | PASS — branch rooted at handoff; T1 code parent `483373f1cef2142847fcd9c276196593a72a0ecf` |
| V0d | Subject tip SHA (implementation + evidence) | PASS — `5d5ec91ad6d1b8e8f7258675508e1612552ae01a` |
| V0e | Python interpreter | PASS — `Python 3.13.12`, `pytest 9.1.1` |
| V0f | Externally enforced isolation before imports | PASS — worker `tests/issue_286_codex_bootstrap_isolation_worker.py` installs network/service denial and `IsolationBoundary` with forbidden production roots via `sanitized_worker_env()`; parent gate `tests/test_issue_286_codex_bootstrap_hermetic_gate.py` |
| V0g | Negative boundary probes | PASS — `boundary-probe`: `network=IsolationViolation`, `watcher=IsolationViolation`, `forbidden_root=IsolationViolation`, `root_escape=IsolationViolation`; empty credential and production override env lists |
| V0h | Temporary HOME/config/data + synthesis failure log redirect | PASS — worker `pytest` sets `HOME`/`XDG_*` under tokenized root; redirects `ingest._SYNTHESIS_FAIL_LOG` to `<root>/logs/synthesis_failures.jsonl` before pytest collects tests |
| V0i | Worktree discipline | PASS — isolated worktree `/home/lauer/.local/share/convmem/worktrees/fix-2026-10-18-issue-286-codex-bootstrap`, branch `fix/2026-10-18-issue-286-codex-bootstrap` |

Execute evidence (`EXECUTE-TASK.md` fields recorded here; no PR-native review yet):

| Field | Value |
|-------|-------|
| `gate_applicability` | `pending` |
| `reason` | No PR authorized; runtime/concurrency review is a later merge gate |
| `subject_tip_sha` | `5d5ec91ad6d1b8e8f7258675508e1612552ae01a` |
| `bugbot_reviewed_sha` | `n/a` |
| `result` | `n/a` |
| `finding_disposition` | `none` |
| `authority_reference` | Ryan grant in CODEX-2026-10-18 execute handoff |

```bash
cd /home/lauer/.local/share/convmem/worktrees/fix-2026-10-18-issue-286-codex-bootstrap
git rev-parse HEAD
python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py
# exit 0; 3 passed
```

## V1 — Format, grant, and v1 compatibility (T1)

**PASS (hermetic).** Scoped tests run inside the isolation worker subprocess (10 tests). Synthetic fixtures only; no real transcript reads.

| ID | Check | Result |
|----|-------|--------|
| V1a | v2 grant field set + independent hash oracle | PASS — `tests/test_issue_286_codex_bootstrap_v2_t1.py::test_v2_hash_vectors_independent_oracle` |
| V1b | Negative control: Kiro-default `source_state_id` rejected | PASS — `test_v2_rejects_kiro_default_state_id` |
| V1c | v1 grant parse/hash compatibility | PASS — `test_v1_grant_parse_unchanged` |
| V1d | v1 strict grant shape/hash fixtures | PASS — `tests/test_incremental_jsonl_bootstrap_command.py` (3 tests) |
| V1e | Provider binding (paid transport) | PASS — `test_paid_transport_disables_automatic_redirects` |
| V1f | One-recovery invocation journal | PASS — `test_invocation_journal_allows_exactly_one_recovery` |
| V1g | Predecessor-preserving supersession | PASS — `test_admissible_supersession_archives_exact_bytes_and_preserves_evidence` |

Published synthetic v2 hash oracle (independent worker `hash-oracle`; metadata digests only):

| Field | Value |
|-------|-------|
| `operation_id` | `72ed0df0e35939ad0e8f9446505821ff520d4b3d81267175f106eacae8ab209f` |
| `grant_fingerprint_v2` | `d4cc0d72de7c0817350f5ea8c437fa8ad553cb7ca4b7078a0589ebcbcd73d8e0` |
| `source_state_id` (format-bound) | `92a0cc170c15b58240963d3e7d9abc27e2432966246da9f230484665198520d9` |
| `kiro_default_state_id` (negative reference) | `141a770cbd3ee9a3f167ee5e839956e8f57788468c91034fc2c29110d26cf39c` |

```bash
python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_t1_and_v1_regressions_in_isolated_worker
# exit 0; worker subprocess reports: 10 passed
```

## V2 — Read-only preflight (T1)

**PASS (hermetic).** Dry-run performs no writes under isolated config roots.

| ID | Check | Result |
|----|-------|--------|
| V2a | `--dry-run` / `dry_run_v2` immutability oracle | PASS — `test_dry_run_no_writes` (mtime unchanged for state, processed, chroma paths) |
| V2b | Proposed packet exposes format-bound vs Kiro-default state IDs | PASS — `packet["source_state_id"] != packet["kiro_default_state_id"]` |
| V2c | Provider/embedding attempts | PASS — zero (validators + metadata reads only; no coordinator construction) |

**Remaining T1 gaps (not V2 failures):** Codex admission matrix beyond dry-run happy path, descriptor cross-surface equality across transaction artifacts, and explicit rejected-grant corpora are partially covered by unit tests but not exhaustively catalogued here. T2+ surfaces remain unimplemented.

```bash
# Covered by the same isolated 10-test bundle as V1 (includes test_dry_run_no_writes)
```

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

- Exact Cursor T1–T5 and hermetic verification authorization: **GRANTED by Ryan; T1 hermetic gate PASS; T2–T5 NOT STARTED**.
- Kiro execution-plan review: **PASS at `942390001bca407c1c28e9972c443ee7612e1c1b`**, written verdict supplied by Ryan; precision notes incorporated in the Execute handoff.
- Later PR/review/merge and deployment authority: **PENDING**.
- Outer-budget enforcement, compatible writer rollout, health diagnosis and
  fresh baseline, verified backups/source disposition, refreshed numeric A1
  grants: **PENDING** under execution plan §7.
- A1 live execution: **PARKED / NOT AUTHORIZED**. A2: **STOPPED**.

## Evidence log (fill after Execute)

| Date | Subject SHA | Command | Exit | Result | Notes |
|------|-------------|---------|------|--------|-------|
| 2026-10-18 | `5d5ec91ad6d1b8e8f7258675508e1612552ae01a` | `python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py` | 0 | PASS | 3 gate tests; spawns isolated worker with boundary probe + 10 scoped T1/v1 tests |
| 2026-10-18 | `5d5ec91ad6d1b8e8f7258675508e1612552ae01a` | worker `boundary-probe` | 0 | PASS | All negative probes return `IsolationViolation` |
| 2026-10-18 | `439b851` | (ad hoc, pre-isolation) | — | **not hermetic** | T1 code landed; evidence gate intentionally not filed |

**TL;DR:** [Arc Codex] T1 hermetic V0–V2 PASS at `5d5ec91ad6d1b8e8f7258675508e1612552ae01a`. V3–V8 and live readiness remain NOT RUN / not authorized.

<!-- src: ./VERIFY-TEMPLATE.md — evidence and review-gate structure -->
<!-- ref: ./EXECUTION-issue-286-codex-bootstrap-corrective.md, ./ARCHITECTURE-issue-286-codex-bootstrap-corrective.md — scoped contracts -->
