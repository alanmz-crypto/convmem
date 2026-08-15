# Review Handoff: CG-2 Architecture Implementation Feasibility

**Date:** 2026-08-14
**Author:** Kiro (design review lane)
**For:** Cursor (implementation feasibility review lane)
**Authorization:** Ryan, 2026-08-14 (verbal; sequencing confirmed after Kiro design PASS)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | Read-only review — deliverable committed on `plan/2026-08-14-cg2-production-activation` |
| **Target revision** | `1222b1ede2d6cc5da582388768f06d60b36c5e50` (this branch tip) |
| **Push status** | Target revision pushed to origin |
| **PR** | Not applicable (review artifact, not implementation) |
| **Ryan GATE** | None — Cursor may begin immediately |
| **Kiro design review** | PASS at same SHA (this session) |

---

## What to review

Assess whether the CG-2 architecture can be implemented against the code that
exists on `main` today — specifically whether the proposed boundaries, hooks,
and state machines fit the real module structure without requiring a ground-up
rewrite.

**Why this exists:** A design-correct architecture is worthless if the code on
disk can't host it without a rewrite that nobody budgeted. Cursor maps each
architectural claim to real source and reports whether the seams exist, are
partially present, or are missing entirely.

---

## Target documents

**Architecture under review (this branch):**

```bash
# Already checked out at this worktree tip:
docs/plans/ARCHITECTURE-cg2-production-activation.md
docs/plans/STATUS-cg2-production-activation.md
```

**Code to map against (`main`):**

| Module | Role in CG-2 |
|--------|--------------|
| `file_generation_contract.py` | CG-1 identity, manifests, owner digest |
| `file_generation_builder.py` | Candidate construction |
| `file_generation_store.py` | Staging, exact validation, mediated proof reads |
| `file_generation_pointer.py` | Pointer publication, recovery, qualification |
| `file_generation_validate.py` | Cold validation |
| `chroma_store.py` | Current production Chroma facade (to be wrapped) |
| `chroma_readonly.py` | Read-only Chroma operations |
| `chroma_write_store.py` | Write-side Chroma operations |
| `query.py` | Production query path (search, ask, related) |
| `ask.py` | Ask pipeline (one of four bypass sites) |
| `mcp_server.py` | MCP tool surface (related, stats bypass sites) |
| `convmem.py` | CLI entry point (search bypass site) |
| `watch.py` | Filesystem watcher / ingest trigger |
| `ingest.py` | Ingest pipeline |
| `projection_parity.py` | Current parity/drift semantics |
| `doctor.py` | Health checks |
| `tests/test_file_generation_read_path_inventory.py` | Bypass AST inventory |

---

## Review sections and acceptance checklist

### 1. §3 repository-fact claim audit

For each row in the architecture's §3 table ("Repository facts that shape
CG-2"), trace the claim to specific lines in the `main` codebase:

- [ ] `ownership_key(path)` is `source:<Path.resolve(strict=False)>` — verify in `file_generation_contract.py`
- [ ] Production code has no caller of CG-1 pointer/builder APIs — verify no production import
- [ ] Four `cg2-production-bypass` constructors classified — verify the AST inventory test is accurate and complete
- [ ] `FileGenerationStore` snapshots active map once per read and rechecks rows — verify in `file_generation_store.py`
- [ ] Hermetic store computes cosine distance in Python — verify query implementation
- [ ] `query.py` catches broad failures and uses read-only fallback — verify lines ~428, ~523
- [ ] `doctor._check_index_drift` compares raw Chroma IDs with export IDs — verify in `doctor.py`
- [ ] `projection_parity.entity_key` prefers `ledger_id` then `row["id"]` — verify in `projection_parity.py`
- [ ] Live doctor reports legacy embedding identity missing — verify the `embed_collection_identity` check

**Verdict per claim:** Confirmed / Inaccurate / Outdated (with correction)

### 2. Bypass inventory completeness

- [ ] Verify the four sites in `tests/test_file_generation_read_path_inventory.py` match reality
- [ ] Search for any additional `ChromaStore` constructor calls or direct Chroma collection access not in the inventory
- [ ] Check whether `chroma_readonly.py` or `chroma_write_store.py` have serving-path reads that bypass the proposed boundary
- [ ] Check `brief.py`, `complete_data_restore.py`, and any other modules that touch Chroma

**Verdict:** Inventory is complete / N additional sites found (list them)

### 3. Serving boundary feasibility (`ServingIndexRepository`)

The architecture proposes a single deep boundary that wraps all serving reads.
Assess:

