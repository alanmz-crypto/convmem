# EXECUTION — OpenClaw maintenance watch coverage

**Arc: OpenClaw Watch Coverage** · **State: KIRO PASS at `19dea97`; W0–W6
EXECUTE AUTHORIZED** · **Date: 2026-09-21**

Companion:
[ARCHITECTURE-openclaw-watch-coverage.md](ARCHITECTURE-openclaw-watch-coverage.md).
This plan implements only safe repository-knowledge watch coverage. It does not
implement the OpenClaw reader or change its approved T0–T5 plan.

## 1. Frozen implementation surface

Cursor may edit only the following tracked paths after Ryan grants an exact
reviewed-plan SHA:

```text
adapters/detect.py
adapters/repository_knowledge.py
config.example.toml
config/repository-knowledge/openclaw-watch-scope-v1.json
config/repository-knowledge/openclaw-watch-scope-v1.schema.json
ingest.py
repository_knowledge_index.py
repository_knowledge_scope.py
repository_knowledge_sync.py
watch.py
tests/fixtures/repository_knowledge/**
tests/test_openclaw_watch_coverage.py
tests/test_repository_knowledge_adapter.py
tests/test_repository_knowledge_scope.py
tests/test_repository_knowledge_sync.py
docs/plans/STATUS-openclaw-watch-coverage.md
docs/plans/VERIFY-openclaw-watch-coverage.md
```

The implementation may update the exact manifest hashes/classifications as
part of W0. It may not edit any OpenClaw T0–T5 module, connector, fixture,
schema, test, architecture, or execution plan. A required edit outside this
list is a contract defect and returns to Codex/Kiro.

No new runtime dependency is allowed. Use the standard library, existing
`watchdog`, existing embedding/Chroma paths, and existing Git executable used
by repository tooling. No network or provider call is allowed in tests.

## 2. Ordered slices

### W0 — Materialize and audit the exact inventory

Create the schema and manifest from the complete tracked tree, using `.` as the
single coverage root. The manifest
must contain exact entries for all current combined-system maintenance files
and `required_when_present` records for every exact T0–T5 path named by the
Kiro-approved plans. Each coverage root must classify every tracked file.

Minimum current inclusions:

- this arc's architecture, execution, and status documents;
- `config.example.toml`, `config/agent-protocol.md`, and `AGENTS.md`;
- `convmem.py`, `config.py`, `watch.py`, `ingest.py`,
  `source_reconciler.py`, `adapters/detect.py`,
  `adapters/inter_model_doc.py`, `inter_model_index.py`,
  `chroma_write_store.py`, `provenance.py`, `provenance_binding.py`,
  `propose_decision.py`, and `observe.py`;
- `tests/test_watch.py`, `tests/test_watch_skip.py`,
  `tests/test_inter_model_doc.py`, `tests/test_provenance.py`,
  `tests/test_provenance_continuity.py`, and every current governed-writer
  safety test selected by the manifest audit;
- `docs/MODEL-WORKFLOW.md`, `docs/CODEX-DEEPSEEK-VERIFY.md`,
  `docs/RECOVER.md`, `docs/MILESTONE-F.md`, Git hygiene and always-available
  fallback plans, the watch incremental architecture/invariants/execution
  plans, and the four architecture/planning builder digests named in the
  requirement; and
- the repository-knowledge schema and later VERIFY document.

The exact approved OpenClaw architecture and execution documents at
`cd9d2698b7423f907b552bc9118a0af523018ca9`, the bounded actualization brief,
T0–T5 files, and prospective Gate W files such as `governed_admission.py`
become active entries only when the same reviewed bytes exist in the target
checkout. Until then, the audit reports them as
`required_when_present`, not covered. It must never copy their `/tmp` or
worktree versions into the watched checkout.

Generate a human-readable inventory table into the VERIFY document from an
independent manifest reader. The manifest is the machine authority; the table
is review evidence, not a second source of truth.

**Exit:** schema validation passes; no path is unclassified; all included
files are tracked, clean, regular, within root, and hash-matched; every
mandatory exclusion has an explicit rule and fixture.

### W1 — Scope and byte-authority module

Implement `repository_knowledge_scope.py` as the only module that loads,
validates, resolves, and classifies repository knowledge. Implement the closed
schema contract with the Python standard library; do not import an ambient
`jsonschema` installation. It must expose
side-effect-free operations for:

- manifest/schema validation;
- exact path lookup and exclusion-first classification;
- complete coverage-root audit against `git ls-files`;
- current `HEAD`, index, working-tree, path, and SHA-256 validation;
- closed parser/resource/sensitivity policies; and
- prior-source identity validation for retirement.

It must also expose the exact cached `outside|eligible|blocked` classification
contract consumed first by `adapters.detect.detect_format()`. Manifest or Git
validation failure for a path beneath a configured root returns `blocked`,
never `outside`. All path comparisons use resolved absolute paths plus the
original repo-relative path. Reject symlinks at any component, nested worktrees, `.git`,
case collisions, traversal, aliases, missing files, and a manifest outside its
own checkout. Git commands use argv arrays, fixed cwd, closed stdin, bounded
output/time, and no shell.

