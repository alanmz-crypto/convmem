# Verify Plan — Shadow Ledger Phase 0

```text
Planning Status

Phase:        Verify (shadow-ledger-phase0)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro/Ryan-named lane (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Stub status:** Execute in progress on PR #122. Mechanical focused tests exist;
full V0–V8 row fill awaits final Execute tip + independent sign-off.

**Subject / tip:** `feat/2026-07-24-shadow-ledger-phase0` — T4 disposable projector landed (tip moves; pin after commit)

**PR(s):** [#122](https://github.com/alanmz-crypto/convmem/pull/122)

**Execute progress (Cursor mechanical):**
- T1–T5 modules landed (contract, sink, durability tests, replay projector, inventory helpers).
- Writer coverage: production mutators migrated to `open_chroma_for_write` / `chroma_write_session`; bypass list **0**.
- T4: `run_disposable_replay` projects into marked temp Chroma with `mutation_sink=None`, stub/live modes, checkpoint-under-root, two-level compare.
- Focused suite: `pytest -q tests/test_shadow_ledger_phase0_t*.py tests/test_shadow_writer_coverage_scan.py` (run at tip).
- Lock-timeout doctor WARN threshold **N = 3** (`LOCK_TIMEOUT_WARN_THRESHOLD_N` in `shadow_sink.py`).
- **Production activation still unauthorized.**

**Architecture:**

[`ARCHITECTURE-shadow-ledger-phase0.md`](ARCHITECTURE-shadow-ledger-phase0.md)

**Execution:**

[`EXECUTION-shadow-ledger-phase0.md`](EXECUTION-shadow-ledger-phase0.md)

**Goal:** Prove the approved Phase 0 implementation captures and replays only
post-activation `knowledge_units` deltas, preserves Chroma authority, fails
safely, and never writes to a production replay target.

## Finding — factory routing migration (2026-07-24)

**Verdict for V3b / V3d at this tip: PASS (code-path).** Prior FAIL at `5c0ddb8` is closed by migrating production writers.

**Proved (code-path + hermetic):**
- Production call sites of `open_chroma_for_write`: **10**; plus **4** `chroma_write_session` sites that wrap the factory (see [`SHADOW-WRITER-COVERAGE-INVENTORY.md`](SHADOW-WRITER-COVERAGE-INVENTORY.md)).
- Sites classified `must_use_factory` that still construct `ChromaStore(...)` directly: **0**.
- Remaining direct ctors are allowlisted read-only / helper / factory-internal.
- Hermetic control retained: direct `ChromaStore(dir)` with eligible cfg ⇒ no sink / no ledger (documents why factory remains mandatory).
- Positive control: factory with eligible cfg ⇒ sink attaches and one event is written.

**Not proved (do not fog):** a live production ingest/observe with `enabled=true` writing (or missing) a shadow line — live activation is forbidden for this verification slice.

**Report format:** For every row, record **PASS / FAIL / SKIP** plus one line of
tip-specific evidence. An applicable SHA mismatch is **FAIL**, never SKIP.

**Flow:** V0–V8 mechanical checks → mechanical PASS/FAIL → independent written
sign-off → Ryan GATE. The verifier performs no cleanup or correction.

## Human consequence (fill after Execute)

**Consequence:** `<what Ryan gains or must still avoid if this arc is accepted>`

### 5 Ws

| | |
|---|---|
| **Who** | Cursor implements; independent reviewer verifies; Ryan accepts or rejects |
| **What** | Disabled-by-default, non-authoritative shadow delta capture and disposable replay |
| **When** | `<final Execute tip and verification time>` |
| **Why** | Prove capture/replay mechanics before any activation, migration, or cutover decision |
| **How** | Mutation-boundary coverage, durable append, isolated replay, comparison, and readiness evidence |

**TL;DR:** `<filled result and largest residual>`

**Honest limits / caveats:** Phase 0 cannot prove historic-corpus rebuild,
production activation safety over time, canonical-schema fitness, backup
fitness, migration readiness, or authority cutover.

### Merge reading

- Architecture:
  [`ARCHITECTURE-shadow-ledger-phase0.md`](ARCHITECTURE-shadow-ledger-phase0.md)
- Execution:
  [`EXECUTION-shadow-ledger-phase0.md`](EXECUTION-shadow-ledger-phase0.md)
- This VERIFY: `docs/plans/VERIFY-shadow-ledger-phase0.md`
- Active handoff: [`../inter-model/LATEST.md`](../inter-model/LATEST.md)
  (`<named Shadow Ledger Phase 0 bullet after Execute>`)
- Execute PR: `<PR link/number>`

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Optional `ChromaStore` unit-mutation observer and one authoritative write-store factory | Production read-path changes or authority transfer |
| Disabled config, activation validation, and read-only baseline | Live config edit, live activation, or production observation period |
| Durable shadow writer, validator, sidecar, and unit-writer coverage | `conversation_summaries` or decision-log authority |
| Fail-closed corruption and visible post-Chroma gap semantics | Auto-repair, auto-heal, tail truncation, or quarantine-and-continue |
| Disposable temp-root replay and touched-ID comparison | Historic bootstrap, migration, live rewrite, or full rebuild claim |
| Runtime-stamped inventory and readiness report | Restic/restore changes, Neutral/Office, ranking/retrieval work |

## V0 — Preconditions and exact subject

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git show --stat --oneline HEAD
convmem doctor
convmem brief --stdout-only
```