- [ ] Can `ChromaStore` be wrapped (composed into) a repository boundary without rewriting its internals?
- [ ] Does `query.py`'s current structure allow a single injection point, or do multiple call-sites need independent wiring?
- [ ] Can the broad-exception fallback (lines ~428, ~523) be narrowed to distinguish authority failures from transient Chroma errors without a rewrite of the error handling?
- [ ] Is the `--raw` summary search path reachable from the same boundary, or does it use a separate Chroma access path?
- [ ] Does `mcp_server.py` use `query.py` or access Chroma directly?

**Verdict:** Wrappable without rewrite / Wrappable with bounded refactor (describe) / Requires rewrite (describe scope)

### 4. Ingest/watch hooks for source reconciliation

The architecture requires startup/overflow/periodic reconciliation (§7.1).
Assess:

- [ ] Does `watch.py` currently expose `IN_Q_OVERFLOW` or equivalent from its inotify/watchdog backend?
- [ ] Is there a startup hook where reconciliation could run?
- [ ] Is there a periodic/timer mechanism already, or would one need to be added?
- [ ] Can the existing ingest pipeline accept reconciliation-enqueued work through the same admission path as watcher events?
- [ ] What is the current source-hash mechanism (if any) in the ingest path?

**Verdict:** Hooks exist / Partial (describe gaps) / Major new mechanism needed

### 5. Authority-resolution integration point

The architecture proposes a request-frozen authority vector resolved at query
start (§5.1). Assess:

- [ ] Where in the current query path would resolution happen? (before Chroma call? inside ChromaStore? new layer?)
- [ ] Does the existing `FileGenerationStore.active_generation_resolver` pattern transfer to a production context?
- [ ] Can the pointer/manifest/fence evidence be read without holding a lock for the duration of a query?

**Verdict:** Clear integration point / Ambiguous (options) / Structurally blocked

---

## Deliverable

**File:** `docs/inter-model/CURSOR-2026-08-14-cg2-feasibility-review.md`
(committed on this branch or a child branch)

**Required sections:**
1. One-paragraph summary verdict: PASS / FAIL / PASS WITH RISKS
2. §3 claim-by-claim findings table
3. Bypass inventory findings
4. Serving boundary assessment
5. Ingest/watch hooks assessment
6. Authority-resolution integration assessment
7. Overall risk summary (what's easy, what's hard, what might block)
8. SHA confirmation: verdict applies to `1222b1e` only

---

## What NOT to review

- **Design correctness** — Kiro already PASSed the state machines and invariants
- **Evidence/failure plausibility** — Crush's lane (parallel)
- **Formal model** — Codex does this after feasibility + evidence PASS
- **Implementation** — no code changes, no tests, no refactoring, no execution plan
- **Worktree cleanup or CG-1 Batch 3 cherry-picks** — parked
- **Other arcs** (JudgeBench, Shadow Ledger, etc.)
- **Production activation or configuration** — not authorized

---

## Acceptance criteria

- [ ] All 5 review sections addressed with specific file:line evidence
- [ ] Each §3 claim mapped to code or flagged as inaccurate
- [ ] Bypass inventory verified complete or gaps named
- [ ] Serving boundary given a clear feasibility grade with rationale
- [ ] Ingest/watch hooks assessed with gap severity
- [ ] Verdict is PASS, FAIL, or PASS WITH RISKS — not ambiguous
- [ ] Verdict bound to exact SHA `1222b1e`
- [ ] No implementation produced (no `.py` changes, no test additions)
- [ ] Deliverable pushed

---

## Related files

| What | Path |
|------|------|
| Architecture under review | `docs/plans/ARCHITECTURE-cg2-production-activation.md` (this branch, `1222b1e`) |
| Arc brief | `docs/plans/STATUS-cg2-production-activation.md` (this branch, `1222b1e`) |
| CG-1 closure (context) | `docs/inter-model/CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md` |
| CG-1 dependability handoff | `docs/inter-model/HANDOFF-CG1-DEPENDABILITY-2026-08-10.md` |
| Bypass inventory test | `tests/test_file_generation_read_path_inventory.py` |
| Crush parallel review handoff | `docs/inter-model/KIRO-2026-08-14-cg2-crush-evidence-review-handoff.md` (on `docs/2026-08-14-cg2-crush-feasibility-handoff` branch) |
| Kiro design review | This session Track A (PASS, not separately filed) |

---

## Leaving checklist (Kiro, author)

- [x] This file committed and pushed on the plan branch
- [x] `LATEST.md` updated (on docs branch; plan branch LATEST already references CG-2 review)
- [ ] Cursor notified (Ryan relays "go")
