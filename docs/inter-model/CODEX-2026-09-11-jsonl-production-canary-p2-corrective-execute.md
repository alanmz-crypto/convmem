# Implementation Handoff: Arc Codex P2 Transfer Seam Corrective Pass

**Arc:** Codex

**Date:** 2026-09-11

**Author:** Codex architecture lane

**For:** Cursor implementation lane

**Authorization:** Ryan, 2026-09-11 — hermetic corrective implementation pass after
Kiro PASS on the blocked P2 capability-gap packet (PR #298 merge `8741774`, reviewed
tip `77e6e2eafc030b5add8d2da47419a2e83d1ade9b`)

**Design review:** Kiro PASS_WITH_CORRECTIONS at `245db63` (2026-09-11). One editorial
fix applied: acceptance matrix P2-C14 renumbered to P2-C13. Cursor may begin C0–C4.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` — Execute authorized; corrective code absent |
| **Reviewed base** | `8741774273e968824e4c09f1a7d6bb57729c0d43` on `origin/main` (PR #298) |
| **Implementation branch** | Create `feat/2026-09-11-codex-jsonl-p2-corrective` from current `origin/main` |
| **Push status** | Cursor must push the explicit feature refspec immediately after every commit |
| **PR** | Not opened; Execute does not authorize PR creation |
| **Ryan GATE** | None for this corrective slice; stop after pushed evidence for Kiro. Live P2 run, grant digest issuance, and PR remain separately Ryan-gated |
| **Track A ingest** | Do not run: this Execute explicitly prohibits `convmem index`, including session indexing |

---

## What to build

Add the missing **positive exact-resource P2 capability mode** and wire the reviewed
**P2-T2 twelve-part Gate 0** plus **P2-T3–T6 orchestration** into the existing
canary module and launcher. Prove the correction **hermetically** using
**production-shaped temporary paths** (the same eleven resource roles and lock layout
already used in P1 helpers), with **fake local providers** and **synthetic Kiro
sources** — not the frozen live session or live ConvMem followers.

**Why this exists:** merged P1 correctly denies production-rooted resources and the
launcher hard-refuses non-preflight execution. That is not a P1 defect; it is a missing
transfer seam. Without a positive P2 capability boundary, any grant naming the exact
live source and production followers would fail closed before mutation, and issuing a
digest would create false authority. PR #298 recorded that contradiction; Kiro
accepted the corrective direction (positive capability mode, full Gate 0, hermetic
orchestration proof, P1 denial preserved).

---

## Normative specification and order

Read these before the first edit:

1. `docs/plans/STATUS-codex-jsonl-production-integration.md`
2. `docs/inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-grant-packet.md`
3. `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` (especially §10 Gate 0)
4. `docs/plans/EXECUTION-codex-jsonl-production-canary.md` (P2-T2–T6, P2-A1–A14)
5. `docs/plans/VERIFY-codex-jsonl-production-canary.md` (P1 baseline — do not regress)

Execute in order:

### C0 — re-establish unchanged surfaces

1. Start `feat/2026-09-11-codex-jsonl-p2-corrective` from current `origin/main`.
2. Confirm byte-identical baseline for `watch.py`, normal `convmem.py` routing,
   `incremental_jsonl.py` default-off dispatch, and `incremental_jsonl_isolation.py`
   production denial (`IsolationBoundary.from_environment()` still fail-closed).
3. Re-run the existing focused P1 matrix before edits; stop on any regression.

**Gate:** any baseline hash mismatch or P1 regression stops the corrective pass.

### C1 — positive P2 capability mode (grant + boundary)

1. Extend the closed grant schema with an explicit **capability mode** field, e.g.
   `"capability_mode": "p2-exact-resource-v1"`. P1 grants omit the field or use
   `"p1-hermetic-v1"`; default validation behavior stays production-denying.
2. Add a **positive allowlist** constructor, e.g.
   `ProductionCanaryBoundary.from_p2_grant(grant)`, that:
   - requires `capability_mode == "p2-exact-resource-v1"`;
   - binds **only** the grant's exact source, metadata, overlay, evidence dir, and
     eleven named resource roles — no ambient production-root permission;
   - rejects any resource path not listed in the grant, any symlink escape, any
     world/group-writable authority artifact, and any alias of a non-granted path;
   - does **not** accept `forbidden_roots=()` or any caller-supplied empty override.
3. Keep `validate_grant()` and `ProductionCanaryBoundary.from_grant()` **unchanged**
   for P1: they continue to use `forbidden_roots or known_production_roots()`.
4. Add decode/validation rules so a P2-mode grant cannot mix P1 hermetic resource
   paths with live-shaped paths unless every path is explicitly named and digest-bound.

**Gate:** hermetic tests must show P1 still rejects production-shaped grants and P2
refuses every resource not named exactly in the grant.

### C2 — full twelve-part P2 Gate 0

Replace the current partial `gate0_preflight()` P1 subset with a complete P2 preflight
that implements Architecture §10 / Exec P2-T2 in one non-mutating call:

| # | Check |
|---|---|
| 1 | exact grant digest, revision, expiry, nonce, and clean allowed worktree |
| 2 | 61–109 accepted messages and exact baseline complete-prefix binding |
| 3 | source and metadata canonical, regular, read-only opened, unchanged |
| 4 | no processed entry, checkpoint/state, or Chroma rows for this source |
| 5 | persistent feature false and full rebuild false |
| 6 | watcher inactive by service probe, process census, and denied launcher; unknown/error fails |
| 7 | no competing indexer/writer; production locks free or attested to canary only |
| 8 | all grant paths exact; no symlink escape |
| 9 | named local models installed with exact digests (hermetic tests use fakes) |
| 10 | external credentials absent; non-loopback network denied |
| 11 | source-scoped rollback capsule readable and expected-empty for new source |
| 12 | fresh restic backup identifier recorded as evidence only — no restore |

Requirements:

- Split P1 hermetic Gate 0 from P2 Gate 0 explicitly (`gate0_preflight_p1` may remain
  as a thin wrapper if needed); the launcher `--preflight-only` path for P2-mode grants
  must call the full twelve-part preflight.
- Gate 0 emits a digested evidence event; any failure consumes no model calls and
  performs no mutation.
- Hermetic tests stub or inject: watcher census, writer/process census, model manifest,
  network self-test, restic identifier, and zero-adoption Chroma/processed probes.
- Live Gate 0 must not run in this grant: tests prove the function contract only.

### C3 — P2-T3–T6 orchestration (hermetic)

Implement orchestration stages behind the existing deep interface
(`canary_coordinator`, `canary_writer_scope`, fault runner, serving probe, nonce
receipt, rollback capsule). The launcher must expose explicit stages aligned with
Exec P2-T3–T6, for example:

| Stage | Behavior (hermetic proof) |
|---|---|
| **P2-T3** | initial two-chunk adoption on synthetic 61–68 message source; assert starts `[0, 50]`, call ceilings, durable prepared outputs before Chroma, checkpoint before processed, unrelated sentinels unchanged, zero-call unchanged replay |
| **P2-T4** | simulated pure append under grant envelope (test helper appends bytes without runner writing source); bind new stage receipt; prove chunk 0 reuse, frontier 50 only transformed, append ceilings, zero-call replay |
| **P2-T5** | five selected fault/replay observations using contained workers, serving probe, descendant termination, convergence or capsule restore, three stable reads after recovery |
| **P2-T6** | evidence freeze via `assemble_evidence` / `write_evidence`; disposition `converged`, `restored`, or `recovery_unproven`; stop without PR or live run |

Orchestration rules:

- Launcher requires P2 capability mode, matching CLI digest, unexpired nonce, reviewed
  code revision, successful full Gate 0, and nonce consumption before the first
  mutation stage.
- Remove the blanket `canary_p2_unauthorized` refusal for P2-mode grants that pass
  preflight; retain hard refusal for P1-mode grants attempting mutation and for P2 grants
  failing any gate.
- `--preflight-only` remains non-mutating for both modes.
- Hermetic tests use `python -I` workers, fake provider endpoints, and temporary
  production-shaped layouts from `tests/incremental_jsonl_canary_helpers.py`; extend
  helpers to build **P2-mode grants** whose resource paths mirror the packet's eleven
  roles under a temp `home/.local/share/convmem/...` tree.
- Do **not** open the frozen live source at
  `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/`.
- Do **not** read or write live production Chroma, processed, locks, or config.

### C4 — evidence and stop

1. Append a **P2 corrective** section to
   `docs/plans/VERIFY-codex-jsonl-production-canary.md` with exact commands,
   revisions, focused test counts, and explicit confirmation that no live source,
   production corpus, provider, watcher, config, indexing, live P2 run, PR, or
   activation occurred.
2. Run focused corrective tests plus existing P1 regressions; compileall and scoped
   pylint per repo gates.
3. Stop at a pushed exact tip for Kiro review. Do not open a PR.

---

## Integration point

Primary surfaces:

| File | Change |
|---|---|
| `incremental_jsonl_canary.py` | P2 capability mode, full Gate 0, orchestration stages, evidence assembly |
| `scripts/run-jsonl-production-canary.py` | Stage dispatch; P2 preflight + orchestration entry; retain `--preflight-only` |
| `tests/incremental_jsonl_canary_helpers.py` | P2-mode grant builder with production-shaped temp paths |
| `tests/test_incremental_jsonl_canary_p2_corrective.py` | New focused hermetic matrix (create) |
| `tests/incremental_jsonl_canary_worker.py` | Extend only if subprocess stage proofs require it |
| `docs/plans/VERIFY-codex-jsonl-production-canary.md` | Append corrective evidence |

Do **not** modify `incremental_jsonl_isolation.py`, `watch.py`, `ingest.py` routing,
`convmem.py`, or live config.

Minimal insertion pattern for positive mode:

```python
# incremental_jsonl_canary.py — illustrative only
P2_CAPABILITY_MODE = "p2-exact-resource-v1"

