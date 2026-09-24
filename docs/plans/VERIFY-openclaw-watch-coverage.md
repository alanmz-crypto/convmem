# OpenClaw Watch Coverage — verification evidence

**Arc: OpenClaw Watch Coverage**

**Implementation branch:** `fix/2026-09-21-openclaw-watch-coverage-refinement`

**Corrective implementation commit:** `fa7f62926c2831817273fb98fa3be3d762f1cd7d`

**Merged main commit:** `dc79eeb328c98f34add4d51b73d23b114afcfc21`

**Inventory-closure merge:** `2e50ec38e35bf806bf9edec662dc97344aa09ee7`
(GitHub PR `#331`)

**Reviewed plan:** `19dea97368408ee0b179c05c942306f6d8f1a2e8`

**Code baseline:** `5ab03a37559a93f1b51932c57a2a2a783da3354b`

The machine authority is
`config/repository-knowledge/openclaw-watch-scope-v1.json`. The table below is
a review snapshot, not a second source of truth. The Git-clean audit below was
run at the pushed corrective implementation commit.

## Inventory snapshot

Git-clean audit at `fa7f62926c2831817273fb98fa3be3d762f1cd7d`:

| Class | Count |
|---|---|
| include | 70 |
| exclude | 169 |
| unrelated | 1226 |
| tracked classifications | 1465 |
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
| `tests/fixtures/repository_knowledge/subprocess/sitecustomize.py` | python |
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
| A3 | PASS | Documentary fixture E2E retrieved markdown, python, JSON, JavaScript, TOML, text, and ops needles; aggregate line windows remain bounded while covering every source line without truncation |
| A4 | PASS | Real watchdog E2E: folder canary absent, filesystem event/debounce fired, exact public `index --file` subprocess ran, and public `search` retrieved the nonce |
| A5 | PASS | Real watcher E2E replaced the changed file and public `search` retrieved the new nonce; manifest-only/Git-only identity changes re-dispatch every included file |
| A6 | PASS | Retirement requires the prior sync-state file+manifest identity and row metadata match; completed retirements persist exact resolved identity and remain idempotent on later startup; mismatched-manifest and non-`repository_knowledge_v1` rows remain untouched |
| A7 | PASS | Credential nonce unretrievable; detector maps excludes to blocked with no parser |
| A8 | PASS | Units carry root-bound deterministic IDs, exact JSON source spans/byte locators, `source_type`, path, commit, file/manifest hashes, locator, adapter version, claimed envelope, `effective_integrity=untrusted` |
| A9 | PASS | Isolated governance tree hash identical before and after indexing |
| A10 | PASS | Inert `approved propose_decision convmem record` text retrieved as documentary content |
| A11 | PASS | Same canonical repository replayed into a second fresh ConvMem data root: identical inventory, active unit IDs, metadata, and public-query needles; distinct repository roots intentionally produce distinct IDs |
| A12 | PASS | Ryan authorized the writer-inventory correction; all 18 production/ScratchBoundary writer routes are inventoried and both writer coverage tests pass |

## Commands

```text
python -m pytest -q \
  tests/test_repository_knowledge_scope.py \
  tests/test_repository_knowledge_adapter.py \
  tests/test_repository_knowledge_sync.py \
  tests/test_openclaw_watch_coverage.py
# 29 passed, 7 subtests passed in 29.19s
# Includes the real watcher/subprocess/public-query two-data-root E2E.

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
# 164 passed, 2 warnings, 12 subtests passed in 27.59s

python repository_knowledge_scope.py audit \
  --manifest config/repository-knowledge/openclaw-watch-scope-v1.json
# PASS at fa7f62926c2831817273fb98fa3be3d762f1cd7d
# include=70 exclude=169 unrelated=1226 tracked=1465
# required_when_present=68 retire=0 unclassified=0
# manifest_sha256=afbad7c6edb587b2674e6f8a78fcadb6ecd1e2b97c633f02fff2304df1a70d3e

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
activation also captured before/after SHA-256 values for
`pending_decisions.jsonl`, `pending_decision_events.jsonl`,
`decisions-approved.jsonl`, the authorization tree, and the file-generation
authority tree. Every value was byte-identical after startup reconciliation.

## Live activation — 2026-09-21

Ryan separately authorized the exact live configuration, service, resource
limits, clean runtime checkout, and rollback. Activation used:

- clean `main` runtime worktree:
  `/home/lauer/Projects/convmem/.worktrees/runtime-main` at `dc79eeb`;
- manifest:
  `config/repository-knowledge/openclaw-watch-scope-v1.json` at SHA-256
  `a376c6c9d0e2182969a94d67a23759c7b25aa01da0f35a64efc792332bf60141`;
- service: `convmem-watch.service`, enabled and active;
- effective limits: `MemoryMax=4G`, `MemoryHigh=3G`,
  `MemorySwapMax=0`; and
- timestamped live-config and unit backups from
  `20260921T162819Z`.

Live evidence:

| Check | Result |
|---|---|
| Git-clean manifest audit | PASS — 70 include, 169 exclude, 1226 unrelated, 68 required-when-present, 0 unclassified |
| Startup reconciliation | PASS — all 70 entries published as `indexed`; 0 pending |
| Live Chroma inventory | PASS — 1,115 `repository_knowledge_v1` units across exactly 70 paths |
| Identity binding | PASS — every live unit binds merged commit `dc79eeb` and manifest SHA `a376c6c9…` |
| Public vector retrieval | PASS — `ARCHITECTURE openclaw watch coverage` returned the runtime-main architecture as `repository-knowledge` |
| Exclusion control | PASS — zero active repository-knowledge rows map to an excluded manifest path |
| Governance/authority non-bypass | PASS — all captured before/after hashes are identical |
| Service health | PASS — enabled, active/running, exact effective resource limits; observed startup peak about 466 MiB |

The live activation superseded one legacy unmanaged watcher process after its
PID lock correctly prevented overlap. The systemd-managed service then
completed startup reconciliation without rollback.

## Resource measurements

| Item | Value |
|---|---|
| Real watcher E2E wall | 12.96s for one mutation run plus one fresh-data-root reproduction |
| RK unit+E2E wall | 29.19s including real watcher and writer scan |
| RK unit+E2E max RSS | not captured; `/usr/bin/time` is unavailable in this environment |
| Fixture files/bytes | 14 files, 1243 bytes |
| Temporary disk | pytest tempdirs only; no live chroma/config |
| Hermetic RSS utility | none applicable; used `resource.getrusage` |

## Post-activation implications — 2026-09-24

The live service and the repository branch intentionally move at different
speeds. The service reads a dedicated clean worktree pinned at `dc79eeb`; normal
development advanced through `81efa35` via OpenClaw planning PR
`#327`, the later opt-in guardrails PR `#329`, and Claude smoke-retirement PR
`#330`, followed by watch circuit-breaker PR `#328`; routing PR `#332` then
advanced `main` to `afedc54`. Auditing the OpenClaw
planning tip before promotion failed closed on exactly five unclassified
planning files.
A full entry-hash comparison also found stale hashes for `AGENTS.md` and
`config/agent-protocol.md`; integrating `#329` added two new, out-of-W0 guardrail
documents that are explicitly classified as unrelated, while integrating
`#330` retired three unrelated smoke-harness paths. PR `#328` added two
out-of-W0 circuit-breaker tests and changed three already-admitted maintenance
files. Closure PR `#331` reconciled those path changes and current admitted-file
hashes and merged as `2e50ec3`, restoring a zero-unclassified, byte-exact audit
on `main` without changing the live checkout.

