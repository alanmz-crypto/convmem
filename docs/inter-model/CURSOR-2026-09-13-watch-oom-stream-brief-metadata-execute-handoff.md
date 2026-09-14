# Implementation Handoff: Bounded brief metadata reads (C0–C7)

**Arc:** Trapdoor Hunt (issue #268 operational follow-up; does not reopen closed
provenance T3)

**Date:** 2026-09-13  
**Author:** Ryan authorization via Cursor (planning lane)  
**For:** Cursor Execute — **fresh implementation chat and fresh worktree only**  
**Authorization:** Ryan, 2026-09-13 — Execute C0–C7 against plan tip
`7bffdfd047648c6f1523cc4b3a1447656149ed56`

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `READY_FOR_PR` |
| **Authorization tip SHA** | `b7882b89b2b413372d561266abe2006f7f581b62` |
| **Plan tip SHA** | `7bffdfd047648c6f1523cc4b3a1447656149ed56` |
| **Runtime baseline** | `a91bb28b97aa038fde0d14caeee1b7f75b3ae094` (PR #302 merged; code state at authorization tip) |
| **Branch** | `impl/2026-09-13-watch-oom-stream-brief-metadata` |
| **Worktree** | `/home/lauer/Projects/convmem-watch-oom-brief-metadata` |
| **Push status** | push this commit immediately |
| **PR** | `not opened` — stop after pushed evidence for Copilot audit |
| **Ryan GATE** | none — Execute complete; Copilot then Kiro |
| **Track A ingest** | this session's Cursor agent transcript at handoff |

---

## What to build

Replace the brief's repeated full Chroma metadata scans with one projected
streaming read and bounded in-memory aggregates so a small watched transcript
can no longer trigger a corpus-sized brief refresh that loads ~0.98 GiB of unused
`provenance_envelope` strings. Preserve the existing brief payload, rendering,
CLI, and MCP contracts byte-for-byte on the golden oracle.

**Why this exists:** PR #302 removed export-compactor whole-export RAM, but
issue #268 recurrence still OOM-killed watch children at ~12.5 GiB RSS on
5.8–9.7 MiB Codex transcripts. Phase profiling isolated the next floor:
`collection_metadata_rows()` + repeated brief scans + `ReadonlyUnitStore` +
ledger cache retain full metadata including duplicated provenance envelopes.

---

## Normative plan (read first)

| What | Path |
|------|------|
| Execution plan (authoritative C0–C7) | `docs/plans/EXECUTION-watch-oom-stream-brief-metadata.md` @ plan tip `7bffdfd` |
| Plan branch (docs only) | `plan/2026-09-13-watch-oom-stream-brief-metadata` |
| Issue | #268 (operational; not T3 reopen) |

Kiro conditionally PASSed the projected single-pass design; Codex pinned the
exact projection union (including `rationale`); Kiro's targeted recheck folded
that scalar in. Ryan now authorizes Execute — do not re-plan.

---

## Worktree setup (mandatory)

Use a **fresh** worktree — do not implement in the planning checkout or any
Arc Codex / P2 corrective tree. Start from the **authorization tip** so the
approved plan and this handoff are present on disk. Runtime code matches PR
#302 (`a91bb28`); only docs differ from that baseline.

```bash
cd ~/Projects/convmem
git fetch origin
git worktree add -b impl/2026-09-13-watch-oom-stream-brief-metadata \
  ~/Projects/convmem-watch-oom-brief-metadata \
  origin/docs/2026-09-13-2026-09-13-watch-oom-brief-execute-auth
cd ~/Projects/convmem-watch-oom-brief-metadata
convmem doctor
```

Do not start from `origin/main` alone — that omits
`EXECUTION-watch-oom-stream-brief-metadata.md` and this handoff. Do not edit
on `main`.

---

## Integration points

| Surface | Location | Role |
|---------|----------|------|
| Streaming iterator | `chroma_readonly.py` ~34–76 | Add `iter_collection_metadata_rows()`; keep `collection_metadata_rows()` as list wrapper |
| Brief aggregation | `brief.py` ~139–146, ~270, ~418, ~520–544 | Replace repeated scans + `ReadonlyUnitStore` with one projected pass |
| Ledger graph | `ledger.py` ~364–393 | Extract metadata-iterable helpers; preserve store APIs |
| Unresolved | `unresolved.py` | Metadata-iterable path for brief; no `_LEDGER_INDEX_CACHE` mutation during brief |

Current hot path (to replace):

```139:146:brief.py
def _recent_decisions(chroma_dir: str | Path, *, limit: int = 5) -> list[dict]:
    decisions = [
        meta
        for meta in collection_metadata_rows(chroma_dir, "knowledge_units")
        if str(meta.get("ledger_kind") or "").strip().lower() == "decision"
    ]
```

```536:544:brief.py
    try:
        from chroma_readonly import open_readonly_unit_store
        from unresolved import list_unresolved

        store = open_readonly_unit_store(chroma_dir)
        ur_list = list_unresolved(store)
        unresolved_count = len(ur_list)
```

---

## Specification — pinned projection union

Exact metadata fields (no additions without returning to Kiro):

```text
id, ledger_id, ledger_kind, type, relates_to, timestamp, result,
verification_result, severity, site, domain, title, summary, rationale, tool,
source_path, superseded, deleted, document
```

**Forbidden in brief path:** `provenance_envelope`, `provenance_commitment`,
`provenance_assertion_id`. Do not call `filter_superseded_decisions()` or
`provenance_identity()` from the brief aggregate.

**Lifecycle filter:** exclude row only when `superseded is True` (current
semantics). `deleted` is projected but not a new brief exclusion rule.

**Iterator contract:** SQLite URI `mode=ro`; no `fetchall()`; no Chroma client;
cursor closed on exhaustion/exception/early close; full-mode parity with existing
`collection_metadata_rows()`.

**Memory acceptance (C6):** peak RSS < **384 MiB** on 5k/20k/58,825 fixtures;
58,825 run ≤ **160 MiB above import baseline**; envelope 2 KiB→32 KiB delta ≤
**32 MiB**; normalized payload + rendered brief match C0 golden oracle.

**Hermetic boundary (C5):** path-denial hooks before import; temporary
`write_brief(..., out_path=...)` only; temporary config alone is insufficient.

---

## Cursor implementation sequence (C0–C7)

Implement exactly the sequence in
`EXECUTION-watch-oom-stream-brief-metadata.md` §7:

| Step | Deliverable |
|------|-------------|
| **C0** | Deterministic Chroma fixture + golden normalized payload/render oracle (record tie-break: embedding id ascending) |
| **C1** | `iter_collection_metadata_rows()` + compatibility wrapper + readonly/cleanup tests |
| **C2** | Metadata-iterable ledger/unresolved helpers; store APIs delegate |
| **C3** | Single-pass brief aggregate; remove brief's `ReadonlyUnitStore` and repeated unprojected scans |
| **C4** | Adversarial/fail-soft tests; projection trap; no cache mutation |
| **C5** | Hermetic boundary tests with path-denial hooks |
| **C6** | Subprocess memory curve 5k/20k/58,825 + parity vs C0 oracle |
| **C7** | Focused + regression suites; refresh governed inventories/hashes; compileall, diff --check, pylint; commit, push, **stop — no PR** |

---

## What NOT to build

- No provenance representation, commitment, or storage dedup changes
- No Chroma/HNSW migration, rewrite, or metadata compaction
- No watcher/systemd/config/exclusion changes or source re-inclusion
- No live Chroma, live brief, production profiling, or provider/network access
- No Arc Codex Gate 0, P2 grant, digest, live P2, or activation
- No PR open — stop at pushed tip for Copilot targeted safety/evidence audit
- Do not claim full issue #268 closure (residual Chroma/model/thread caveat remains)

---

## Test expectations

Add/extend tests under `tests/test_chroma_readonly.py`, `tests/test_brief.py`,
`tests/test_ledger.py`, `tests/test_unresolved*.py`, and a dedicated hermetic
memory worker module as the plan specifies. Minimum proof classes:

1. **Projection trap:** forbidden provenance keys absent from brief path rows
2. **Golden parity:** C0 fixture payload + rendered brief match pre-refactor oracle
3. **No retention:** brief path does not construct `ReadonlyUnitStore` or mutate `_LEDGER_INDEX_CACHE`
4. **Read-only SQLite:** no WAL/SHM; mtime/canary unchanged on hermetic Chroma
5. **Memory curve:** 5k/20k/58,825 subprocess RSS under ceilings
6. **Fail-soft:** iterator failure leaves prior brief byte-identical; unresolved `None` on error

---

## Acceptance criteria

- [x] C0–C7 complete on branch `impl/2026-09-13-watch-oom-stream-brief-metadata`
- [x] Fresh worktree used; no production paths opened in tests/workers
- [x] Brief public contract unchanged on golden oracle (including `rationale`)
- [x] Memory evidence recorded in commit message or attached evidence file
- [x] Focused + repository regression suites green; pylint gates pass
- [x] Code-derived writer inventories / baseline hashes refreshed honestly if touched
- [x] Branch pushed to `origin`; resume state updated to `READY_FOR_PR` or evidence-ready stop
- [x] **No PR opened** — await Copilot audit, then Kiro implementation review

---

## Delivery gate order (after your stop)

1. GitHub Copilot audit lane — targeted safety/evidence audit on exact pushed tip
2. Kiro — implementation design review after Copilot PASS
3. Ryan — PR + squash-merge disposition
4. Post-merge hermetic end-to-end memory diagnostic before watcher/P2 reconsideration

---

## Related files

| What | Path |
|------|------|
| Execution plan | `docs/plans/EXECUTION-watch-oom-stream-brief-metadata.md` |
| Prior OOM recurrence triage | `docs/inter-model/KIRO-2026-09-12-arc-codex-watch-oom-recurrence-handoff.md` |
| Export compactor fix (merged) | PR #302 @ `a91bb28` |
| Trapdoor T3 STATUS (closed; reference) | `docs/plans/STATUS-dependability-provenance.md` |

---

## Leaving / picking up checklist

**Implementer (picking up):**

- [ ] Read this file and the execution plan before first edit
- [ ] Create fresh worktree per setup above
- [ ] State **Arc: Trapdoor Hunt** and Goal/role/system/next in first response
- [ ] Push after every commit; stop at C7 without opening PR
- [ ] Track A: index this session transcript at handoff

---

## TL;DR

**Arc Trapdoor Hunt:** Cursor Execute C0–C7 is complete on
`impl/2026-09-13-watch-oom-stream-brief-metadata` from authorization tip
`b7882b8`. One projected streaming scan preserves the brief contract including
`rationale`. Hermetic RSS 5k/20k/58,825 = 102.3/118.7/156.1 MiB peak. Next:
Copilot targeted audit on the pushed tip — no PR.
