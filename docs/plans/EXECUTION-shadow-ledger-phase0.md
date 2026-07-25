# Execution Plan — Shadow Ledger Phase 0

```text
Planning Status

Phase:        Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Codex authors; Kiro reviews; Cursor downstream implementation
Authority:    Awaiting Ryan HITL on this Execution Plan; Execute is unauthorized
```

**Source:** Ryan-authorized Cursor → Codex work order
[`CURSOR-2026-07-24-shadow-ledger-phase0-codex-execution-handoff.md`](../inter-model/CURSOR-2026-07-24-shadow-ledger-phase0-codex-execution-handoff.md),
on branch `docs/2026-07-24-shadow-ledger-phase0-architecture` at authorized
planning tip `c13042c`.

**Approved direction:**
[`ARCHITECTURE-shadow-ledger-phase0.md`](ARCHITECTURE-shadow-ledger-phase0.md)
was Architecture-HITL approved by Ryan on 2026-07-24. Gate 1b passed after
audit correction PR `#121` landed on `main` as `0d08310`.

**Goal:** Prove that every covered post-activation `knowledge_units` mutation
can be captured durably, replayed into a disposable Chroma root, and compared
against authoritative Chroma without enabling production shadowing or changing
data authority.

## Human consequence

If Ryan approves this plan, Cursor receives five bounded implementation tasks
that produce a disabled-by-default Shadow Ledger Phase 0 mechanism and its
evidence. Chroma remains Tier-1. The implementation may demonstrate delta
capture and disposable replay, but it cannot activate shadowing on production,
claim a historic rebuild, change restore order, or transfer authority.

The largest accepted trade-off is synchronous file durability after a Chroma
success: shadow `fsync` can add latency, while failure still leaves Chroma's
successful result intact. The mechanism remains reversible because absent or
disabled configuration injects no sink.

## Intake and locked direction

Execution must translate, not reopen, these Architecture decisions:

- Use Option B: an optional mutation observer on `ChromaStore` plus one
  authoritative write-store factory.
- Observe only confirmed per-entity `knowledge_units` mutations. Summary
  mutations remain excluded.
- Chroma remains authoritative; the shadow JSONL is non-authoritative.
- Generate the event identity before the Chroma call, then append only after
  Chroma succeeds.
- A shadow failure is visible but never rolls back or changes a successful
  Chroma result.
- Use the locked envelope, operation vocabulary, SHA-256 canonical-JSON hash
  rules, duplicate semantics, lock order, durability contract, failure
  visibility, disposable replay boundary, inventory rules, and backup doctrine.
- Prove only the post-activation delta for touched stable entity IDs.
- Treat unknown embedding provenance as `UNVERIFIABLE`, never as equality.
- Keep Chroma-first backup and restore unchanged.

Architecture and the Gate 1b correction banners take precedence over stale
audit-body proposals. For Phase 0, corruption is fail-closed: validation and
projection stop at the first invalid record, the checkpoint does not advance,
and any temporary quarantine copy is diagnostic only. There is no
quarantine-and-continue success path.

## Scope boundary

### In scope

- A docs contract that freezes the Phase 0 envelope, activation/configuration
  contract, baseline manifest fields, readiness meanings, and non-authority
  language.
- Disabled-by-default configuration parsing and isolated activation-manifest
  validation. Example configuration may be added; live user configuration may
  not be changed.
- An optional `ChromaStore` unit-mutation observer and one authoritative
  write-store factory that is the only production injection boundary.
- A durable append-only shadow writer, validator, health sidecar, and complete
  unit-writer coverage evidence.
- Hermetic durability, concurrency, crash-window, corruption, and failure
  tests.
- Disposable delta replay into a newly created marked temporary root, with
  state/projection comparison and explicit stub/live embedding modes.
- Read-only, runtime-stamped inventory and a machine-readable Phase 0 readiness
  report.
- Focused tests, full regression, doctor evidence, targeted safety/isolation
  review, and the filled arc VERIFY artifact.

### Out of scope

- Production read-path changes or any authority transfer from Chroma.
- Production activation, including editing live config, creating a production
  activation manifest, attaching the sink to the live root, or starting an
  observation period.
- `conversation_summaries`, approved/pending decision authority, proposal event
  logs, or governed-decision semantics.
- Historic bootstrap, full empty-corpus rebuild, migration, live Chroma rewrite,
  `knowledge_units.jsonl` rewrite, auto-ingest, auto-delete, or auto-repair.
- Canonical observation-schema freeze, cutover, restore-order flip, or treating
  the shadow as a backup/restore source.