**Exit:** table-driven tests cover every accept/refuse reason, including dirty
staged and unstaged changes and identical bytes in a duplicate checkout.

### W2 — Deterministic adapter and documentary indexer

Implement the six content-class chunkers and wire the exact detection order:
call the W1 classifier first; map `eligible` to `repository_knowledge_v1`, map
`blocked` to `repository_knowledge_blocked` with parser `None`, and run the
existing detector body only for `outside`. A path beneath a configured
repository root that is not eligible therefore stops before every
transcript/JSON/SQLite detector. Manual `index --file` and watch use the same
order.

Implement `repository_knowledge_index.py` using exact chunks, deterministic
content-addressed unit IDs, current provenance helpers, and the existing
production writer session. It creates no summaries and uses the existing
source-scoped snapshot/revalidate/prune path for updates. It must return the
complete unit-ID keep set to `ingest.py`.

No parser executes input, resolves imports, follows links, expands templates,
loads external schemas, or asks an LLM to summarize. Embeddings are the only
model boundary; tests replace them with deterministic local vectors.

**Exit:** exact chunk/parity fixtures for Markdown, Python, JSON, JS/MJS, TOML,
and text; invalid and oversized inputs refuse atomically; stored metadata and
provenance match the architecture; changed content replaces only its own
source generation.

### W3 — Watch routing, startup sync, and retirement

Add the `repository_knowledge_manifests` watch setting. `watch.py` appends the
validated repository roots to the existing observer-root set and keeps one
handler, one raw batch, one debounce scheduler, and the sequential flush loop.
Before `is_watchable()`, `_drain_batch()` maps an exact configured manifest path
to a reconciliation control token; every other event uses W2's root-aware
detector. Overlapping observer registrations are allowed, but resolved-path
batch deduplication must collapse them before classification and child dispatch.
Keep the current subprocess, timeout, memory scope, lock, and one-child
behavior.

Implement startup/manifest reconciliation in
`repository_knowledge_sync.py`. It validates the whole manifest before
dispatch, compares a dedicated derived sync-state snapshot, and invokes the
same public CLI argv used by current watch:

```text
<python> <repo>/convmem.py index --file <absolute-eligible-file>
```

Poll only configured manifest identities every 30 seconds so a manifest event
that arrived before `git commit` is retried after the checkout becomes clean;
do not poll or parse repository content. Index changed entries in stable
repo-relative order. A child failure leaves
that and later entries pending. Revalidate identity after each child. Add the
closed, idempotent retirement path exactly as designed; it may supersede only
matching `repository_knowledge_v1` rows through the existing authorized
writer.

**Exit:** startup indexes preexisting eligible files; one committed manifest
change causes one bounded reconciliation; a dirty/unlisted event causes zero
child dispatches; a transcript-shaped in-scope file cannot reach a legacy
parser; overlapping roots yield one repository dispatch; retirement cannot
touch another source/type.

### W4 — Isolated end-to-end acceptance harness

Build `tests/test_openclaw_watch_coverage.py` around a disposable Git repo and
disposable ConvMem data/config root. Use the real watchdog handler, debounce,
subprocess argv boundary, ingest routing, Chroma writer, processed state, and
normal query/retrieval path. Replace only embedding/provider computation with
a deterministic fake and deny network.

Run the positive sequence in Architecture §6 for every content class. The
folder-add case must prove:

```text
absent before config/manifest addition
→ observer attached
→ eligible event/startup reconciliation
→ index --file child
→ processed + Chroma derived mutation
→ normal retrieval returns exact nonce and provenance
```

Run all negative controls and the independent governance before/after hashes.
Record event, debounce, child-dispatch, indexed-unit, rejection, retrieval,
and mutation counts. Repeat in a fresh root.

**Exit:** two independent isolated runs pass; no expected value is derived by
calling the implementation under test on both sides of an assertion.

### W5 — Regression, inventory, and resource verification

Run at minimum:

```bash
pytest -q \
  tests/test_repository_knowledge_scope.py \
  tests/test_repository_knowledge_adapter.py \
  tests/test_repository_knowledge_sync.py \
  tests/test_openclaw_watch_coverage.py \
  tests/test_watch.py \
  tests/test_watch_skip.py \
  tests/test_inter_model_doc.py \
  tests/test_provenance.py \
  tests/test_provenance_continuity.py
```

Also run the repository's targeted governed-writer tests selected by W0,
`python repository_knowledge_scope.py audit --manifest ABS`,
`git diff --check`, and a source scan proving the new
adapter/sync modules do not import or invoke governed proposal/admission/
publication routes. Report wall time, maximum fixture files/bytes/units, peak
RSS if the existing hermetic measurement utility supports it, and temporary
disk peak. Do not run a live corpus, full repository suite, provider/model, or
OpenClaw runtime.

