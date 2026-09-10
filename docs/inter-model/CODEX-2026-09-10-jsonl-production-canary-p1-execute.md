# Implementation Handoff: Arc Codex P1 Hermetic Canary Harness

**Date:** 2026-09-10
**Author:** Codex (architecture / Execute-handoff lane)
**For:** Cursor (implementation lane; Composer Extra High recommended)
**Authorization:** Ryan, 2026-09-10 — explicit P1-T0–T8 / P1-A1–A14
Execute grant in chat after Kiro closed the plan review PASS at `8b48a39`

> **Arc: Codex.** This grant authorizes only the hermetic P1 harness. It does
> not authorize P2, any live source or production-data access, model/provider
> calls, network access, watcher action, PR creation, or activation.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` — P1 Execute authorized |
| **Merged baseline** | PR #295 squash merge `b23cabad3a040bb6fef94cc8db8d9f5714b12a46` |
| **Handoff branch** | `plan/2026-09-10-codex-jsonl-production-canary-p1-execute` |
| **Implementation branch** | create `feat/2026-09-10-codex-jsonl-production-canary-p1` from current `origin/main` with `convmem work start ... --worktree` |
| **Push status** | handoff branch pushed to origin after every commit; Cursor must do the same on its feature branch |
| **PR** | not opened; Cursor must not open one |
| **Ryan GATE** | none for P1 implementation; Kiro exact-tip review and Ryan PR decision are required afterward |
| **P2 GATE** | not granted; the live source, production paths, config, models, watcher, and canary run remain prohibited |

---

## Goal / role / system / next action

**Goal:** prove that a one-shot, exact-resource canary wrapper can safely drive
the already merged incremental Kiro JSONL coordinator without weakening its
scratch isolation or normal default-off behavior.

**Cursor's role:** implement and test P1-T0–T8 under temporary roots using only
synthetic sources and deterministic in-process fakes. Generate reproducible
evidence, push it, and stop for Kiro.

**The system currently:** the incremental coordinator and source-scoped Chroma
primitives are on `main`; the feature is disabled. The two-grant canary plan
and Kiro PASS handoff are on `main` through PR #295. No canary harness exists.

**Next action:** create the implementation worktree, establish test denials
before importing the new harness, re-run the scoped baseline, then implement
P1 in the order below.

---

## Normative specification

The authoritative requirements are:

1. [`ARCHITECTURE-codex-jsonl-production-canary.md`](../plans/ARCHITECTURE-codex-jsonl-production-canary.md)
2. [`EXECUTION-codex-jsonl-production-canary.md`](../plans/EXECUTION-codex-jsonl-production-canary.md), **P1-T0 through P1-T8 and P1-A1 through P1-A14 only**
3. [`KIRO-2026-09-10-jsonl-production-canary-review-handoff.md`](KIRO-2026-09-10-jsonl-production-canary-review-handoff.md), including the two implementer notes

The Execution plan preserves its review-time statement that P1 was not yet
authorized. This later dated handoff records Ryan's explicit P1 authorization;
it does not change any technical requirement or grant P2.

If this handoff paraphrase conflicts with those reviewed documents, stop and
report the exact contradiction. Do not expand into P2 to resolve it.

---

## What to build

Build a canary-only deep module and thin launcher around the existing
`IncrementalJsonlCoordinator`. The harness must have no ambient authority: an
exact closed-schema grant, expected SHA-256, unused nonce, temporary config,
and explicit resource-role map are required before it can construct a
write-capable coordinator.

Recommended surfaces, subject to normal code-structure judgment:

- `incremental_jsonl_canary.py` — grant decoding, capability boundary,
  preflight, one-run state receipt, call-budget guards, source-scoped capsule,
  fault supervision, serving probe, and evidence assembly;
- `scripts/run-jsonl-production-canary.py` — a thin explicit launcher that is
  not registered in the normal ConvMem CLI or watcher; and
- focused `tests/test_incremental_jsonl_canary_*.py` plus minimal helpers.

The implementation must reuse the existing governed writer, source locks,
source-scoped Chroma snapshot/restore/delete operations, checkpoint authority,
prepared artifacts, follower reconciliation, and processed-state transaction.
Do not fork the state machine.

---

## Mandatory pre-import isolation gate

Before any P1 test imports the new canary module or production integration:

1. relocate `HOME`, XDG config/data/cache/state, temporary paths, Chroma,
   checkpoint, export, dedupe, processed, locks, attestations, and census into
   a fresh tokenized temporary root;
2. install denials for `convmem`, watcher/service commands, Ollama, paid
   providers, DNS, sockets, and subprocess escape paths;
3. scrub provider credentials from an allowlisted child environment;
4. assert the dedicated Kiro source and all known production roots are outside
   the temporary root and rejected before construction;
5. prevent test collection/import from loading a real default config; and
6. contain crash workers and every descendant in a killable process group.

Use mocks or in-process fakes for network/provider semantics. Do not open a
real loopback socket and do not query installed Ollama models during P1.

Any uncertain or failed denial is a failed P1 gate. Do not downgrade it to a
skip.

---

## Ordered implementation

### T0 — baseline and scope proof

- Start from `origin/main` containing merge `b23cabad`.
- Record hashes for `watch.py`, normal CLI routing, unrelated adapters, and the
  current default-off branches.
- Run only the focused baseline tests. **Do not run bare `pytest -q`**: the
  repository-wide suite contains live-corpus retrieval tests outside this
  grant.
- Prove the test process cannot resolve or construct any live resource.

### T1 — grant and one-run receipt

- Decode a closed, versioned schema; reject unknown/missing fields.
- Require absolute canonical resource paths, unique roles, grant SHA-256,
  code revision, expiry, nonce, baseline source identity, append envelope,
  model identities, call ceilings, fault list, rollback/evidence paths, and
  expected pre-state.
- Reject symlink components, aliases, duplicate paths, unsafe modes, stale
  grants, mismatched revision/digest, and reused nonce before any writer or
  provider construction.
- Fsync a one-run receipt. It may resume listed stages after a crash but can
  never create a second run.

### T2 — separate canary capability boundary

- Implement a new boundary with the minimum coordinator protocol.
- Leave `IsolationBoundary` production-denying.
- Require the exact granted source/metadata pair read-only and exact granted
  mutable roles.
- Prove the harness cannot be entered from `maybe_route_incremental()`, normal
  `convmem index`, or `watch.py`.

### T3 — config, provider, network, and call caps

- Create a temporary config overlay; never read or write the user's live
  config as operational input in P1.
- Preserve absent/false default behavior and `allow_full_rebuild = false`.
- Canonicalize fake model aliases to exact fake tags/digests using the same
  contract P2 will use. Do not contact the real models.
- Deny provider credentials, DNS, non-loopback sockets, and descendant escape.
- Raise before cap+1 at both per-stage and whole-run limits.

Kiro's implementation note: a literal `inactive` result from a mocked
`systemctl --user is-active` probe is a confirmed negative even if the command
exit is nonzero. Ambiguous output, unavailable status, or conflicting probes
must fail closed. Do not call real systemd during P1.

### T4 — source-scoped rollback capsule

- Round-trip both Chroma collections, export, dedupe, processed entry, and all
  incremental state for one synthetic source.
- Include embeddings/documents/metadata and an independently digestible
  manifest.
- Restore only grant-listed candidate IDs under the exact `source_path`.
- Preserve sentinels from at least two unrelated sources across every crash
  side of restoration.
- Never implement or invoke a whole-Chroma/restic restore.

### T5 — operational fault supervisor

Map exactly these five selectors to real named durable seams:

1. `summary_upsert` → `unit_upsert`;
2. `unit_upsert` → `summaries_prune` / `units_prune`;
3. `units_prune` → `checkpoint_publish`;
4. `checkpoint_publish` → `export_reconcile` / `dedupe_reconcile`; and
5. `dedupe_reconcile` → `processed_publish`.

Use distinct contained child exits, record process groups and durable state,
and prove descendants absent before replay. Unknown selectors fail before
mutation. Keep the exhaustive existing 44-transition regression matrix.

### T6 — serving-visibility probe

- Probe through `ServingIndexRepository` against temporary real Chroma.
- Preserve exact observations and monotonic timestamps; do not normalize mixed
  states away.
- Prove prior→mixed→candidate, roll-forward, exact restore, 30-second hard
  stop, and three stable reads spanning at least two seconds after authority
  settles.
- Never claim atomic two-collection visibility.

### T7 — production chunking rehearsal

With synthetic Kiro JSONL and 60/10 chunking:

- baseline 61–109 accepted messages → starts 0 and 50;
- append ending at no more than 110 → still starts 0 and 50;
- 111 → rejected for this two-chunk canary profile because start 100 appears;
- stable chunk 0 reused; only frontier 50 transformed;
- unchanged replay makes zero transform calls; and
- reconstruction from the same prepared artifacts exactly equals the
  source-scoped projection without another model call.

### T8 — governance and evidence

- Update C3 and R2b writer inventories/revision binding for every new governed
  writer route; do not route around the scanners.
- Run the focused compatibility, safe-reindex-without-live-lock, isolation,
  state, serving, writer, compileall, pylint, and diff-check gates.
- Create `docs/plans/VERIFY-codex-jsonl-production-canary.md` with exact
  commands, environment versions, matrix counts, call counts, and proof of no
  live access.
- Update the Arc STATUS to the pushed implementation-tip state and route
  `LATEST.md` to Kiro exact-tip review.
- Commit and push every coherent unit. Stop with a clean branch and zero
  unpushed commits.

---

## What NOT to build or run

- No P2 grant, packet, preflight, source freeze, initial adoption, append,
  crash canary, or live evidence.
- No access—even read-only—to the dedicated Kiro canary transcript or its
  `session.json` during P1.
- No production Chroma, processed/export/dedupe/state, config, locks,
  attestations, census, or restic operations.
- No real Ollama/model inventory/provider call, paid credential, DNS, or
  socket connection.
- No persistent configuration change and no full-rebuild enablement.
- No `convmem index`, `convmem-watch`, service manager operation, watcher
  install/start/stop, or normal CLI registration.
- No chunking, retrieval, ranking, adapter, migration, or activation change.
- No broad restore and no automatic retry after unproven recovery.
- No repo-wide pytest invocation.
- No PR. Cursor stops at pushed evidence; Ryan decides PR creation only after
  Kiro reviews the exact tip.

---

## Focused test expectations

At minimum, add tests covering every P1-A1–A14 acceptance row. Suggested
grouping:

- grant schema/digest/path/nonce/expiry/revision failures;
- pre-import isolation and source-read-only behavior;
- config/default-off and CLI/watcher unreachability;
- provider/network/credential/model/call-cap failures;
- capsule exactness and cross-source sentinel preservation;
- restore crashes on both sides of every new durable transition;
- five-selector mapping plus existing 44-transition coverage assertion;
- child/descendant/stale-lock containment;
- serving mixed-state and recovery-timing observations;
- 61/109/110/111 boundary cases, frontier reuse, and zero-call replay; and
- writer inventory and revision-binding gates.

Existing regression candidates include:

- `tests/test_incremental_jsonl_config.py`
- `tests/test_incremental_jsonl_isolation.py`
- `tests/test_incremental_jsonl_state.py`
- `tests/test_safe_file_reindex.py` only where no live lock/config is needed
- `tests/test_serving_index_repository.py`
- `tests/test_shadow_writer_coverage_scan.py`
- `tests/test_shadow_writer_gate_c3.py`

All tests use fresh temporary roots. Any test requiring the user's default
config, installed models, live corpus, live service state, or production lock
is out of scope and must not be included as PASS evidence.

---

## Acceptance criteria

- [ ] **P1-A1** Existing isolation guard remains production-denying.
- [ ] **P1-A2** Canary has no default source/resource authority.
- [ ] **P1-A3** Grant digest, expiry, revision, nonce, and mode fail closed.
- [ ] **P1-A4** Synthetic source is read-only and identity-bound before/after.
- [ ] **P1-A5** Persistent/default feature and rebuild flags remain false.
- [ ] **P1-A6** Paid/nonlocal provider and outbound network are impossible.
- [ ] **P1-A7** Call ceilings stop before cap+1.
- [ ] **P1-A8** Capsule restores exact source state without sentinel change.
- [ ] **P1-A9** Five faults map to reviewed durable transitions.
- [ ] **P1-A10** Descendants and stale locks are contained or fail closed.
- [ ] **P1-A11** Serving probe reports rather than hides mixed visibility.
- [ ] **P1-A12** 60/10 frontier reuse and zero-call replay are exact.
- [ ] **P1-A13** Normal ingest/watcher route remains default-off and unchanged.
- [ ] **P1-A14** Evidence is hermetic and independently reproducible.
- [ ] Existing focused regressions pass.
- [ ] `compileall`, scoped pylint, and `git diff --check` pass.
- [ ] Diff scope matches P1 and contains no live artifacts or credentials.
- [ ] Branch is clean, pushed, and stops for Kiro exact-tip review.

---

## Branch and handoff protocol

```text
feat/2026-09-10-codex-jsonl-production-canary-p1
```

Start with `convmem work start feat codex-jsonl-production-canary-p1
--worktree` from current `origin/main`. Do not switch the shared checkout.
Push immediately after each commit using the explicit branch refspec.

At completion, report:

- exact branch and tip;
- `git log origin/main..HEAD --oneline`;
- zero-unpushed confirmation;
- exact focused test commands/counts;
- largest remaining risk; and
- the single VERIFY path for Kiro.

Do not open a PR.

---

## Related files

| What | Path |
|---|---|
| Reviewed canary architecture | `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` |
| Authoritative P1/P2 plan | `docs/plans/EXECUTION-codex-jsonl-production-canary.md` |
| Kiro closed-PASS handoff | `docs/inter-model/KIRO-2026-09-10-jsonl-production-canary-review-handoff.md` |
| Current Arc snapshot | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Existing coordinator | `incremental_jsonl.py` |
| Existing scratch guard | `incremental_jsonl_isolation.py` |
| Governed writer/store | `chroma_write_store.py`, `chroma_store.py` |
| Serving read boundary | `serving_index_repository.py` |

---

## Leaving / picking up checklist

**Codex (leaving):**

- [x] Kiro plan review closed PASS at `8b48a39`.
- [x] Reviewed plans and handoff merged via PR #295 (`b23cabad`).
- [x] Ryan explicitly authorized P1-T0–T8 / P1-A1–A14.
- [x] This handoff, `LATEST.md`, and Arc STATUS updated on a pushed plan branch.
- [x] P2 and every live operation remain expressly unauthorized.

**Cursor (picking up):**

- [ ] Read Arc STATUS and all three normative documents before edits.
- [ ] State Goal / role / system state / next action and **Arc: Codex**.
- [ ] Create the feature worktree from current `origin/main`.
- [ ] Install the P1 pre-import denials before loading the new module.
- [ ] Execute only T0–T8 and map evidence to A1–A14.
- [ ] Push every commit; stop at evidence for Kiro without opening a PR.

## TL;DR

- Ryan authorized Cursor to implement only the hermetic P1 canary harness at
  P1-T0–T8 / P1-A1–A14.
- All sources, stores, configs, services, providers, sockets, and models are
  synthetic or temporary in P1; the dedicated live Kiro session is forbidden.
- Cursor pushes reproducible evidence and stops for Kiro. P2, PR creation, and
  activation remain separately Ryan-gated.

## Jargon TL;DR

- **P1:** temporary-root-only implementation and proof of the canary harness.
- **P2:** later one-source live run; not authorized here.
- **Grant:** closed SHA-256-bound resource and operation manifest.
- **Nonce receipt:** durable proof that one grant creates only one resumable
  run.
- **Gate 0:** fail-closed checks before any live write or model call.
- **Frontier:** earliest overlap-affected chunk that must be transformed.
- **Follower:** rebuildable Chroma or sidecar projection governed by the
  checkpoint.
- **Mixed visibility:** a reader seeing the two collections at different
  generation states.