- Restic includes, timers, tags, retention automation, Track 1 complete-data
  backup, or Hybrid audit work.
- Neutral Core, Office Team, cross-project extraction, retrieval/ranking work,
  or re-opening Architecture Options A/B/C.
- Git hooks, always-on background hooks, or new production automation. Fitness
  checks belong in tests/CI and explicit commands only.
- Further edits to `docs/audit-ledger-first/`.

### Deferred behind later Ryan gates

- Exact production root, final enabled config value, production activation
  manifest, and activation time.
- Observation-period length and readiness acceptance.
- Canonical schema, historic bootstrap, migration manifest, ambiguous-record
  disposition, cutover, backup wiring, and restore redesign.

## Exact Phase 0 configuration contract

T1 must document and tests must enforce this optional table shape:

```toml
[shadow_ledger]
enabled = false
ledger_path = "~/.local/share/convmem/shadow_ledger.jsonl"
activation_manifest_path = "~/.local/share/convmem/shadow_activation.json"
health_path = "~/.local/share/convmem/shadow_health.json"
```

Contract rules:

1. An absent `[shadow_ledger]` table and `enabled = false` are equivalent: no
   sink is constructed or injected.
2. These example paths do not activate production. `enabled = true` only permits
   an activation attempt; it does not attach a sink unless the complete manifest,
   shadow file, and exact resolved Chroma root all validate.
3. The write-store factory compares canonical `resolve()` results and refuses a
   mismatched root, production-root alias, incomplete manifest, corrupt ledger,
   or baseline mismatch.
4. Read-only, verify, evaluation, restore-drill, and disposable replay stores
   always receive `mutation_sink=None`, regardless of config.
5. The live user config remains untouched until Ryan separately authorizes the
   exact root, paths, activation operation, and final enabled state.
6. The shadow ledger and sidecar contain documents/metadata or diagnostics and
   must be mode `0600`; normal stdout and readiness summaries expose counts,
   stable IDs, hashes, and categories, not record payloads.

## Ordered tasks

| ID | Deliverable | In scope | Depends on | Gates | Execution lane |
|----|-------------|----------|------------|-------|----------------|
| **T1** | Phase 0 contract, disabled config, and activation baseline | Contract doc; exact optional config shape; parser/path handling; manifest creation/validation; runtime inventory stamp; no live activation | — | Contract tests; absent/false no-sink tests; invalid/mismatched activation refusal; baseline atomicity/durability tests | Cursor |
| **T2** | Shadow writer, mutation sink, and complete writer coverage | Optional observer; confirmed per-entity events for all five unit mutators; authoritative write-store factory; closed envelope/vocabulary/hash validation; coverage fitness | T1 | Unit/integration coverage; direct-client allowlist; no summary events; sink failure preserves Chroma result | Cursor |
| **T3** | Durability, corruption, concurrency, and failure evidence | Lock/commit order; `0600`; single append; file/directory `fsync`; timeout/latency telemetry; duplicate retry; crash window; fail-closed corruption | T2 | Hermetic fault-injection and process-boundary tests; checkpoint stop; doctor/readiness status checks | Cursor |
| **T4** | Disposable replay and final-state comparison | Marked temp-root projector; sink forced off; stub/live embedding modes; ordered idempotent replay; two-level comparison and categories | T2 | Root/symlink/nonempty-target refusal; recursion test; duplicate/checkpoint tests; equality and `UNVERIFIABLE` tests | Cursor |
| **T5** | Runtime inventory and Phase 0 readiness report | Read-only snapshot inventory; deterministic candidate classes; machine-readable report; human summary; filled VERIFY evidence | T3, T4 | Determinism/redaction/non-mutation tests; PASS/PARTIAL/FAIL semantics; focused/full regression; independent sign-off handoff | Cursor |

T1 and T2 are serial because implementation cannot safely encode events or
inject a sink before the contract and activation boundary are executable. After
T2 stabilizes the observer and validator interfaces, T3 and T4 are
parallel-safe with disjoint test concerns. The inventory collector portion of
T5 may begin after T1, but the readiness verdict and filled VERIFY remain
blocked on both T3 and T4.

## T1 — Phase 0 contract, disabled config, and activation baseline

### Deliverable

1. Create `docs/plans/PHASE0-SHADOW-CONTRACT.md` during Execute. It must be the
   human-readable mirror of the locked Architecture decisions, not a canonical
   observation-schema proposal.
2. Add the exact optional `[shadow_ledger]` shape above to config parsing and
   `config.example.toml`, with `enabled = false`. Do not edit
   `~/.config/convmem/config.toml`.