### External review evidence input

Copy this block from Execute; do not infer applicability during Verify.

| Field | Value |
|-------|-------|
| `gate_applicability` | `required` |
| `reason` | Production mutation boundary, durability, and replay isolation changed |
| `subject_tip_sha` | `<sha>` |
| `reviewed_sha` | `<sha>` |
| `result` | `clean` \| `findings` \| `unreachable` |
| `finding_disposition` | Per finding: `fixed` \| `ryan_accepted` \| `none` |
| `authority_reference` | `<PR-native evidence / Ryan acceptance>` |

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V0a | Subject tip resolves to the exact commit being verified | PENDING |
| V0b | Architecture and Execution Plan approvals are cited; Execute authority is explicit | PENDING |
| V0c | The pre-edit runtime stamp re-measured counts instead of using audit snapshot constants | PENDING |
| V0d | Final external review evidence names the same subject tip | PENDING |
| V0e | Every external finding is fixed or Ryan-accepted | PENDING |
| V0f | Worktree is clean except for explicitly documented evidence updates | PENDING |

## V1 — Diff and authority boundary

```bash
git diff --name-status <approved-execute-base>..HEAD
git diff --check <approved-execute-base>..HEAD
git diff <approved-execute-base>..HEAD -- \
  docs/audit-ledger-first \
  docs/plans/ARCHITECTURE-shadow-ledger-phase0.md
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V1a | Every changed path maps to T1–T5, tests, or approved VERIFY evidence | PENDING |
| V1b | Architecture and audit-baseline bodies are unchanged | PENDING |
| V1c | No live config, production data root, Restic/restore, Neutral/Office, ranking, or authority file changed | PENDING |
| V1d | No git hook or always-on production hook was added | PENDING |
| V1e | `git diff --check` passes | PENDING |

## V2 — Disabled configuration and activation baseline

```bash
<focused activation/config/baseline test command from Execute>
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V2a | Missing `[shadow_ledger]` and `enabled = false` both inject no sink | PENDING |
| V2b | Example configuration is disabled and no live config was edited | PENDING |
| V2c | `enabled = true` without a complete matching manifest refuses injection visibly | PENDING |
| V2d | Canonical root comparison rejects mismatches and aliases | PENDING |
| V2e | Read, verify, evaluation, restore-drill, and replay stores always receive no sink | PENDING |
| V2f | Baseline fields match Architecture and are runtime-derived, not hardcoded | PENDING |
| V2g | Baseline temp-write, file `fsync`, atomic rename, and parent-directory `fsync` are tested | PENDING |
| V2h | Configured and observed embedding identities remain separate; unknown is not inferred | PENDING |

## V3 — Envelope, mutation sink, and complete writer coverage

