# convmem Review Context

Use this file as repository-specific technical context. Workflow and acceptance
policy live in `docs/planning/EXECUTE-TASK.md`; this file does not replace that
policy or the HITL team charter.

## Verification commands

Choose the commands relevant to the changed surface and report failures with
the failing command and observed output.

```bash
pytest -q
convmem doctor
```

For planning-guide changes:

```bash
pytest -q tests/test_planning_guide_contract.py
```

For cross-project digest changes:

```bash
scripts/cross-project-digest.sh --skip-ask
scripts/smoke-cross-project-digest.sh
```

For shipped-work verification, follow `docs/CODEX-DEEPSEEK-VERIFY.md` and the
task-specific smoke or evaluation command. Do not treat a passing narrow unit
test as proof that corpus, retrieval, or orchestration behavior is unchanged.

## Architectural invariants

- The append-only JSONL ledger owns durable decisions, observations, and
  verifications. Chroma is a derived search index and must remain rebuildable.
- Ingest flows one way from source material to ledger/export and derived index.
  Search or MCP adapters must not become alternate fact stores.
- `mcp_server.py` and `convmem.py` are thin surfaces. Retrieval, evidence, and
  rendering behavior belongs in the established deeper modules.
- Protocol text has one source in `config/agent-protocol.md`. Generated surface
  files must be updated through the repository generator and deploy scripts,
  not edited as independent policy forks.
- Planning guides preserve Contract v1 headings, metadata fields, and their
  explicit HITL stop. `convmem doctor` is the structural fitness check.
- The JSONL ledger and Chroma index have different retention semantics.
  Historical, superseded, and active counts need not be identical.
- A forced single-file ingest may clear and rebuild derived rows for that exact
  source. It must not clear unrelated sources or bypass supersession rules.
- Refine mutations retain their documented undo evidence. A code change must
  not weaken backup, tombstone, or approval boundaries.
- Agents do not merge, force-push, or push `main`. Task work stays on a valid,
  pushed branch, and every commit is pushed as the recovery fallback.

## False-positive boundaries

- `convmem index --file <path>` is the allowed narrow session-tracking form. It
  is distinct from an unbounded corpus index.
- Differences between active Chroma units and historical JSONL identifiers are
  not automatically corruption; compare active coverage, supersession, and
  index-drift diagnostics before reporting a defect.
- A non-fatal doctor warning is not automatically a regression. Confirm it was
  introduced or materially worsened by the change, and still report any failed
  doctor check.
- Optional or environment-owned services can be unavailable in isolated test
  environments. Distinguish an environmental limitation from changed product
  behavior using contemporaneous command evidence.
- Untracked files in a shared checkout can belong to another actor. Do not
  recommend deleting, staging, or stashing them unless ownership is established.
- Documentation examples may intentionally show placeholders such as `<sha>`
  or `<pending>`; flag them only when the artifact claims completed evidence.

These boundaries are narrow diagnostic guidance, not permission to suppress a
finding that crosses a data-loss, authorization, isolation, or correctness
boundary.

## Sensitive areas

Review changes in these areas with particular care:

- `ingest.py`, `chroma_store.py`, and refine jobs: deletion scope, source
  identity, supersession, locks, partial failure, and undo behavior.
- `query.py`, `ask.py`, `evidence.py`, and reranking: result ordering, score
  meaning, truncation order, provenance, and trace/API compatibility.
- `config/agent-protocol.md` and generation/deployment scripts: cross-surface
  consistency and accidental hand-edited drift.
- `doctor.py`, planning-contract checks, hooks, and `convmem work`: fail-closed
  behavior, correct repository detection, branch isolation, and recovery.
- Session parsers and transcript ingestion: source boundaries, secrets,
  attachments, malformed records, duplicate indexing, and source-specific IDs.
- Configuration, authentication, and external-service code: secret exposure,
  unsafe defaults, implicit network mutations, and overly broad authorization.
- Backup, restore, purge, forget, dedupe, and approval paths: exact target
  resolution, recoverability, dry-run fidelity, and human gates.