3. Define a machine-readable activation manifest containing:
   manifest version and unique baseline ID; completion status; UTC activation
   timestamp; code commit; resolved Chroma root and collection identity; active
   and total unit counts; per-entity document/metadata/state hashes; configured
   and observed embedding identity plus dimensions; shadow identity and starting
   sequence; and hashing rules/version.
4. Build the manifest from runtime reads only. Write a temporary file, flush and
   `fsync`, atomically rename, then `fsync` the parent directory. An incomplete
   manifest cannot enable the sink.
5. Record configured and observed embedding identity separately. Legacy
   collection identity remains `unknown` unless measured metadata proves it.
6. Capture a fresh UTC/code/root/count stamp before any later inventory or
   migration-flavored discussion. Never encode the audit's `192`, `3,448`, or
   other snapshot counts as constants.

### Gates

- Missing table and `enabled = false` produce the same no-sink result.
- `enabled = true` without a complete matching manifest refuses injection and
  reports why.
- Root canonicalization rejects a different root and alias mismatch.
- The baseline is complete and durable before activation status can become
  eligible; an interrupted build remains visibly incomplete.
- Config/example changes cannot activate a live store.
- The contract explicitly says Chroma Tier-1, post-activation delta only,
  provisional schema, no backup/restore authority, and no cutover.

## T2 — Shadow writer, mutation sink, and complete writer coverage

### Deliverable

1. Add a narrow `UnitMutationSink` boundary. `ChromaStore` accepts an optional
   observer defaulting to `None`; it does not load global config or decide
   activation.
2. Add one authoritative write-store factory. It is the only production path
   that may inject the sink after T1 validation. All other store factories and
   constructors remain sink-free.
3. Emit one event for each confirmed entity mutation from:
   `add_unit`, `update_unit`, `update_unit_metadata`,
   `supersede_units_for_source`, and `delete_units_for_source`.
4. Create the event context and `event_id` before the Chroma call. Append the
   complete post-state or deletion tombstone only after Chroma confirms success.
   A pre-Chroma failure emits no event.
5. Enforce schema version 1 operations only: `create`, `replace`,
   `metadata_update`, `supersede`, `restore`, and `delete`. Bulk source changes
   emit per-confirmed-entity events; aggregate counts are diagnostics only.
6. Hash canonical UTF-8 JSON with SHA-256, sorted keys, compact separators, and
   no NaN. Raw embeddings never enter the ledger.
7. Preserve uncertain-ack retries with the same event object and `event_id`.
   Replay applies the first valid occurrence and counts later copies as
   idempotent duplicates.
8. Produce a machine-readable writer inventory that maps every production
   mutating caller to the authoritative factory and every unit-mutating
   `ChromaStore` method to emitted/excluded behavior.

### Coverage proof

Grep is supplementary evidence, not the proof. Execute must provide all three:

1. A static direct-client scan with an explicit allowlist for the storage
   adapter, tests, evaluation projection, and restore-drill isolation.
2. A test that enumerates the unit-mutating `ChromaStore` methods and fails when
   a method lacks an event assertion or explicit collection exclusion.
3. Integration tests exercising the production mutating call paths and proving
   one confirmed entity event per successful mutation, including partial bulk
   completion.

No event may be emitted for `conversation_summaries`, a failed Chroma mutation,
or a store constructed for read, verify, evaluation, restore drill, or replay.

## T3 — Durability, corruption, concurrency, and failure evidence

### Deliverable

1. Enforce the fixed order: create context → confirm Chroma → release any
   Chroma operation → acquire shadow `flock` → validate tail → allocate sequence
   → issue one encoded-byte append → flush/`fsync` file → first-create parent
   directory `fsync` → release lock.
2. Bound only lock acquisition to 250 ms. On timeout, warn, update health best
   effort, and return without retrying or changing the Chroma result.
3. Measure `fsync` latency and mark append latency over 500 ms degraded. Do not
   use signal interruption to claim a hard I/O bound.
4. Maintain an atomic best-effort health sidecar with last success/failure,
   failure class, consecutive failures, lock timeouts, event ID, sequence, and
   append latency. The sidecar must not become an authority source.
5. Refuse append on an invalid/truncated tail. Full validation, replay, and
   readiness stop at the first invalid record; checkpoint state never advances
   past it. Do not auto-truncate, skip, repair, or continue projection.
6. Inject and test Chroma-success/pre-shadow termination. The only guaranteed
   detector is baseline/touched-ID comparison; no auto-heal claim is allowed.
