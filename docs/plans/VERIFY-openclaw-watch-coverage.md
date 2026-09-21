# OpenClaw Watch Coverage — verification evidence

**Arc: OpenClaw Watch Coverage**

**Implementation branch:** `feat/2026-09-21-openclaw-watch-coverage`

**Reviewed plan:** `19dea97368408ee0b179c05c942306f6d8f1a2e8`

**Code baseline:** `5ab03a37559a93f1b51932c57a2a2a783da3354b`

The machine authority is
`config/repository-knowledge/openclaw-watch-scope-v1.json`. The table below is
a review snapshot, not a second source of truth. Git-clean `audit --manifest`
is recorded after the implementation commit lands; until then the working
tree is dirty by construction.

## Inventory snapshot

Worktree generator after staging W0–W6 files:

| Class | Count |
|---|---|
| include | 69 |
| exclude | 169 |
| unrelated | 1226 |
| tracked classifications | 1464 |
| required_when_present (absent) | 68 |
| retire | 0 |
| unclassified | 0 |

Exclude reasons: `unrelated_material` 146, `vcs_caches_build` 9,
`generated_duplicates` 7, `credentials` 5, `authority_private` 1,
`live_data_stores` 1. The control-state manifest itself is excluded
(`generated_duplicates`).

### include (review snapshot)

| Path | Content |
|---|---|
| `AGENTS.md` | markdown |
| `adapters/detect.py` | python |
| `adapters/inter_model_doc.py` | python |
| `adapters/repository_knowledge.py` | python |
| `chroma_store.py` | python |
| `chroma_write_store.py` | python |
| `config.example.toml` | toml |
| `config.py` | python |
| `config/agent-protocol.md` | markdown |
| `config/repository-knowledge/openclaw-watch-scope-v1.schema.json` | json |
| `conflict_events.py` | python |
| `convmem.py` | python |
| `docs/CODEX-DEEPSEEK-VERIFY.md` | markdown |
| `docs/MILESTONE-F.md` | markdown |
| `docs/MODEL-WORKFLOW.md` | markdown |
| `docs/RECOVER.md` | markdown |
| `docs/builder-reference/hard-parts-builder-digest.md` | markdown |
| `docs/builder-reference/manning-builder-digest.md` | markdown |
| `docs/builder-reference/ousterhout-builder-digest.md` | markdown |
| `docs/builder-reference/zeller-builder-digest.md` | markdown |
| `docs/inter-model/CODEX-2026-09-21-openclaw-watch-coverage-execute.md` | markdown |
| `docs/plans/ARCHITECTURE-always-github-fallback.md` | markdown |
| `docs/plans/ARCHITECTURE-openclaw-watch-coverage.md` | markdown |
| `docs/plans/ARCHITECTURE-watch-incremental-index.md` | markdown |
| `docs/plans/EXECUTION-always-github-fallback.md` | markdown |
| `docs/plans/EXECUTION-git-hygiene-baseline.md` | markdown |
| `docs/plans/EXECUTION-openclaw-watch-coverage.md` | markdown |
| `docs/plans/EXECUTION-watch-incremental-index.md` | markdown |
| `docs/plans/INVARIANTS-watch-incremental-index.md` | markdown |
| `docs/plans/STATUS-openclaw-watch-coverage.md` | markdown |
| `docs/plans/VERIFY-openclaw-watch-coverage.md` | markdown |
| `docs/plans/git-hygiene-baseline.md` | markdown |
| `ingest.py` | python |
| `inter_model_index.py` | python |
| `mcp_server.py` | python |
| `observe.py` | python |
| `propose_decision.py` | python |
| `provenance.py` | python |
| `provenance_binding.py` | python |
| `repository_knowledge_index.py` | python |
| `repository_knowledge_scope.py` | python |
| `repository_knowledge_sync.py` | python |
| `source_reconciler.py` | python |
| `tests/fixtures/repository_knowledge/eligible/*` (9 files) | markdown/python/javascript/json/toml/text |
| `tests/test_chroma_approve_index.py` | python |
| `tests/test_governed_recovery_and_writers.py` | python |
| `tests/test_governed_writer_gate.py` | python |
| `tests/test_inter_model_doc.py` | python |
| `tests/test_openclaw_watch_coverage.py` | python |
| `tests/test_propose_decision.py` | python |
| `tests/test_provenance.py` | python |
| `tests/test_provenance_continuity.py` | python |
| `tests/test_repository_knowledge_*.py` | python |
| `tests/test_shadow_writer_coverage_scan.py` | python |
| `tests/test_shadow_writer_gate_c3.py` | python |
| `tests/test_watch.py` | python |
| `tests/test_watch_skip.py` | python |
| `tests/test_writer_census.py` | python |
| `watch.py` | python |

## Acceptance A1–A12

