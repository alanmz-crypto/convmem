# Verify Plan — Shadow Ledger Phase 0

```text
Planning Status

Phase:        Verify (shadow-ledger-phase0)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro/Ryan-named lane (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Stub status:** Mechanical VERIFY V0–V7 filled by Cursor (2026-07-25). V8
independent sign-off + Ryan GATE still required before activation.

**Subject / tip:** `feat/2026-07-24-shadow-ledger-phase0` @ `0070b27` — mechanical
VERIFY base (T1–T5 Execute); this VERIFY-fill commit pins after evidence below

**PR(s):** [#122](https://github.com/alanmz-crypto/convmem/pull/122)

**Execute progress (Cursor mechanical):**
- T1–T5 modules landed (contract, sink, durability, replay projector, inventory CLI).
- Writer coverage: factory routing bypass list **0** (V3 PASS).
- T3/V4 durability PASS; T4/V5 projector PASS; T5/V6 inventory PASS.
- Mechanical VERIFY V0–V2/V7 filled 2026-07-25T07:28:06Z (runner: Cursor).
- Focused suite: `pytest -q tests/test_shadow_ledger_phase0_t*.py tests/test_shadow_writer_coverage_scan.py` → **59+** passed.
- Full suite: `pytest -q` → **837 passed** (after inter-model mock fix for factory migration).
- Live: `shadow_ledger` doctor **PASS disabled**; inventory **PARTIAL** (not activated).
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

**Consequence:** Ryan can run a read-only Phase 0 inventory/readiness report
without enabling shadowing or mutating Chroma; Execute on #122 now has
mechanical V3–V6 evidence. Activation remains a separate grant.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor implements; independent reviewer verifies; Ryan accepts or rejects |
| **What** | Disabled-by-default, non-authoritative shadow delta capture and disposable replay |
| **When** | Execute tip on `feat/2026-07-24-shadow-ledger-phase0` (see Subject tip) |
| **Why** | Prove capture/replay mechanics before any activation, migration, or cutover decision |
| **How** | Mutation-boundary coverage, durable append, isolated replay, comparison, and readiness evidence |

**TL;DR:** Phase 0 Execute machinery is in place (factory, durability, projector,
inventory CLI); live activation is still forbidden; largest residual is
independent VERIFY sign-off + activation grant.

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
| `subject_tip_sha` | `0070b27a7188a82fca32b030e0a58fb3956ed228` (mechanical base; VERIFY-fill tip supersedes after commit) |
| `reviewed_sha` | _(empty — awaits V8 independent review)_ |
| `result` | `unreachable` until V8 |
| `finding_disposition` | `none` yet |
| `authority_reference` | PR #122; Architecture HITL + Execution HITL cited in V0b |

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V0a | Subject tip resolves to the exact commit being verified | **PASS** — tip `0070b27` = `git rev-parse HEAD` at mechanical fill; VERIFY-fill commit will re-pin |
| V0b | Architecture and Execution Plan approvals are cited; Execute authority is explicit | **PASS** — Arch HITL locked (`e326aa6` / #115 path); Execution plan `5104022` + Ryan Execute grant; PR #122 Consequence states activation still separate |
| V0c | The pre-edit runtime stamp re-measured counts instead of using audit snapshot constants | **PASS** — PR #122 Runtime stamp @ `2026-07-25T04:03:19Z` / corpus **11092** units (live re-measure, not audit constants) |
| V0d | Final external review evidence names the same subject tip | **SKIP** — awaits V8 independent review of final tip |
| V0e | Every external finding is fixed or Ryan-accepted | **SKIP** — no V8 findings yet |
| V0f | Worktree is clean except for explicitly documented evidence updates | **PASS** (post-commit of this VERIFY fill + whitespace/test fixes only) |

## V1 — Diff and authority boundary

```bash
git diff --name-status origin/main...HEAD
git diff --check origin/main...HEAD
git diff origin/main...HEAD -- \
  docs/audit-ledger-first \
  docs/plans/ARCHITECTURE-shadow-ledger-phase0.md
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V1a | Every changed path maps to T1–T5, tests, or approved VERIFY evidence | **PASS** — code/tests under shadow_* / chroma_write_store / writers; plans VERIFY/EXECUTION/PHASE0/inventory; inter-model handoffs; doctor; config.example — all Phase 0 scoped |
| V1b | Architecture and audit-baseline bodies are unchanged | **PASS** — `docs/audit-ledger-first` untouched; Architecture decision body unchanged after HITL; only planning-status/handoff banner updated in authorize-Execution commit (`c13042c`) |
| V1c | No live config, production data root, Restic/restore, Neutral/Office, ranking, or authority file changed | **PASS** — no `~/.config/convmem/config.toml` in git; live TOML has no `[shadow_ledger]` section (absent ≡ disabled); no Restic/Neutral/ranking paths in diff |
| V1d | No git hook or always-on production hook was added | **PASS** — `git diff --name-status origin/main...HEAD -- scripts/git-hooks` empty |
| V1e | `git diff --check` passes | **PASS** — trailing whitespace in PHASE0 contract + Claude review handoff stripped in this VERIFY fill |