7. Distinguish fresh isolated failure (doctor WARN) from persistent failure,
   corruption, baseline mismatch, or unexplained drift (readiness FAIL).

### Required evidence scenarios

- Two writers serialize sequence allocation and produce parseable complete
  lines.
- Lock acquisition exceeds 250 ms: Chroma succeeds, event is missing, health
  records the miss, and comparison reports `missing-in-shadow`.
- File `fsync` fails after append: acknowledgement is uncertain, retry reuses the
  event ID, and duplicate count is visible.
- First creation asserts file mode `0600` plus file and parent-directory
  `fsync` calls.
- Process death after Chroma success and before shadow/health write leaves a
  detectable comparison gap.
- Truncated tail and invalid middle line both produce FAIL, no new append, no
  later projection, and no checkpoint advance.
- Shadow append/health-sidecar failure never converts a successful authoritative
  Chroma mutation into failure.

## T4 — Disposable replay and final-state comparison

### Deliverable

1. Reduce valid events in sequence order to final state by stable entity ID and
   project only touched IDs into a newly created temporary Chroma root.
2. Require a tool-owned safety marker and refuse the configured production root,
   its parent, any symlink/canonical alias, or a nonempty unmarked target.
3. Force `mutation_sink=None` in the projector even when config says enabled.
   Replay must not append shadow events or recurse.
4. Keep the checkpoint under the disposable root. Advance it only after a valid
   event projects successfully, and never past corruption.
5. Support two explicit modes:
   - `stub`: deterministic placeholder embeddings of recorded dimensions;
     hermetic, offline, and the required automated-test mode.
   - `live`: opt-in re-embedding with the configured local model in the
     disposable root only. It is supplemental evidence, never required for
     state equality, never uses an external provider, and cannot turn unknown
     historic model provenance into PASS.
6. Report state equality and projection equality independently. Raw vectors are
   excluded. Exact document drift fails projection equality; known-vs-unknown
   model identity is `UNVERIFIABLE`.
7. Report at least: missing-in-shadow, missing-in-Chroma, state mismatch,
   projection mismatch, unknown embed provenance, duplicates, corrupt records,
   and extras.

### Gates

- Empty/new marked temp root succeeds; production, parent, alias, and unmarked
  nonempty targets fail before opening a writable client.
- Stub mode is deterministic and makes no Ollama/network call.
- Live mode remains explicit, disposable, and cannot change readiness semantics
  for unknown historic provenance.
- Duplicate event IDs apply once and remain counted; distinct IDs with equal
  state remain ordered history.
- A document mismatch cannot PASS projection equality.
- The comparator scopes its claim to the activation baseline and touched IDs,
  not the historic corpus.

## T5 — Runtime inventory and Phase 0 readiness report

### Deliverable

1. Produce a read-only, snapshot-stamped inventory recording UTC time, code
   revision, resolved input paths, file hashes, Chroma root/collection identity,
   live counts, and comparison-rule version.
2. Report Chroma-only counts and stable IDs without payloads by default. Never
   hardcode the audit snapshot counts.
3. Classify legacy-decision candidates deterministically and locally as:
   exact approved identity/content match; normalized title+summary with
   provenance agreement; likely observation/non-governed extracted statement;
   or ambiguous/human review required.
4. Make inventory and classification non-mutating: no auto rewrite, ingest,
   delete, authority transfer, LLM/API call, or human disposition.
5. Emit a machine-readable readiness report plus a concise human summary with
   statuses `PASS — delta capture`, `PARTIAL`, or `FAIL` exactly as defined by
   Architecture.
6. Populate
   [`VERIFY-shadow-ledger-phase0.md`](VERIFY-shadow-ledger-phase0.md) with the
   exact Execute tip, commands, evidence, residuals, and independent-review
   handoff. Cursor fills mechanical evidence only.

### Readiness rules

- `PASS — delta capture` requires all covered touched IDs to reconcile, no
  corruption, clear failure telemetry, safe replay isolation, deterministic
  inventory, and separately disclosed unknown provenance.
- `PARTIAL` covers healthy but insufficient evidence, uncovered mutation types,
  incomplete observation, or unknown provenance that prevents a stronger claim.
- `FAIL` covers unexplained missing events, state/projection mismatches,
  corruption, persistent sink failure, unsafe replay target, or nondeterministic
  inventory.
- PASS never means historic rebuild, migration readiness, backup status,
  cutover authorization, or production activation approval.

## Evidence requirements for Execute

### First preflight and runtime stamp