```bash
pytest -q tests/test_shadow_writer_coverage_scan.py tests/test_shadow_ledger_phase0_t2.py
# inventory: docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json
rg -n 'open_chroma_for_write\(|ChromaStore\(' --glob '*.py' -g '!tests/**' .
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V3a | Observer defaults to `None`; `ChromaStore` does not load global activation config | **PASS** — `mutation_sink=None` default; no `load_config` in `chroma_store.py` |
| V3b | One authoritative production write-store factory is the only sink injection boundary | **PASS** — **10** `open_chroma_for_write` + **4** `chroma_write_session` prod sites; sink only attached in factory |
| V3c | All five unit-mutating methods emit or explicitly exclude confirmed per-entity events | **PASS** — method-level (`test_unit_mutating_methods_emit_or_exclude` + T2 emit tests) |
| V3d | Production mutating callers route through the factory; allowlisted direct clients are isolated | **PASS** — **0** bypass sites; allowlisted direct ctors = read/helper/internal only |
| V3e | Static scan, mutator enumeration test, and caller integration tests all exist; grep is not the sole proof | **PASS** — inventory + scan lock routing; hermetic bypass control + factory positive control |
| V3f | Failed Chroma mutation emits no event; successful mutation creates the event context before Chroma and appends after success | **PASS** (hermetic) — event_id before upsert; BoomSink / success path in T2 |
| V3g | Bulk source operations emit one event per confirmed entity, including partial completion | **PASS** (hermetic) — supersede/delete per-entity emit in T2 |
| V3h | Summary mutations emit no unit event | **PASS** — `test_summaries_not_shadowed` |
| V3i | Envelope version, closed vocabulary, tombstones, hashes, and no-raw-vector rule match Architecture | **PASS** (partial hermetic) — schema v1 ops + hashes in sink |
| V3j | Sink failure never changes a successful Chroma return result | **PASS** — `test_sink_failure_preserves_chroma_success` |

## V4 — Durability, concurrency, corruption, and failure visibility

```bash
<focused writer/durability/corruption test command from Execute>
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V4a | Shadow lock is acquired only after Chroma success and no Chroma lock is acquired while holding it | PENDING |
| V4b | Lock acquisition has a 250 ms budget; timeout leaves Chroma successful and records degradation | PENDING |
| V4c | Append uses one encoded-byte write, flush, file `fsync`, and first-create directory `fsync` | PENDING |
| V4d | First-created shadow and health files are mode `0600` | PENDING |
| V4e | `fsync` latency above 500 ms is measured/degraded without unsafe interruption | PENDING |
| V4f | Concurrent writers serialize sequence allocation and produce complete parseable lines | PENDING |
| V4g | Uncertain acknowledgement retry reuses `event_id`; duplicates are visible and idempotent | PENDING |
| V4h | Truncated tail and invalid middle line both refuse append and make readiness FAIL | PENDING |
| V4i | Validation/projection stops at first corruption and checkpoint never advances past it | PENDING |
| V4j | Post-Chroma/pre-shadow process death is detected by baseline/touched-ID comparison without auto-heal claim | PENDING |
| V4k | Health/doctor distinguish disabled, healthy, degraded, corrupt, and baseline mismatch honestly | PENDING |

## V5 — Disposable replay isolation and equality