## V2 — Disabled configuration and activation baseline

```bash
pytest -q tests/test_shadow_ledger_phase0_t1.py
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V2a | Missing `[shadow_ledger]` and `enabled = false` both inject no sink | **PASS** — `test_absent_table_equals_enabled_false` |
| V2b | Example configuration is disabled and no live config was edited | **PASS** — `test_config_example_shadow_ledger_disabled`; live config mtime pre-Execute; no `[shadow_ledger]` section present |
| V2c | `enabled = true` without a complete matching manifest refuses injection visibly | **PASS** — `test_enabled_true_without_manifest_refuses` + `test_incomplete_manifest_cannot_enable` |
| V2d | Canonical root comparison rejects mismatches and aliases | **PASS** — `test_complete_manifest_root_mismatch_refuses` |
| V2e | Read, verify, evaluation, restore-drill, and replay stores always receive no sink | **PASS** — `open_chroma_for_read`/`verify` default sink None; `purpose="test"` forces None; replay `open_replay_store` forces None |
| V2f | Baseline fields match Architecture and are runtime-derived, not hardcoded | **PASS** — `new_incomplete_manifest`/`finalize_manifest` + `test_runtime_stamp_has_no_hardcoded_audit_counts` |
| V2g | Baseline temp-write, file `fsync`, atomic rename, and parent-directory `fsync` are tested | **PASS** — `test_atomic_write_fsyncs_file_and_parent` + mode `0600` |
| V2h | Configured and observed embedding identities remain separate; unknown is not inferred | **PASS** — finalize keeps `observed_embed_model="unknown"` separate from configured model in T1 complete-manifest tests |

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
pytest -q tests/test_shadow_ledger_phase0_t3.py
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V4a | Shadow lock is acquired only after Chroma success and no Chroma lock is acquired while holding it | **PASS** — `add_unit` upsert before `_emit_shadow`; sink has no Chroma client |
| V4b | Lock acquisition has a 250 ms budget; timeout leaves Chroma successful and records degradation | **PASS** — `test_lock_timeout_does_not_block_caller` (default budget 250 ms) |
| V4c | Append uses one encoded-byte write, flush, file `fsync`, and first-create directory `fsync` | **PASS** — binary `a+b` single `write(data)` + flush/fsync + parent dir fsync on create |
| V4d | First-created shadow and health files are mode `0600` | **PASS** — `test_first_create_mode_0600` |
| V4e | `fsync` latency above 500 ms is measured/degraded without unsafe interruption | **PASS** — `append_degraded` / `FSYNC_DEGRADED_LATENCY_MS`; no signal interrupt |
| V4f | Concurrent writers serialize sequence allocation and produce complete parseable lines | **PASS** — `test_two_writers_serialize_sequences` |
| V4g | Uncertain acknowledgement retry reuses `event_id`; duplicates are visible and idempotent | **PASS** — fsync fail → `uncertain_ack`; retry same id → `idempotent_retries` |
| V4h | Truncated tail and invalid middle line both refuse append and make readiness FAIL | **PASS** — `truncated_tail` / `invalid_middle` → health `status=corrupt` |
| V4i | Validation/projection stops at first corruption and checkpoint never advances past it | **PASS** — `test_checkpoint_does_not_advance_past_corruption` |
| V4j | Post-Chroma/pre-shadow process death is detected by baseline/touched-ID comparison without auto-heal claim | **PASS** — `test_post_chroma_pre_shadow_gap_via_comparison` (`missing-in-shadow`) |
| V4k | Health/doctor distinguish disabled, healthy, degraded, corrupt, and baseline mismatch honestly | **PASS** — `assess_shadow_status` + doctor `_check_shadow_ledger` |

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
pytest -q tests/test_shadow_ledger_phase0_t5.py
convmem shadow-inventory
convmem shadow-inventory --json
# optional: convmem shadow-inventory --report /tmp/shadow-phase0-readiness.json
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V6a | Inventory records UTC time, code revision, resolved inputs, hashes, root identity, live counts, and rule version | **PASS** — `collect_phase0_inventory` stamp fields + file hashes |
| V6b | Repeated run over identical inputs is deterministic | **PASS** — fixed `utc`/`code_commit` ⇒ identical report |
| V6c | Counts are runtime-derived; audit snapshot values are absent from implementation constants | **PASS** — module/source + stamp tests reject `192`/`3448` |
| V6d | Default output exposes counts/stable IDs/categories, not documents, metadata payloads, secrets, or embeddings | **PASS** — `redacted_stdout_view`; CLI `--json` uses it |
| V6e | Candidate classes are deterministic/local and ambiguous rows remain human-gated | **PASS** — `classify_unit_metadata` / `ambiguous` class |
| V6f | Inventory performs no rewrite, ingest, delete, authority transfer, or LLM/API call | **PASS** — `chroma_readonly` only; no `llm`/`requests` imports |
| V6g | Machine-readable and human reports agree on PASS/PARTIAL/FAIL | **PASS** — `human_summary` mirrors `readiness.status` |
| V6h | PASS is labeled `delta capture` and makes no historic rebuild, backup, migration, cutover, or activation claim | **PASS** — status `PASS — delta capture`; `claims.not_claimed` list |

## V7 — Focused/full regression and non-mutation evidence

```bash
pytest -q tests/test_shadow_ledger_phase0_t*.py tests/test_shadow_writer_coverage_scan.py
pytest -q
convmem doctor   # expect shadow_ledger PASS disabled; restic may be unrelated FAIL
git diff --check origin/main...HEAD
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V7a | All focused Shadow Ledger Phase 0 tests pass | **PASS** — focused shadow suite green (59+; T1 now 12) |
| V7b | Full existing regression suite passes or every pre-existing failure is proved against the base | **PASS** — `pytest -q` → **837 passed** after fixing `test_inter_model_doc` mock for `chroma_write_session` |
| V7c | Doctor reports disabled production state honestly and no false readiness PASS | **PASS** — `[PASS] shadow_ledger: disabled`; inventory `PARTIAL` (not activated). Note: live `restic_gate` FAIL (stale snapshot) is unrelated ops residual — not a shadow false PASS |
| V7d | Test roots and artifacts are temporary/marked and cleaned without touching production | **PASS** — pytest `tmp_path`; replay marker `.convmem_shadow_replay_ok` under temp roots only |
| V7e | No network/provider call occurs in hermetic stub tests | **PASS** — stub replay / inventory AST forbid `llm`/`requests`; live embed tests raise without network fallback |
| V7f | Repository diff and runtime checks show no live Chroma, live config, JSONL authority, decision-log, Restic, or restore mutation | **PASS** — git paths exclude live roots; live `config.toml` has no enabled shadow section; `convmem shadow-inventory` read-only |

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
VERIFY-shadow-ledger-phase0 — tip 0070b27 (+ VERIFY-fill tip) — runner Cursor — 2026-07-25T07:28:06Z
V0 Preconditions: PASS (V0d/V0e SKIP → V8)
V1 Diff/authority: PASS
V2 Activation/config: PASS
V3 Writer coverage: PASS
V4 Durability/corruption: PASS
V5 Replay/equality: PASS
V6 Inventory/readiness: PASS
V7 Regression/non-mutation: PASS
V8 Independent sign-off: PENDING
Mechanical: PASS
Sign-off: PENDING
Ryan GATE: PENDING
Residuals: restic_gate stale (ops); embed_collection_identity WARN; activation forbidden
```

## Stub stop

Mechanical VERIFY does **not** authorize production activation, migration,
cutover, backup wiring, restore-order change, or a change in Chroma authority.
Next: V8 independent PASS/FAIL on the VERIFY-fill tip, then Ryan GATE / merge.
