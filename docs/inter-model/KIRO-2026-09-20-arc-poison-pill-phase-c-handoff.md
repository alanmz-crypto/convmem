# Implementation Handoff: Arc Poison Pill — Phase C′ (corrected diagnostic experiment)

**Date:** 2026-09-20
**Author:** Claude Opus 5, holding the Kiro design/plan lane (review-required; no prod code)
**For:** Cursor (execution) — **after** the Ryan platform gate clears
**Arc:** Poison Pill (`chroma-upsert-crash`)
**Supersedes the experiment design in:** `KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md`
(that document's Part A/B remediation remains valid; its root-cause premise does not)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` (platform gate) |
| **Branch** | `fix/2026-09-20-chroma-upsert-poison-pill` (pushed) |
| **Push status** | pushed |
| **PR** | not opened |
| **Ryan GATE** | platform quiet verdict required before any Phase C′ run (§ Ryan GATE) |
| **Related ledger** | `obs_a09dbfa9e237`, `obs_e8db779df8c3`, `obs_c1499a660d4f` (all three need correction — see § Ledger corrections) |

---

## Why this supersedes the earlier experiment design

Three premises the previous design rested on are contradicted by evidence already on disk.

### 1. The crash is not file-specific — "poison transcript" is refuted

`coredumpctl` shows the same SIGSEGV on inputs and programs that have nothing to do with the
40 MB transcript:

| When (CDT) | Process | Signal |
|---|---|---|
| 2026-09-20 05:56:50 | `convmem.py watch` (the watcher **parent**) | SIGABRT (SI_TKILL) |
| 2026-09-20 06:32:10 | `convmem.py index --file docs/inter-model/LATEST.md` (~11 KB) | SIGSEGV |
| 2026-09-20 07:00:02 | `convmem.py refine` (F1 daemon, not ingest) | SIGSEGV |
| 2026-09-20 07:20:32 | `convmem.py index --file …rollout-2026-09-17T23-18-39….jsonl` | SIGSEGV |

The watcher journal corroborates: `[watch] error processing …/LATEST.md: index subprocess exit -11`.

### 2. The quarantined indices are not structurally corrupt — hypothesis (c) is unsupported

Read-only forensics (no Chroma client opened; nothing written) over
`chroma.corrupt-2026-09-19`, `chroma.corrupt-2026-09-20`, and the live rebuilt `chroma`:

- Size invariants exact in every segment: 3212 B/element = 768 dims × 4 + (maxM0 32 + 1) × 4 + 8 label.
- Level-0 link counts: values above 32 are hnswlib's **delete mark** (bit `0x10000`), not corruption;
  true counts are ≤ 32 everywhere.
- **Zero** out-of-range neighbor ids, **zero** self-references, **zero** non-finite vectors.
- `link_lists.bin` walks cleanly to the exact byte end in all six segments.
- **Zero** duplicate labels; labels contiguous `1..N`.
- `index_metadata.pickle`: `total_elements_added` == element count, and `len(id_to_label)` ==
  elements − delete-marked, **exactly**, in every segment.
- SQLite `PRAGMA quick_check` = `ok` on all three stores.

Element census: corrupt-09-19 units 158,070 · corrupt-09-20 units 153,626 (73,545 delete-marked →
80,081 live) · live rebuilt units 81,575 (566 marked → 81,009).

Decisively: the live index's segment files were last written **07:18:18**, two minutes fourteen
seconds before the 07:20:32 SIGSEGV, and that on-disk state validates clean. The crash did not
require a corrupt index.

### 3. The systemd memory cap is not binding — drop that lead

`~/.config/convmem/config.toml` sets `subprocess_memory_max = "12G"` /
`subprocess_memory_high = "12G"` against a documented ~2 GB working set on a 62 GB host.
`convmem-watch.service` caps the parent at `MemoryMax=8G`, `MemorySwapMax=0`. A 12 G ceiling is
not a plausible allocation-failure source. The C0 note that the cap is "a genuine new lead"
should not be carried forward.

### 4. New hypothesis (d): platform-level memory corruption

Retained core-dump census (journal retention starts 2026-09-17 02:03, so there is **no**
pre-upgrade baseline — absence of evidence, not evidence of absence):

| Day | Faulting executables |
|---|---|
| 09-17 | python3.11 ×1 |
| 09-18 | python3.11 ×16, python3.14 ×5, chrome ×4, borg ×2, python3.13, ChatGPT, copilot |
| 09-19 | python3.11 ×28, python3.13 ×5, udevadm ×2, chrome, journalctl |
| 09-20 | udevadm ×17, python3.11 ×13, python3.13 ×2, git (**SIGBUS**), copilot |

Current boot (started 06:34:59) already shows: `udev-worker` SIGSEGV at 06:35:11 — eleven seconds
after boot, as root — plus the two convmem faults above.

**Live confirmation during the quiet window:** at **10:02:10**, with `convmem-watch`, `-refine`,
`-reconcile`, `-monitor` and `-cg2-soak-check` all stopped and zero convmem processes running,
`/usr/lib/electron42/electron` (Cursor) took a SIGSEGV. Faults span P-cores (CPU 3, 4, 8) and an
E-core (CPU 17), which argues against one bad core and toward memory/SoC/power — or the kernel.

Correlation worth testing: `linux 7.2.4.arch1-2 → 7.2.6.arch2-1` was installed 2026-09-16 02:00
(with `nvidia-open 615.71.09-1 → -3`); the retained window begins at the first boot on it.
`linux-7.2.4.arch1-2-x86_64.pkg.tar.zst` is still in `/var/cache/pacman/pkg/`, so the A/B is cheap
and reversible.

---

## Ryan GATE (blocking — Phase C′ may not start without it)

Phase C′ counts crashes. On a platform that is faulting unrelated programs, those counts cannot be
attributed. Required before any run:

1. **Kernel A/B first** (cheapest discriminator): boot 7.2.4 from the pacman cache, run a
   representative load, compare the cross-program fault rate. `memtest86+` with XMP off if that is
   inconclusive.
2. **Quiet verdict**: a defined window with **zero non-convmem process core dumps** under
   representative load. Ryan sets the duration; ≥ 12 h including one full workload is suggested.
3. **Golden snapshot** taken inside the quiet window, watcher and all Chroma writers inactive:
   `cp -a` (mtime-preserving), SQLite via backup API, manifest (path, size, mtime, sha256) captured
   from live **before** the copy, then `chmod -R a-w`.

Writer state as of this document (reversible; see § Reversal): stopped 2026-09-20T09:57:02-05:00;
last live write `chroma.sqlite3` mtime 09:53:01.

---

## What to build (Phase C′, diagnostic only — no fix code)

### Arms — a 2×2, not the previous three-arm design

| | Golden index (81 k elements) | Freshly rebuilt index |
|---|---|---|
| **Poison transcript** | control | rebuild arm |
| **Innocuous small file** (`LATEST.md`, a proven crasher) | **negative control (new)** | second cell |

The negative control is the arm the previous design lacked, and it is now the most informative
cell: if the small file crashes at a similar rate, the payload hypothesis is closed and the
question becomes index state versus platform.

**Drop** the "rebuild without the poison units, replay them as new inserts" arm. C0 settled it:
ids are deterministic and content-addressed, the write path is `upsert`-then-prune, and `--force`
only bypasses the unchanged-skip gate. There is no insert-versus-update distinction to construct.

### Replay fidelity

- Inject at the **`ingest.distill` module attribute** (`ingest.py`, `_distill_with_provenance`
  takes the patched branch when `distill is not _distill`). Feed **raw-shaped** dicts — the export
  holds normalized, provenance-attached units. Everything downstream stays real: `normalize_unit`,
  envelope minting, `ollama_embed`, `evaluate_ingest_batch`, `production_chroma_write_session`,
  `add_summary` / `add_unit`.
- **Mandatory id-fidelity preflight (new).** `assertion_seed` at `ingest.py:918-922` is
  `output_locator | rendered_chunk_sha256 | sha256(json.dumps(raw, sort_keys=True, default=str))`
  — it hashes the **raw** distill dict, and only `response_sha256` is persisted
  (`ingest.py:877-886`), never the raw text. So replay preserves ids only if the reconstruction
  serializes byte-identically. Replay one chunk, compare minted unit ids against the golden
  export's ids for that `source_path`. **If they differ, the replay is an insert of new ids, not
  the observed condition — report and stop.**
- Summaries: `summarize` is called directly inside `build_chunk_artifact` with no ingest-level
  indirection. Patch `ingest.summarize` to avoid a provider call, or declare the summary path
  **UNREPLAYED** in the hand-back. Do not silently leave `add_summary` (`chroma_store.py:227`)
  unexercised — it is half the crash surface.

### Counting and interpretation

- Three outcomes per run, counted separately: **CRASH**, **HANG** (per-run wall-clock timeout →
  kill), **CLEAN**. Threshold on crashes alone.
- **Every arm must report the background fault count for its own run window** — concurrent
  non-convmem core dumps from `coredumpctl`. A crash count without its platform baseline is not
  interpretable, and this is now the single most important reporting requirement.
- Restore a pristine golden copy before **every** run.

### Isolation (unchanged, still required)

Worktree with a worktree-local venv (never the `~/.local/bin/convmem` wrapper — it execs the main
checkout). Scratch config redirecting all seven live paths; preflight prints resolved paths and
**aborts** if any resolves under `~/.local/share/convmem`. `env -u DEEPSEEK_API_KEY` (and other
provider keys) on every run — fail closed. Live SQLite read-only via backup API or `mode=ro`
only; never open the live directory with a Chroma client. After-proof: sha256 + mtime of live
Chroma and the convmem DB against the golden manifest.

---

## What NOT to build

- No fix code in Phase C′ — diagnose, report, stop.
- No live-store writes or Chroma-client opens; no watcher restart; no corpus-wide reindex.
- No external provider calls; the transcript never leaves the machine.
- No hardware or BIOS actions — that is Ryan's gate, not an agent's.
- Do not carry forward the memory-cap lead (§ 3) or the poison-payload framing (§ 1).

---

## Test expectations

1. Id-fidelity preflight passes (minted ids == golden export ids) or the run stops with that finding.
2. Negative control (`LATEST.md` against the golden index) produces a crash/hang/clean count.
3. Each arm reports its concurrent background (non-convmem) fault count.
4. Restore-to-pristine verified between runs (manifest match).
5. After-proof shows the live store untouched.

## Acceptance criteria

- [ ] Platform quiet verdict recorded before the first run (Ryan).
- [ ] All four cells run, or an explicit reason a cell was skipped.
- [ ] Id-fidelity and summary-path status stated explicitly, not assumed.
- [ ] Every crash count paired with its background fault count.
- [ ] Conclusion states which of (a) payload / (b) index size-state / (c) residual corruption /
      (d) platform is supported, and names the WRONG-BLAME risk that remains.

---

## Separable work that does not depend on root cause

Part A of the earlier handoff (watcher cannot infinite-retry a crashing file) is still correct and
still the only thing that stops the re-corruption loop when the watcher returns — **but the
evidence changes its shape**. A per-file crash counter would have quarantined `LATEST.md`, a file
the corpus needs. The design should be a per-file quarantine **plus a global circuit breaker**:
if N index children die from signals within M minutes regardless of which file, stop spawning,
log, and raise an observation. A file-scoped remedy does not fit a failure that is not file-scoped.

---

## Ledger corrections needed (Ryan owns ledger writes)

- `obs_a09dbfa9e237` — "TWO SEPARATE PROBLEMS confirmed: XMP-off fixed hard lockups": the
  separation and the "fixed" claim are both contradicted; unrelated programs still fault.
- `obs_e8db779df8c3` / `obs_c1499a660d4f` — "deterministic, file-specific" and "live Chroma index
  corruption" are not supported by the forensics above.

---

## Reversal (writer stops taken 2026-09-20T09:57:02-05:00)

```bash
systemctl --user start convmem-refine.service
systemctl --user enable --now convmem-reconcile.timer
systemctl --user enable --now convmem-monitor.timer
systemctl --user enable --now convmem-cg2-soak-check.timer
```

`convmem-monitor` writes Chroma (`monitor_command` opens `production_chroma_write_session`) and
`convmem-cg2-soak-check` runs `convmem doctor`, which opens the Chroma directory; both were stopped
for that reason. Restic timers were deliberately left running.

---

## Related files

| What | Path |
|------|------|
| Prior handoff (remediation still valid) | `docs/inter-model/KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md` |
| Arc brief | `docs/plans/STATUS-chroma-upsert-crash.md` |
| Distill seam / id seed | `ingest.py` (`_distill_with_provenance`; `assertion_seed` at `:918-922`) |
| Crash surface | `chroma_store.py:227` (`add_summary`), `:282` (`add_unit`) |
| Watcher argv + caps | `watch.py:160`, `:169`, `:203-233` |
| Quarantined evidence | `~/.local/share/convmem/chroma.corrupt-2026-09-19`, `…-2026-09-20` |

## Leaving / picking up checklist

**Author (Kiro lane, leaving):**
- [x] Chroma writers stopped and timestamped; reversal documented
- [x] Read-only forensics on both quarantined indices and the live index
- [x] Experiment redesigned against the evidence; superseded premises named
- [x] LATEST.md bullet + STATUS arc brief written on this branch

**Implementer (Cursor, picking up):**
- [ ] Do not start before the Ryan platform gate clears
- [ ] Read this file and `docs/plans/STATUS-chroma-upsert-crash.md` before the first edit
- [ ] Run the id-fidelity preflight before counting a single run
