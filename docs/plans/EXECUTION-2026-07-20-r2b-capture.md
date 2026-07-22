# Execution Plan — R2b authorization, capture, and corpus package

```
Planning Status

Phase:        Architecture docs replacement
Characters:   Task Decomposer, Scope Guardian
Functions:    Planner
Lanes:        Codex (this docs PR); Cursor (later implementation); Copilot + Kiro (review); Ryan (merge/grant)
Authority:    R2b implementation and live capture are not authorized by this plan
```

**Source:** Ryan direction, revised after the seven-finding architecture
assessment on 2026-07-20

**Architecture:** [`ARCHITECTURE-r2b-capture-auth.md`](ARCHITECTURE-r2b-capture-auth.md)

**VERIFY companion:** [`VERIFY-r2b-capture.md`](VERIFY-r2b-capture.md)

**Parent runbook:** [`EXECUTION-embedding-model-eval.md`](EXECUTION-embedding-model-eval.md)

**Supersedes:** [PR #64](https://github.com/alanmz-crypto/convmem/pull/64) — do not merge #64

**Goal:** Introduce an honest phase-scoped authorization boundary for one
content-bound, deterministic, write-once R2b capture, then stop before
B-Accept. The work proceeds through separate architecture, implementation,
packet-acceptance, grant, execution, and verification gates.

---

## Settled architecture contract

- **Option A:** real capture requires `authorization_phase: "r2b"` and exactly
  `operations: ["capture"]`; placeholder/pre-image Option B is rejected.
- **Completion:** expanded `corpus_package_manifest.json` is the last atomic
  completion marker. It hashes required `capture_report.json` and every other
  non-marker artifact and binds the exact inventory.
- **Source identity:** approved export/processed state plus a canonical Chroma
  collection/ID/document/superseded digest; trusted code recomputes it before
  capability mint, at write authorization, and before marker publication.
- **Controls:** `capture_id=run_id`, canonical overlap, spot `n=20`, one
  attempt.
- **Write authority:** `bind_r2b_capture` -> opaque `_R2bCapability` ->
  `run_capture` -> materialize before mkdir. Plain `bind_capture` refuses R2b.
- **Containment:** safe `run_id`; exact auth/capture templates; lexical and
  resolved path equality; no symlink components; capture directory absent.
- **Failure:** no marker, quarantine, no reuse; retry means a new run/grant.

The architecture document owns the detailed schema, marker, snapshot, path,
and failure contracts. This execution plan must not weaken them by omission.

---

## Tasks and gates

| ID | Deliverable | Scope | Depends on | Gate / owner |
|----|-------------|-------|------------|--------------|
| T1 | Architecture replacement: architecture + filled VERIFY + this execution plan + LATEST | Docs only | — | Ryan reviews docs PR; **Supersedes #64** |
| T2 | Implement R2b schema, trusted canonical snapshot, capability chain, fixed controls, last marker, and hermetic tests | Code/tests only; no live capture | T1 merge | Cursor implementation PR |
| T3 | Exact-tip safety/isolation and architecture-fidelity review | Review only | T2 PR tip | Copilot + Kiro on same SHA; Ryan merge + tree proof |
| T4 | Run `convmem doctor`; require `restic_gate: PASS`; trusted fresh source recompute and filled packet draft | Read-only sources + auth draft | T3 merge | Cursor; timestamp/source gates |
| T5 | Ryan packet ACCEPT; materialize manifest, sidecar, hashes, exact argv, revision; Ryan `ACCEPT AND GRANT` | Auth files only | T4 | Ryan two-stage HITL |
| T6 | Execute exactly one capture into an absent canonical `capture_dir`; retain full evidence | One eval-root capture only | T5 | Named operator under exact grant |
| T7 | Mechanical VERIFY then Kiro sign-off; Ryan arc GATE | Read-only verification | T6 | [`VERIFY-r2b-capture.md`](VERIFY-r2b-capture.md) |
| T8 | Stop for B-Accept | Explicitly out of scope | T7 | New architecture/grant required |

T1 is the only task authorized by this docs brief. T2–T8 require their own
normal lane and gates.

---

## Acceptance and authority sequence

```text
architecture docs PR + Ryan merge
  -> implementation PR at exact tip
  -> Copilot + Kiro same-tip verdicts
  -> Ryan implementation merge + tree proof
  -> restic_gate: PASS
  -> trusted snapshot + filled draft packet
  -> Ryan ACCEPT (snapshot <=1h, timezone-aware, identity unchanged)
  -> manifest/sidecar/exact command materialized
  -> Ryan ACCEPT AND GRANT
  -> one attempt into absent capture_dir
  -> mechanical VERIFY + Kiro verdict
  -> Ryan GATE
  -> STOP before B-Accept
```

A verbal `GRANT: yes` without the filled approved packet is not authority.
Architecture approval, packet ACCEPT, and `ACCEPT AND GRANT` are not
interchangeable.

---

## Later packet requirements

The T4/T5 packet must bind at least:

- exact manifest path and file SHA;
- canonical approved-body digest and matching adjacent sidecar;
- exact implementation revision and Gate 1 harness pin;
- safe `run_id` and canonical auth/capture path templates;
- exact absolute `export`, `processed`, `capture_dir`, and `chroma_dir` strings;
- full trusted `source_snapshot`, including canonical Chroma content digest and
  timezone-aware timestamp;
- exact fixed controls and exact argv vector;
- exact prohibited list from architecture; and
- evidence that `capture_dir` is absent and bound paths have no symlink
  components.

`corpus_package_sha256`, `unit_corpus_fingerprint`, and Gate 2 outputs are not
pre-capture authorization fields.

---

## Future execution command

The filled packet supplies literal values. While the CLI flag remains, the only
allowed command shape is:

```bash
cd /home/lauer/Projects/convmem
python3 scripts/eval_corpus_capture.py \
  --run-manifest <AUTH_ROOT>/<run_id>/capture.json \
  --export <approved absolute export path> \
  --processed <approved absolute processed path> \
  --capture-dir <EVAL_ROOT>/<run_id>/capture \
  --chroma-dir <approved absolute Chroma path> \
  --max-retries 1
```

No live command is authorized or executable from this docs PR. The later grant
must quote a fully filled argv vector; placeholders are not authority.

---

## Execute-phase evidence

- `restic_gate: PASS` before snapshot computation and before eval-root write
- exact implementation SHA, cwd, argv JSON, start/finish timestamps, exit,
  stdout, and stderr
- approved packet/manifest/body/sidecar hashes
- trusted snapshot recomputations and staleness calculations
- capability/materialization-before-mkdir proof
- whole-directory inventory and SHA-256 for every artifact
- completion-marker validation and write-order proof
- explicit failure/quarantine evidence if no marker is produced
- independent Kiro verdict on the same evidence and implementation revision

`CAPTURE_COMPLETE` normally exits `0`; a structurally complete `UNRESOLVED`
capture may retain exit `1`. FAILED/drift/exception is nonzero and has no
marker. VERIFY records both exit semantics and marker authority.

---

## Failure and retry policy

| Point of failure | Action |
|------------------|--------|
| Before capture directory creation | Refuse; correct only through a fresh packet/grant if approved inputs change |
| After directory creation, before marker | Preserve and quarantine partial directory; no cleanup or resume |
| Source drift | Record `post_capture_source_drift`; no marker; quarantine |
| Overlap/dedup FAILED | Preserve report/evidence; no marker; quarantine |
| UNRESOLVED | Valid marker may prove structural completion; Ryan decides later acceptance, never automatic retry |

Every retry requires a new `run_id`, absent capture directory, trusted snapshot,
packet ACCEPT, and `ACCEPT AND GRANT`. Cleanup is separately prohibited.

---

## Out of scope

- Live capture during the architecture or implementation PR
- B-Accept design/execution, adjudication, C0+, R3–R8, Gate 2
- R2a changes, shadow-config regeneration, model pull/probe/execution
- Build, compare, promotion, cleanup, or service mutation
- Overwrite or reuse of any prior R2a/R2b directory
- Treating #64 as mergeable after this replacement exists

## Current entry and close conditions

- **Current entry:** T1 docs replacement only.
- **Architecture close:** Ryan merges this docs PR; #64 may then be closed as
  superseded.
- **Capture close:** T2–T7 complete with exact evidence and Ryan GATE.
- **Hard stop:** merge of any planning or implementation PR does not grant live
  R2b execution.
