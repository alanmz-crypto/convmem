# Implementation Handoff: R2b inventory rebind for the watch/index correctives

**Date:** 2026-09-17
**Author:** Claude (discovery + diagnosis; author of the change being attested)
**For:** Cursor (implementation) → Kiro (review)
**Authorization:** Ryan, 2026-09-17 (verbal: "give me a handoff for the next step")

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` |
| **Branch** | `fix/2026-09-17-watch-skip-hash-parity` (exists, pushed) |
| **Tip SHA** | `a544493` |
| **Push status** | `pushed to origin` |
| **PR** | `not opened` |
| **Ryan GATE** | **Yes.** Regenerating the R2b authority-content digest so it matches code written in the same session is self-attestation. Ryan authorizes; a lane other than the author performs it. |
| **Track A ingest** | Not possible — no Claude adapter exists (see companion handoff). |

---

## What to build

Rebind one R2b route coordinate and regenerate the committed writer-coverage
inventory, so `fix/2026-09-17-watch-skip-hash-parity` returns to `main`'s test
baseline and can go to PR.

**Why this exists:** the branch carries three verified correctives (watch
re-spawn loop, `index --file` silent success, provider fail-fast). It is **red**
purely because R2b binds a content digest over governed modules — editing
`ingest.py` or `convmem.py` at all invalidates it. No logic regression is
involved.

| Scope | Failed | Passed |
|---|---|---|
| Branch `a544493`, full suite | **53** | 2483 |
| `main`, the 9 affected files | **2** | 108 |
| Branch `d4056e4` (watch fix alone), those 9 files | 7 | 103 |

The 2 on `main` are pre-existing and out of scope:
`test_static_scan_matches_inventory_routing` and
`test_static_scan_zero_legacy_production_factory_calls`.

---

## Integration point

`eval_corpus/r2b_v2/coverage/inventory.py:90`, inside the `_STATIC_ROUTES`
table entry whose `entrypoint` is `convmem.py:index_command`:

```python
"governed_mutation_sinks": ("convmem.py:640",),   # -> ("convmem.py:655",)
```

---

## Specification

### Inputs

- Branch `fix/2026-09-17-watch-skip-hash-parity` at `a544493`, clean tree.
- No config, env, or credential is involved. Nothing touches the live corpus.

### Why the coordinate moved

The loud-failure commit (`38421fc`) inserted 15 lines into `convmem.py`'s
`index` command, above the governed sink. The sink itself is unchanged —
verified byte-identical:

```
main   convmem.py:640  store = ChromaStore(str(cfg["index"]["chroma_dir"]), mutation_sink=None)
branch convmem.py:655  store = ChromaStore(str(cfg["index"]["chroma_dir"]), mutation_sink=None)
```

Confirm this still holds before editing — if further commits land on the
branch, re-derive the line number rather than trusting `655`:

```bash
grep -n 'ChromaStore(str(cfg\["index"\]\["chroma_dir"\]), mutation_sink=None)' convmem.py
```

### Algorithm / behavior

```
1. Verify the sink line number (grep above). Use what it reports, not 655.
2. Edit inventory.py:90 -> ("convmem.py:<line>",)
3. Regenerate the committed artifact:
     python3 -c "import sys; sys.path.insert(0,'.'); \
       from eval_corpus.r2b_v2.coverage.inventory import write_v2_inventory_file; \
       print(write_v2_inventory_file())"
4. Confirm convergence:
     resolve_r2b_implementation_revision() == load_v2_implementation_tip()
5. Re-run the nine affected test files.
```

### Digest values (measured at `a544493` — recompute, do not trust these)

```
committed in artifact   : d04c2f4daa2a71862666fee0b55255cfe8142b7b   (inherited from main)
computed from this tree : 7e1dd72e255476418db7b5653818621749daae4e
```

`resolve_r2b_implementation_revision()` (`inventory.py:293`) is a SHA-256 over
the authority-content manifest — governed writer, proof, lease and
route-entrypoint modules plus their transitive local dependency closure. It is
**not** repo `HEAD`. Any further edit to a governed module changes it again, so
step 3 must be the last action before commit.

### Output / contract

- `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` rewritten, `code_revision`
  equal to the value computed in step 4.
- `eval_corpus/r2b_v2/coverage/inventory.py` — exactly one changed line.
- No other file modified.

---

## What NOT to build

- **Do not change `ingest.py` or `convmem.py`.** Their behavior is reviewed and
  verified in production; touching them re-invalidates the digest.
- **Do not fix the two pre-existing `main` failures.** Out of scope; they
  predate this branch.
- **Do not suppress, skip, xfail or weaken any R2b test** to make the branch
  green. If the rebind does not restore the baseline, stop and report.
- **Do not add routes, sinks or categories** to `_STATIC_ROUTES`. One coordinate
  changes; nothing else.
- **Do not merge, and do not open the PR before Kiro review.**
- **Do not touch Arc Codex** (`incremental_jsonl*.py`) or the live watcher
  config.

---

## Test expectations

Run exactly these nine, which are the full failing set:

```bash
python3 -m pytest \
  tests/test_r2b_v2_authority_boundary_iv.py \
  tests/test_r2b_v2_authority_boundary_v.py \
  tests/test_r2b_v2_contract.py \
  tests/test_r2b_v2_corrective.py \
  tests/test_r2b_v2_corrective_viii.py \
  tests/test_r2b_v2_coverage.py \
  tests/test_r2b_v2_implementation_revision.py \
  tests/test_shadow_writer_coverage_scan.py \
  tests/test_shadow_writer_gate_c3.py -q --tb=short