| ID | Result | Evidence |
|---|---|---|
| A1 | PASS (isolated) | Scope tests: unclassified tree fails; complete fixture classification; production generator reports unclassified=0 |
| A2 | PASS | Dirty/staged/untracked/copy/symlink/hash-mismatch tests refuse before parse |
| A3 | PASS | Two-root E2E retrieved markdown, python, json, javascript, toml, text, and ops needles |
| A4 | PASS | Folder canary absent, then one public `index --file` child, then retrievable |
| A5 | PASS | Clean commit + manifest hash update replaced retrieval with the new nonce |
| A6 | PASS | Sync test: retirement refuses stale prior-manifest identity and does not touch `inter_model_doc` rows |
| A7 | PASS | Credential nonce unretrievable; detector maps excludes to blocked with no parser |
| A8 | PASS | E2E units carry `source_type`, path, commit, file/manifest hashes, locator, adapter version, claimed envelope, `effective_integrity=untrusted` |
| A9 | PASS | Isolated governance tree hash identical before and after indexing |
| A10 | PASS | Inert `approved propose_decision convmem record` text retrieved as documentary content |
| A11 | PASS | Second fresh root: same needles, same content-addressed unit IDs, same governance hashes |
| A12 | FAIL | Focused watch/inter-model/provenance tests passed; `tests/test_shadow_writer_coverage_scan.py::test_static_scan_matches_inventory_routing` failed because new `production_chroma_write_session` call sites are in allowlisted modules while `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` is outside the frozen edit surface |

## Commands

```text
python -m pytest -q \
  tests/test_repository_knowledge_scope.py \
  tests/test_repository_knowledge_adapter.py \
  tests/test_repository_knowledge_sync.py \
  tests/test_openclaw_watch_coverage.py
# 22 passed, 7 subtests passed in 9.54s
# wall 9.76s, max RSS 145060 kB (Linux ru_maxrss)

python -m pytest -q \
  tests/test_repository_knowledge_scope.py \
  tests/test_repository_knowledge_adapter.py \
  tests/test_repository_knowledge_sync.py \
  tests/test_openclaw_watch_coverage.py \
  tests/test_watch.py \
  tests/test_watch_skip.py \
  tests/test_inter_model_doc.py \
  tests/test_provenance.py \
  tests/test_provenance_continuity.py \
  tests/test_governed_writer_gate.py \
  tests/test_governed_recovery_and_writers.py \
  tests/test_shadow_writer_gate_c3.py \
  tests/test_propose_decision.py \
  tests/test_chroma_approve_index.py \
  tests/test_shadow_writer_coverage_scan.py \
  tests/test_writer_census.py
# 1 failed, 156 passed, 2 warnings, 12 subtests passed in 16.00s
# FAIL: test_static_scan_matches_inventory_routing
# extra={'ingest.py:1212', 'ingest.py:1174',
#        'repository_knowledge_index.py:256',
#        'repository_knowledge_sync.py:226'}
# missing={'ingest.py:1138', 'ingest.py:1176'}

python repository_knowledge_scope.py audit \
  --manifest config/repository-knowledge/openclaw-watch-scope-v1.json
# pre-commit: fails Git-clean (manifest/worktree dirty vs HEAD)
# post-commit: re-run on the clean tip

git diff --check
# clean

Source scan of adapters/repository_knowledge.py,
repository_knowledge_index.py, repository_knowledge_scope.py,
repository_knowledge_sync.py: no import or call of propose_decision,
governed_admission, observe, conflict_events, or publication writers.
Fixture/E2E strings mentioning those names are inert content only.
```

## Governance hashes

Isolated E2E writes empty proposal/approval/ledger/receipt/publication files
in a temp tree and asserts the tree hash is unchanged after indexing. Live
governance paths were not opened.

## Resource measurements

| Item | Value |
|---|---|
| Isolated E2E wall | 8.6–9.2s for two roots |
| RK unit+E2E wall | 9.76s |
| RK unit+E2E max RSS | 145060 kB |
| Fixture files/bytes | 14 files, 1243 bytes |
| Temporary disk | pytest tempdirs only; no live chroma/config |
| Hermetic RSS utility | none applicable; used `resource.getrusage` |

## Deferred required_when_present paths

68 exact absent paths, including the Kiro-approved OpenClaw architecture and
execution plans, T0–T5 modules/tests/fixtures/schemas, connector files, and
prospective Gate W `governed_admission.py` plus admission schemas. Full list
is in the manifest `required_when_present` array.

## Verdict

- `IMPLEMENTATION`: BLOCKED (A12 writer-inventory JSON is outside the Execute allowlist)
- `WATCH_COVERAGE`: BLOCKED
- `LIVE_WATCH`: NOT_ACTIVATED
- `CURRENT_OPENCLAW_PLAN_BYTES`: REQUIRED_WHEN_PRESENT