This is the first verification command block Cursor must run after Ryan approves
this plan, before editing runtime code:

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
git branch --show-current
git rev-parse HEAD
git status --short
convmem doctor
convmem brief --stdout-only
```

The command output belongs in the PR/VERIFY evidence, not a new repo log. It
re-measures corpus state and prevents audit snapshot counts from becoming live
constants.

### Focused automated evidence

The implementation must add focused test modules covering these contracts:

- activation/config/baseline and root matching;
- envelope, hashes, operation vocabulary, duplicate semantics, and writer
  coverage;
- durability, lock timeout, concurrency, health telemetry, and corruption;
- disposable replay, target isolation, recursion prevention, checkpointing,
  and two-level equality;
- runtime inventory, deterministic classification, redaction, non-mutation,
  and readiness statuses.

The test names/paths may follow repository convention, but the five behavioral
groups above are mandatory. The filled VERIFY must cite the exact paths and
commands rather than relying on chat claims.

### Supplementary static evidence

Execute must record the results of repository-wide scans for direct
`chromadb.PersistentClient` use, direct `ChromaStore` construction, and the five
unit-mutating methods. Any allowlisted exception must state why it cannot touch
the authoritative production root with a sink. Static scans cannot replace the
dynamic coverage tests.

### Regression and safety evidence

- Focused shadow-ledger test groups pass.
- The existing full test suite passes.
- `convmem doctor` and relevant `doctor --v1` checks report the shadow state
  honestly while disabled and in isolated failure fixtures.
- `git diff --check` passes and the implementation diff remains within this
  plan's scope.
- No live config, live shadow file, Restic config, restore doctrine, audit-pack
  body, Neutral/Office path, production data root, or ledger authority file is
  changed.
- A targeted independent safety/isolation review examines production-root
  refusal, symlink aliases, corruption stop behavior, secret/payload exposure,
  and Chroma-success/shadow-failure semantics at the final Execute tip.

## External review applicability

External technical review is **required** for the eventual Execute PR because
the diff will touch the production mutation boundary, filesystem durability,
and replay isolation. Execute must preserve final-tip review evidence and route
every finding to `fixed` or Ryan-accepted disposition. A technical review does
not replace Kiro plan/sign-off duties or Ryan's HITL gates.

No external review is invoked by this Execution Planning phase.

## Stop conditions during Execute

Cursor must stop and return to Ryan/Codex instead of silently replanning if:

- complete writer coverage requires a new authority boundary or an Architecture
  option change;
- the exact config/activation contract cannot be implemented without enabling
  production behavior;
- a direct production writer bypass cannot be routed through the approved
  factory without expanding scope;
- corruption handling would continue projection beyond the invalid record;
- replay isolation cannot prove refusal of production-root aliases before a
  writable client opens;
- a task would mutate live Chroma, live config, JSONL authority, decision logs,
  Restic/restore behavior, or audit baseline bodies;
- live embedding evidence would require an external provider, new cost, or an
  unapproved model change;
- focused or full regression fails for a reason not demonstrably pre-existing;
- the implementation diff materially departs from this plan.

## Rollback and reversibility

- Before separate production activation, rollback is code/config-example
  reversion only; no production shadow state should exist.
- In isolated tests, deleting the marked temporary replay root and generated
  test artifacts restores the pre-test state.
- After a future separately authorized activation, disabling sink injection
  returns writes to current behavior. Shadow artifacts remain diagnostic and
  non-authoritative; this plan does not authorize deleting or restoring from
  them.
- No rollback path may rewrite the append-only shadow file automatically.

## Arc VERIFY companion

- Path: [`docs/plans/VERIFY-shadow-ledger-phase0.md`](VERIFY-shadow-ledger-phase0.md)
- Status: stub created during Execution Planning; fill after Execute.
- Template: [`docs/plans/VERIFY-TEMPLATE.md`](VERIFY-TEMPLATE.md)
- Mechanical evidence: Cursor at the exact Execute tip.
- Independent sign-off: Kiro or another Ryan-named independent lane.
- Final gate: Ryan.

## Execute entry

- Entry authority: only after Ryan approves this Execution Plan.
- First task: T1, beginning with the runtime-stamp command block above.
- Execution lane: Cursor.
- Task order: T1 → T2 → T3 and T4 (parallel-safe after T2) → T5.
- Production activation remains a separate later Ryan grant even after all five
  tasks and VERIFY pass.
- Do not merge, deploy, activate, write a ledger decision, or self-transition
  to Verify/Revise/Architecture.

Active phase lane must stop here. Await HITL.
