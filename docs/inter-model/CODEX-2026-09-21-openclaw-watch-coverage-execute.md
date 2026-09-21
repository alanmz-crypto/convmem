# Implementation Handoff: OpenClaw Watch Coverage W0–W6

**Arc:** OpenClaw Watch Coverage

**Date:** 2026-09-21

**Author:** Codex architecture lane

**For:** Cursor implementation lane

**Authorization:** Ryan, 2026-09-21 — explicit approval to move ahead with the
ConvMem watch feature after Kiro's exact-plan PASS at
`19dea97368408ee0b179c05c942306f6d8f1a2e8`

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` — W0–W6 Execute authorized |
| **Reviewed plan** | `19dea97368408ee0b179c05c942306f6d8f1a2e8` on `plan/2026-09-21-openclaw-watch-coverage` |
| **Code baseline** | `5ab03a37559a93f1b51932c57a2a2a783da3354b` |
| **Implementation branch** | Create `feat/2026-09-21-openclaw-watch-coverage` from the pushed branch containing this handoff |
| **Push status** | Handoff branch pushed; Cursor pushes every implementation commit with an explicit refspec |
| **PR** | Not opened; Ryan separately decides PR creation and merge |
| **Ryan GATE** | None for W0–W6 implementation and isolated acceptance; live config, restart, activation, PR, and merge remain gated |

## What to build

Implement the reviewed maintenance-knowledge plane: an exact hash-pinned
repository inventory, exclusion-first byte authority, deterministic
repository-content adapter, normal documentary indexing, watch/startup
reconciliation, safe source retirement, and two-run isolated acceptance.

**Why this exists:** ConvMem currently observes some relevant folders but
cannot parse and retrieve most plans, code, tests, schemas, JavaScript, TOML,
or operational documentation. Future maintainers should retrieve the current
safe repository knowledge without Ryan manually attaching files.

## Normative specification and order

Read completely before editing:

1. `docs/plans/STATUS-openclaw-watch-coverage.md`
2. `docs/plans/ARCHITECTURE-openclaw-watch-coverage.md`
3. `docs/plans/EXECUTION-openclaw-watch-coverage.md`
4. this handoff

The architecture and execution contract at reviewed SHA `19dea97` are
normative. Execute W0 through W6 in order:

1. W0 materializes and audits the exact inventory.
2. W1 implements scope, schema, Git-clean bytes, and tri-state classification.
3. W2 implements deterministic chunking and documentary indexing.
4. W3 adds manifest-driven watch routing, startup reconciliation, and exact
   retirement.
5. W4 proves event-to-index-to-retrieval behavior and governance non-bypass in
   two disposable roots.
6. W5 runs the focused regression, inventory, and resource checks.
7. W6 freezes VERIFY evidence, commits, pushes, and stops for review.

If implementation requires a different file, dependency, parser/content
class, source identity, writer route, retirement rule, config field, or
acceptance condition, stop and return to Codex/Kiro. Do not redesign in code.

## Frozen scope

The exact `docs/plans/EXECUTION-openclaw-watch-coverage.md` §1 allowlist is the
complete edit grant. It permits the repository-knowledge modules, narrow
`watch.py`/`ingest.py`/detector/config seams, exact manifest/schema, focused
fixtures/tests, VERIFY, STATUS, and implementation handoff only.

Do not:

- change any OpenClaw T0–T5 reader, runtime, connector, fixture, schema, test,
  architecture, or execution plan;
- edit `convmem.py`, governed proposal/admission/publication code, Gate W call
  sites, or production authority paths;
- read or mutate live corpus, config, credentials, OpenClaw profiles, memory,
  workspaces, transcripts, databases, or private authority data;
- start, stop, restart, or reconfigure the live watcher;
- add dependencies, network/provider/model calls, broad suffix admission,
  recursive parser eligibility, or an LLM summarization path;
- open a PR, merge, activate live coverage, or claim
  `WATCH_COVERAGE=PASS`.

## Test and evidence expectations

Run the exact focused command and audits in Execution §W5. Complete acceptance
A1–A12, including:

- zero unclassified tracked paths under the declared root;
- dirty, staged, untracked, duplicate-checkout, symlink, traversal, and
  exclusion refusals before parsing;
- deterministic retrieval for every approved content class;
- folder-add, update, and retirement through the normal public child route;
- exact provenance and source-scoped replacement;
- byte-identical proposal, approval, ledger, receipt, authority, and
  publication surfaces;
- inert decision-shaped document text; and
- matching results from a second fresh disposable root.

Record exact commands, counts, timings, resource measurements, rejected paths,
retrieval needles, provenance, and before/after governance hashes in
`docs/plans/VERIFY-openclaw-watch-coverage.md`. No implementation-derived
expected value may be its own independent oracle.

## Stop and hand back

When W0–W6 pass, update the STATUS snapshot and LATEST, commit and push the
exact implementation tip, and return the complete implementation handoff shape
from Execution §5. Stop for focused review. Do not open a PR or activate the
watch path.

## Related files

| What | Path |
|---|---|
| Arc snapshot | `docs/plans/STATUS-openclaw-watch-coverage.md` |
| Reviewed architecture | `docs/plans/ARCHITECTURE-openclaw-watch-coverage.md` |
| Authorized execution | `docs/plans/EXECUTION-openclaw-watch-coverage.md` |
| Required verification | `docs/plans/VERIFY-openclaw-watch-coverage.md` |

## Picking up checklist

- [ ] Run `convmem doctor`, `convmem brief --stdout-only`, and
      `convmem unresolved`.
- [ ] Read STATUS, Architecture, Execution, and this handoff completely.
- [ ] Confirm reviewed plan SHA `19dea97368408ee0b179c05c942306f6d8f1a2e8`
      and code baseline `5ab03a37559a93f1b51932c57a2a2a783da3354b`.
- [ ] State Goal / role / system state / next action and
      **Arc: OpenClaw Watch Coverage**.
- [ ] Create and push the exact feature branch before editing.
- [ ] Execute W0–W6 in order and push every commit.
- [ ] Stop at pushed VERIFY evidence for focused review.

## TL;DR

- Ryan authorized Cursor to implement and test W0–W6 against Kiro-reviewed
  plan `19dea97`.
- Work is repository-knowledge coverage only; OpenClaw T0–T5 and governed
  authority paths remain untouched.
- No live config, watch restart, corpus mutation, PR, merge, activation, or
  `WATCH_COVERAGE=PASS` claim is authorized.