```bash
pytest -q tests/test_shadow_ledger_phase0_t4.py
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V5a | Projector accepts only a newly created marked temporary root | **PASS** — `prepare_replay_root` writes `.convmem_shadow_replay_ok` |
| V5b | Production root, parent, symlink/canonical alias, and nonempty unmarked target fail before writable open | **PASS** — `test_refuse_*` (prod/parent/symlink/unmarked) |
| V5c | Projector forces `mutation_sink=None` and cannot recurse into the shadow writer | **PASS** — `open_replay_store` + `test_no_shadow_recursion_even_when_cfg_eligible` |
| V5d | Checkpoint lives under the disposable root and advances only after successful projection | **PASS** — checkpoint under root; corruption stops without advancing past bad line |
| V5e | Replay reduces valid events in order to final touched-ID state | **PASS** — `reduce_final_states` + ordered `project_event` in `run_disposable_replay` |
| V5f | Duplicate event IDs apply once and are counted; distinct IDs retain sequence history | **PASS** — duplicate counted; second distinct id projects |
| V5g | Stub mode is deterministic, offline, and uses recorded dimensions | **PASS** — `stub_embedding` + stub replay test (no network) |
| V5h | Live mode is explicit/local/disposable and cannot upgrade unknown provenance to PASS | **PASS** — missing host/model and unreachable raise `LiveEmbedError` (no stub fallback); UNVERIFIABLE blocks projection PASS |
| V5i | State and projection equality are reported separately; raw vectors are excluded | **PASS** — `equality_flags` / `ReplayResult.state_equal` vs `projection_equal` |
| V5j | Exact document drift fails projection equality and unknown identity is `UNVERIFIABLE` | **PASS** — `test_document_drift_*` + `test_unverifiable_*` |
| V5k | Report includes all Architecture comparison categories and scopes claims to post-activation touched IDs | **PASS** — `ARCHITECTURE_CATEGORIES` + `touched_ids` scoped compare |

## V6 — Inventory and readiness semantics

```bash
<focused inventory/readiness test command from Execute>
<read-only inventory command against the approved isolated or production-read target>
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V6a | Inventory records UTC time, code revision, resolved inputs, hashes, root identity, live counts, and rule version | PENDING |
| V6b | Repeated run over identical inputs is deterministic | PENDING |
| V6c | Counts are runtime-derived; audit snapshot values are absent from implementation constants | PENDING |
| V6d | Default output exposes counts/stable IDs/categories, not documents, metadata payloads, secrets, or embeddings | PENDING |
| V6e | Candidate classes are deterministic/local and ambiguous rows remain human-gated | PENDING |
| V6f | Inventory performs no rewrite, ingest, delete, authority transfer, or LLM/API call | PENDING |
| V6g | Machine-readable and human reports agree on PASS/PARTIAL/FAIL | PENDING |
| V6h | PASS is labeled `delta capture` and makes no historic rebuild, backup, migration, cutover, or activation claim | PENDING |

## V7 — Focused/full regression and non-mutation evidence

```bash
<all focused shadow-ledger test commands from Execute>
<full repository test command from Execute>
convmem doctor
convmem doctor --v1
git diff --check <approved-execute-base>..HEAD
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V7a | All focused Shadow Ledger Phase 0 tests pass | PENDING |
| V7b | Full existing regression suite passes or every pre-existing failure is proved against the base | PENDING |
| V7c | Doctor reports disabled production state honestly and no false readiness PASS | PENDING |
| V7d | Test roots and artifacts are temporary/marked and cleaned without touching production | PENDING |
| V7e | No network/provider call occurs in hermetic stub tests | PENDING |
| V7f | Repository diff and runtime checks show no live Chroma, live config, JSONL authority, decision-log, Restic, or restore mutation | PENDING |

## V8 — Independent safety/sign-off gate

The independent reviewer must inspect the final subject tip, not an earlier
commit, and must specifically examine:

- production-root and alias refusal before writable client construction;
- observer default-off and non-production store isolation;
- Chroma-success/shadow-failure result preservation;
- corruption stop/checkpoint behavior;
- payload/secret exposure in sidecar, inventory, and readiness output;
- the truthfulness of delta-only and unknown-provenance claims.

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V8a | Targeted external technical review matches final subject tip and findings are disposed | PENDING |
| V8b | Independent reviewer writes PASS or FAIL naming the final tip SHA and residual risks | PENDING |
| V8c | Independent review does not implement fixes or silently broaden scope | PENDING |
| V8d | Ryan records the final HITL GATE outcome | PENDING |

## Evidence log (fill after Execute)

```text
VERIFY-shadow-ledger-phase0 — tip <sha> — runner <lane> — <ISO-8601>
V0 Preconditions: PENDING
V1 Diff/authority: PENDING
V2 Activation/config: PENDING
V3 Writer coverage: FAIL (V3b/V3d/V3e) — factory bypass proved
V4 Durability/corruption: PENDING
V5 Replay/equality: PENDING
V6 Inventory/readiness: PENDING
V7 Regression/non-mutation: PENDING
V8 Independent sign-off: PENDING
Mechanical: PENDING
Sign-off: PENDING
Ryan GATE: PENDING
```

## Stub stop

This artifact predeclares verification only. It does not authorize Execute,
production activation, migration, cutover, backup wiring, restore-order change,
or a change in Chroma authority.