**Exit:** all focused checks pass with complete commands/results in
`VERIFY-openclaw-watch-coverage.md`; failures remain failures rather than
scope-reducing skips.

### W6 — Review and delivery

Cursor commits and pushes after every coherent slice. The final implementation
tip receives code review under the project charter. Ryan owns PR/merge. After
merge, update STATUS as a current-state snapshot.

Live activation is a separate step and grant. W0–W6 may finish with
`IMPLEMENTATION=PASS`, `LIVE_WATCH=NOT_ACTIVATED`, and
`CURRENT_OPENCLAW_PLAN_BYTES=REQUIRED_WHEN_PRESENT` if the approved OpenClaw
plans have not landed in the watched checkout. The combined system reaches
`WATCH_COVERAGE=PASS` only after every required current OpenClaw file has
landed, the manifest hashes it, live activation is granted, startup sync
succeeds, safe retrieval needles pass, and governance hashes remain unchanged.

## 3. Mandatory acceptance matrix

| ID | Requirement | Independent evidence |
|---|---|---|
| A1 | Closed scope | Complete Git tree classification; zero unclassified paths under declared roots |
| A2 | Git-clean authority | dirty/staged/untracked/copy/symlink/path-escape controls all refuse before parse |
| A3 | Content support | retrievable Markdown, Python, test/fixture, JSON Schema, JS/MJS, TOML, operational docs |
| A4 | Folder addition | unique canary absent before, present after watch addition through one public child dispatch |
| A5 | Update | new clean commit + manifest event replaces old active source generation |
| A6 | Retirement | exact retired identity becomes superseded; unrelated/type-mismatch rows unchanged |
| A7 | Exclusions | unique markers for all mandatory exclusion classes remain unretrievable |
| A8 | Provenance | path, commit, file/manifest hash, locator, adapter version, envelope and commitment verified |
| A9 | Non-bypass | proposal, approval, ledger, receipt, authority and publication surfaces byte-identical |
| A10 | Inert instructions | proposal/approval-shaped file content creates only documentary units |
| A11 | Reproduction | second fresh root yields same inventory, unit IDs, metadata, and retrieval needles |
| A12 | Regression | existing watch/inter-model/provenance/writer tests pass unchanged |

No mocked denial is proof when the real forbidden surface can be independently
snapshotted or instrumented. No source-derived expected hash may be compared
only with another value computed by the implementation under test.

## 4. Stop conditions

Stop and return to Codex/Kiro if:

- a file outside the frozen implementation surface must change;
- `convmem.py`, `propose_decision.py`, `observe.py`, `conflict_events.py`,
  prospective `governed_admission.py`, or any Gate W call site would change;
- a dependency, content class, suffix, parser, source identity, writer route,
  retirement rule, or config field differs from this plan;
- exact OpenClaw paths cannot be derived from the approved plans without
  interpretation;
- an exclusion would need to be weakened to index a required file;
- any test touches live config/data, a real OpenClaw profile, network, provider,
  model, credential, authority, or publication state;
- an unreviewed/dirty file becomes parsable or retrievable;
- a documentary record creates stronger than claimed external provenance;
- proposal/approval/admission/capture/publication state changes; or
- acceptance needs a skipped negative control or a hand-authored summary in
  place of source retrieval.

## 5. Required implementation handoff

```text
ARC: OpenClaw Watch Coverage
REVIEWED_PLAN_SHA: <exact Kiro-reviewed SHA>
CODE_BASELINE_SHA: <exact>
IMPLEMENTATION_BRANCH: <exact>
IMPLEMENTATION_SHA: <exact>
PUSH_STATE: <remote ref and status>
CHANGED_FILES: <complete list vs baseline>
MANIFEST_SHA256: <exact>
INVENTORY: <included/excluded/unrelated/required-when-present counts>
IMPLEMENTATION: PASS | BLOCKED
WATCH_COVERAGE: PASS | BLOCKED | NOT_YET_RUN
LIVE_WATCH: NOT_ACTIVATED | <separately authorized result>
FOLDER_ADD_PROOF: <event→child→index→retrieval evidence>
UPDATE_RETIRE_PROOF: <current/superseded/unrelated evidence>
NON_BYPASS_PROOF: <before/after hashes and forbidden-call evidence>
REPRODUCTION: <two-root comparison>
TESTS: <exact commands/results/timings/resources>
DEFERRED_REQUIRED_PATHS: <exact absent paths>
BLOCKERS: <none or exact failed criterion>
```

**TL;DR [Arc OpenClaw Watch Coverage]:** W0–W6 materialize the exact safe
inventory, implement hash-pinned documentary indexing and watch reconciliation,
prove folder-to-retrieval coverage plus governance non-bypass twice in
isolation, and stop before live activation or any OpenClaw reader change.
