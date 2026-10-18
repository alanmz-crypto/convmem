# [Arc Codex #286] Verification stub — existing Codex rollout bootstrap

**State:** T1 scoped mechanical **COMPLETE** (V0–V2 **PASS** under bwrap). V3–V8 **NOT RUN**. v2 live execution **closed**.
**Author:** Codex, 2026-10-18.
**Direction:** [architecture](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md), Kiro PASS at `e0e91bd32f96bce1f8c109a84005ed547d8655ff`; Ryan approved direction in conversation.
**Tasks and contracts:** [execution plan](EXECUTION-issue-286-codex-bootstrap-corrective.md).
**Execution authority:** Ryan granted Cursor T1–T5 and hermetic verification after Kiro plan PASS at `9423900`; see the [Execute handoff](../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md).
**Tested code SHA:** `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` (T1 implementation + contract + bwrap gate). **Documentation evidence tip:** `0c0cc8c47bd3f6f2bf5fd9f35b11d11eda11f654`. **PR:** none authorized.
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

**PASS (external bwrap boundary).** Prior evidence rows that relied on in-process `install_network_denial()` hooks (`5d5ec91`, `45b07d6`) are **withdrawn** — they do not satisfy execution plan §6.

| ID | Check | Result |
|----|-------|--------|
| V0a | Ryan Execute grant (T1–T5 + hermetic verification) | PASS — execute handoff on branch |
| V0b | Reviewed execution plan SHA | PASS — `942390001bca407c1c28e9972c443ee7612e1c1b` |
| V0c | T1 code baseline | PASS — includes `439b851` v2 grant/dry-run + later T1 contract/bwrap harness at `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` |
| V0d | External network enforcement | PASS — `bwrap --unshare-net`; parent loopback positive control; dual AF_INET probe artifacts written **inside** bwrap both `connect_failed` (`tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_external_network_namespace_denied`) |
| V0e | External filesystem enforcement | PASS — narrow production-path `ro-bind` masks + scratch bind; capability probe (`test_external_filesystem_masks_production_paths`) |
| V0f | Worker probe without Python network monkeypatch | PASS — `boundary-probe` uses real `socket.connect`; errno recorded (`test_worker_boundary_probe_without_python_network_hooks`) |
| V0g | Temporary HOME/config/data + synthesis log redirect | PASS — `sanitized_worker_env()` + worker sets `ingest._SYNTHESIS_FAIL_LOG` under isolation root before pytest |
| V0h | Host bwrap availability | PASS — `bwrap` + user-ns probe available on runner |

Execute fields (no PR-native review yet):

| Field | Value |
|-------|-------|
| `gate_applicability` | `pending` |
| `reason` | No PR authorized |
| `subject_tip_sha` | `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` |
| `bugbot_reviewed_sha` | `n/a` |
| `result` | `n/a` |
| `finding_disposition` | `none` |
| `authority_reference` | Ryan grant — CODEX-2026-10-18 execute handoff |

```bash
cd /home/lauer/.local/share/convmem/worktrees/fix-2026-10-18-issue-286-codex-bootstrap
git checkout 517d014a0be11c6d70c985aa35a8c3cbdac4fe71
python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py
# exit 0; 4 passed (requires host bwrap + user namespaces)
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

- Exact Cursor T1–T5 and hermetic verification authorization: **GRANTED; T1 scoped mechanical COMPLETE; T2–T5 NOT STARTED**.
- Kiro execution-plan review: **PASS at `942390001bca407c1c28e9972c443ee7612e1c1b`**, written verdict supplied by Ryan; precision notes incorporated in the Execute handoff.
- Later PR/review/merge and deployment authority: **PENDING**.
- Outer-budget enforcement, compatible writer rollout, health diagnosis and
  fresh baseline, verified backups/source disposition, refreshed numeric A1
  grants: **PENDING** under execution plan §7.
- A1 live execution: **PARKED / NOT AUTHORIZED**. A2: **STOPPED**.

## Evidence log (fill after Execute)

| Date | SHA role | Command | Exit | Result | Notes |
|------|----------|---------|------|--------|-------|
| 2026-10-18 | `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` | `python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py` | 0 | PASS | 4 tests; external bwrap net+fs |
| 2026-10-18 | `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` | bwrap worker pytest bundle | 0 | PASS | 25 passed (T1 contract + v1 regressions) |
| 2026-10-18 | `5d5ec91` / `45b07d6` | prior in-process hook gate | — | **invalid** | withdrawn — not external enforcement |
| 2026-10-18 | `439b851` | ad hoc pytest without bwrap | — | **not hermetic** | implementation only |

**TL;DR:** [Arc Codex] T1 V0–V2 PASS at tested code `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` with bwrap boundary. V3–V8 NOT RUN. Documentation tip `0c0cc8c47bd3f6f2bf5fd9f35b11d11eda11f654`.

<!-- src: ./VERIFY-TEMPLATE.md — evidence and review-gate structure -->
<!-- ref: ./EXECUTION-issue-286-codex-bootstrap-corrective.md, ./ARCHITECTURE-issue-286-codex-bootstrap-corrective.md — scoped contracts -->