Operational implications:

- **The runtime worktree is a deployment fence.** A merge to repository `main`
  does not by itself change the live watch corpus. This prevents partial or
  unreviewed adoption, but every promotion needs an explicit clean commit,
  matching manifest hashes, and a separate runtime authorization.
- **Manifest and admitted bytes are one release unit.** Adding or changing a
  watched file without updating its exact hash makes audit or indexing refuse
  the tree. Later `main` changes demonstrated that this guard works; the process
  gap was allowing admitted files to land without the companion manifest update.
- **Repository knowledge is not OpenClaw activation.** The five newly admitted
  files are documentary guidance only. They do not install or configure
  OpenClaw, expose the ConvMem connector, enable transcript capture, or make
  the separate partial implementation acceptable.
- **Retrieved text remains non-authoritative.** Units retain claimed,
  untrusted documentary provenance. Decision-shaped text is inert and cannot
  propose, approve, publish, or mutate governance state.
- **Capture is eventually consistent.** A file changing during indexing is
  skipped and retried after debounce. That protects exact-source identity but
  means an active transcript or rapidly changing file is not guaranteed to be
  searchable immediately.
- **Memory is bounded, not proven solved.** The first systemd run lasted 2d 14h
  49m with a 1.8 GiB peak and no service failure. A clean local `systemctl`
  stop ended it at 04:34 CDT on 2026-09-24 while Switchboard verification was
  active. After that lane finished, the already-authorized unit was enabled and
  restarted at 05:14 CDT from the unchanged `dc79eeb` runtime. Its first
  debounce/reconciliation cycle completed with no warning or restart and a
  roughly 470 MiB peak. The effective limits remain `MemoryHigh=3G`,
  `MemoryMax=4G`, and `MemorySwapMax=0`. This evidence does not close the
  separate watcher/OOM work or justify admitting live databases.
- **Future T0–T5 landing is deliberately coupled to coverage maintenance.**
  Sixty-six required-when-present implementation/Gate W paths remain absent.
  Their accepted landing must include classifications and exact hashes in the
  same reviewed commit, followed by a separately authorized runtime promotion
  and repeated retrieval, exclusion, governance, and service-health checks.

Ownership remains split: the OpenClaw arc owns implementation and acceptance;
this watch arc owns the closed inventory and promotion evidence; Ryan owns
merge and live-runtime authorization.

## Deferred required_when_present paths

The manifest retains 68 exact required-when-present paths. Two reviewed planning
paths are now present and classified; 66 implementation/Gate W paths remain
absent, including T0–T5 modules/tests/fixtures/schemas, connector files, and
prospective Gate W `governed_admission.py` plus admission schemas. The full
list is in the manifest `required_when_present` array.

## Verdict

- `IMPLEMENTATION`: PASS (A1–A12 and focused regression suite)
- `REVIEW`: PASS — targeted Bugbot re-review found no remaining findings at `324ab174b33916332563c90c285166d0a6b9fa03`
- `LIVE_WATCH`: PASS
- `WATCH_COVERAGE`: BLOCKED on 66 absent `required_when_present` OpenClaw
  T0–T5/Gate W paths and a later separately authorized runtime promotion
- `CURRENT_OPENCLAW_PLAN_BYTES`: CLASSIFIED ON `main` BY PR `#331`; NOT YET
  PROMOTED