```

1. **Baseline restored:** `2 failed, 108 passed` — the same two that fail on
   `main`, no others.
2. **Coordinate drift cleared:** `test_static_inventory_binds_revision` reports
   no `unlisted direct ChromaStore ctor sites`, `stale governed sinks`, or
   `undocumented mutation sink sites` for route `convmem_cli_index`.
3. **Identity converged:** `test_committed_inventory_matches_authority_content_identity`
   passes.
4. **Negative control intact:** `test_stale_governed_content_fails_committed_inventory`
   still fails a zeroed revision — the gate must still be able to say no.
5. **Correctives unaffected:** `tests/test_index_loud_failures.py` and
   `tests/test_watch_skip.py` stay green (8 and 67 respectively).

Then one full-suite run before PR. Do not certify the branch from the nine
files alone — that shortcut is what produced the mis-certification this
handoff is correcting.

---

## Acceptance criteria

- [ ] Sink line number re-derived from the branch, not copied from this doc
- [ ] Exactly one line changed in `eval_corpus/r2b_v2/coverage/inventory.py`
- [ ] `R2B-V2-WRITER-COVERAGE-INVENTORY.json` regenerated, digests converge
- [ ] Nine files at `2 failed, 108 passed`
- [ ] Full suite run, and the delta against a `main` full-suite run is zero.
      **`main`'s full-suite baseline was never measured** — only the nine
      files were (`2 failed, 108 passed`). The implementing lane must
      produce that baseline itself (~23 min) rather than assume one
      exists. A branch-only full-suite run cannot distinguish "restored"
      from "still broken elsewhere".
- [ ] Ruff / pylint clean per repo gates
- [ ] Kiro reviews the exact pushed tip before any PR
- [ ] No R2b test suppressed, skipped or weakened

---

## Branch convention

Continue on the existing `fix/2026-09-17-watch-skip-hash-parity`. Do **not**
open a second branch; the correctives and their attestation belong in one
reviewable change. Push immediately after the commit.

---

## Precedent (this is routine maintenance, not a gate breach)

`docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` is regenerated alongside
governed-module changes as a matter of course:

| Commit | Subject |
|---|---|
| `d14f8a6` | Wire Claude Code into convmem as a protocol surface (#304) |
| `ef4a7dd` | Keep brief refresh bounded during exposure checks (#305) |
| `5c103aa` | Keep brief refresh memory bounded during transcript indexing (#303) |
| `a91bb28` | Bound export compaction memory without risking partial rewrites (#302) |
| `8983a6f` | Add a live-safe exact-resource JSONL production canary (#301) |

What is *not* routine is the author of a change regenerating the digest that
attests to it. That separation is the only reason this is a handoff rather than
a commit.

---

## Related files

| What | Path |
|------|------|
| Route table to edit | `eval_corpus/r2b_v2/coverage/inventory.py:90` |
| Revision function | `eval_corpus/r2b_v2/coverage/inventory.py:293` |
| Regeneration entry point | `eval_corpus/r2b_v2/coverage/inventory.py:592` |
| Committed artifact | `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` |
| Arc brief | `docs/plans/STATUS-r2b-capture-auth.md` |
| Companion handoff (separate work) | `CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` points here as the next step
- [ ] `STATUS-r2b-capture-auth.md` Update Log — **leave to the implementing
      lane**; the author should not write the arc's attestation record
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Read this file before first edit
- [ ] Confirm Ryan cleared the GATE above
- [ ] `convmem work resume fix/2026-09-17-watch-skip-hash-parity`
- [ ] State Goal / role / system state / next action per the R2b arc brief