@classmethod
def from_p2_grant(cls, grant: CanaryGrant) -> "ProductionCanaryBoundary":
    if grant.capability_mode != P2_CAPABILITY_MODE:
        raise CanaryRefused("canary_mode", "not a P2 exact-resource grant")
    allowed = _exact_resource_allowlist(grant)  # positive binding only
    ...
```

---

## What NOT to build

- Live P2 canary execution against the frozen dedicated session or production followers
- Executable grant JSON, nonce consumption against live paths, or grant digest issuance
- `--preflight-only` against live production resources
- Access to live Chroma, processed, export, dedupe, locks, attestations, or census
- `convmem index`, watcher start/stop, config edits under `~/.config/convmem/`
- Provider calls, model pulls, paid selection, or non-loopback network (even in dev)
- Weakening P1 production denial, empty `forbidden_roots` bypass, or
  `IsolationBoundary` production acceptance
- PR creation, merge, activation, or inference that corrective merge authorizes live P2
- Repo-wide pytest unless explicitly needed for a scoped gate (default: focused matrix)

---

## Test expectations

Add `tests/test_incremental_jsonl_canary_p2_corrective.py` (name may vary) covering at
minimum:

1. **P2-C1:** P1 `validate_grant` / `from_grant` still reject production-shaped grants.
2. **P2-C2:** P2-mode grant accepts only its eleven explicitly named resource roles under
   a temp production-shaped tree; rejects an extra path and a missing role.
3. **P2-C3:** empty-forbidden-root override cannot enable production paths.
4. **P2-C4:** full Gate 0 passes hermetically with injected census/model/network/restic
   stubs; each of the twelve checks fails closed when stubbed to bad state.
5. **P2-C5:** launcher refuses mutation for P1 grants and for P2 grants failing Gate 0.
6. **P2-C6:** P2-T3 hermetic initial adoption — two chunks, ceilings, zero-call replay.
7. **P2-C7:** P2-T4 hermetic append — chunk 0 reuse, frontier 50 only, replay zero calls.
8. **P2-C8:** P2-T5 five fault selectors converge or restore; serving probe stable reads.
9. **P2-C9:** P2-T6 evidence bundle contains grant digest, Gate 0, timelines, disposition.
10. **P2-C10:** `prove_cli_watcher_unreachable()` and baseline module hashes unchanged.
11. **P2-C11:** unrelated-source sentinels unchanged across adoption, append, and faults.
12. **P2-C12:** nonce receipt enforces one resumable run; completed nonce cannot restart.

Use `tmp_path`, `-I` workers, and fake providers; never depend on live corpus state.

---

## Acceptance criteria

| ID | Condition |
|---|---|
| P2-C1 | P1 production-root denial unchanged |
| P2-C2 | Positive P2 mode binds only grant-listed exact resources |
| P2-C3 | No forbidden-root bypass or ambient production permission |
| P2-C4 | All twelve Gate 0 checks implemented and hermetically proven |
| P2-C5 | Launcher orchestrates P2-T3–T6 behind successful Gate 0 + nonce |
| P2-C6 | Hermetic initial adoption matches two-chunk profile and ceilings |
| P2-C7 | Hermetic append reuses chunk 0 and transforms frontier only |
| P2-C8 | Five fault cases converge or exact-restore within timeout |
| P2-C9 | Evidence freeze is self-contained and marks `hermetic: true` |
| P2-C10 | Normal CLI, watcher, default-off ingest unchanged |
| P2-C11 | Unrelated sentinels and persistent false/false preserved in tests |
| P2-C12 | No live source, production data, provider, network, config, indexing, live P2, PR, or activation |
| P2-C13 | Existing P1 focused matrix still PASS |

Also require: ruff/pylint clean on touched files; `git diff --check` clean.

---

## Branch convention

```
feat/2026-09-11-codex-jsonl-p2-corrective
```

Push immediately after each commit:

```bash
git push -u origin "feat/2026-09-11-codex-jsonl-p2-corrective:refs/heads/feat/2026-09-11-codex-jsonl-p2-corrective"
```

Open PR only when Ryan separately asks. Squash is fine unless PR body says otherwise.

---

## Related files

| What | Path |
|---|---|
| Blocked P2 packet (Kiro PASS) | `docs/inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-grant-packet.md` |
| PR #298 merge reading | squash `8741774` |
| Architecture Gate 0 | `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` §10 |
| P2 execution stages | `docs/plans/EXECUTION-codex-jsonl-production-canary.md` §4 |
| P1 evidence (baseline) | `docs/plans/VERIFY-codex-jsonl-production-canary.md` |
| Arc STATUS | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Canary module | `incremental_jsonl_canary.py` |
| Launcher | `scripts/run-jsonl-production-canary.py` |
| P1 helpers | `tests/incremental_jsonl_canary_helpers.py` |

---

## Leaving / picking up checklist

**Codex (leaving):**

- [x] This handoff committed on pushed branch
- [x] `LATEST.md` bullet at top with link and `AUTHORIZED (not yet implemented)`
- [x] `STATUS-codex-jsonl-production-integration.md` Update Log line

**Cursor (picking up):**

- [ ] Read this file and the P2 grant packet before first edit
- [ ] `convmem work start feat 2026-09-11-codex-jsonl-p2-corrective` from `origin/main`
- [ ] State Goal / role / system / next action from STATUS before coding

---

## TL;DR

- **Arc Codex:** Ryan authorized a hermetic corrective pass for the missing P2 transfer
  seam after Kiro PASS on PR #298's blocked packet.
- **Build:** positive exact-resource P2 capability mode, full twelve-part Gate 0, and
  P2-T3–T6 orchestration proved under production-shaped temporary paths.
- **Preserve:** P1 production denial, default-off CLI/watcher/ingest, unchanged
  `IsolationBoundary`.
- **Stop:** pushed evidence for Kiro review — no live P2, no grant digest, no PR.
