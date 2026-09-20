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
- **Id and provenance fidelity: verified offline, 2026-09-20.** `normalize_unit` returns
  `make_unit_id(source_path, start_offset, title, unit_index)` — the Chroma unit id never touches
  the raw dict. The raw-dict sha enters only `assertion_seed` (`ingest.py:918-922`), which mints
  `assertion_id`; and `_commit_chunk_to_stores` (`ingest.py:645-670`) compares **provenance
  identity** `(assertion_id, commitment)` and, on divergence, re-keys the write to a fresh
  `projection_id` — i.e. an INSERT, not the observed upsert. So provenance fidelity, not id
  fidelity, is the thing that must hold.
  **It holds.** Reconstructing the raw dict as
  `{type, title, summary, keywords, confidence, domain}` from the export's own normalized values
  and re-minting via `_uuid4_from_seed(f"{seed}:1")` reproduces the stored `assertion_id` for
  **3,548 of 3,548** poison-transcript units — 100%, zero mismatches, first mint attempt.
  `normalize_unit` was value-preserving for every one. Replay through the seam will therefore
  match provenance identity and take the upsert path. Keep the check as a preflight assertion
  per unit and drop any unit that fails it.

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

## Offline findings that change the replay set (2026-09-20, pre-gate)

### The export holds ~67 re-index generations, not one

`make_unit_id` hashes the **title**, and each retry produced a fresh DeepSeek response with fresh
titles, so every retry minted brand-new unit ids and appended them. For the poison transcript the
export holds **3,548 units across 14 chunks** (`chunk_start` 0…650, stride 50 — contiguous, so the
stored units cover the whole file; the handoff's "13 chunks" was one short). Distinct
`provider_payload_sha256` values per chunk show the generation count: **67 for chunk 0**, 51, 47,
39, 31, 20, 22, 23, 23, 21, 19, 18, 9, and **2 for chunk 650**.

The live projection is far smaller: the quarantined 09-20 store holds **449 ids** for this source
— **436 knowledge units + 13 summaries** — and those 436 are a *patchwork* of **42 generation
fragments** (5 generations contribute to chunk 0, 4 to chunk 50, 3 to most others, 2 to chunk 600,
**none to chunk 650**). Prune only removes rows the completing run did not re-emit, and almost no
run completed, so no single generation survives intact.

**Therefore: do not replay the 3,548 units.** That would insert ~3,100 ids Chroma has never seen
and measure the wrong operation. The replay set is **exactly the export rows whose `id` is one of
the 436 unit ids the golden store holds for that `source_path`**, reconstructed raw-faithfully per
the verified method above. Compute the intersection in preflight and report its size; if it is not
436 against the golden snapshot, say so before running anything.

### The survival curve argues against a payload-specific cause

Generations reaching each chunk: 67 → 51 → 47 → 39 → 31 → 20 → 22 → 23 → 23 → 21 → 19 → 18 → 9 → 2.
Runs die **throughout** the file, not at one chunk. A deterministic payload defect at "chunk 13"
would hold flat and then cliff to zero; a roughly constant per-chunk death rate with only ~3% of
runs completing is the signature of a **stochastic** failure. This is independent support for
hypothesis (d) and against (a).

*Caveat:* the curve counts generations that committed ≥1 unit for a chunk, and a chunk can
legitimately yield zero accepted units (`min_confidence` / `normalize_unit` rejections) — which is
why the count ticks up at chunks 300 and 350. It is directional evidence, not a clean survival
function.

### Two store inconsistencies to report, not to fix here

- **13 summaries for 14 chunks.** The `conversation_summaries` collection has no row for
  `chunk_start 650`, and no live unit generation covers that chunk either.
- **Export vs projection drift.** 3,548 export rows against 436 live units for one source. This
  file alone accounts for ~3,100 of the ~69,020 "historical-only" ids `doctor index_drift`
  reports corpus-wide. Export compaction dedupes by id, and these ids are all distinct, so it
  cannot reclaim them.

### Cost note

Sixty-seven distill passes over a 40 MB transcript went to `deepseek-v4-flash` (unit timestamps:
2,864 on 09-18, 661 on 09-19, 23 on 09-20). The 2026-09-17 loud-failure corrective does not catch
this, because a signal death is not a non-zero exit. The circuit breaker below is the control that
would have stopped it.

## Upstream lead: hnswlib `updatePoint` under multiple threads (2026-09-20, pre-gate)

chroma-core/chroma **#6895** reports a SIGSEGV whose trigger shape is ours exactly: *upserting
documents that already exist in the index*, where hnswlib's `updatePoint()` calls
`repairConnectionsForUpdate()` and hits an invalid memory access. The reporter's three workarounds
are all thread-count related — force `num_threads = 1`, or create the collection with
`{"hnsw:num_threads": 1}`, or mark the old label deleted and assign a new one instead of reusing
it — and they report 50,000+ documents indexed with zero crashes afterwards. No fixed version
exists. chroma-core/chroma **#6852** and neo-cortex-mcp **#2** describe related SIGSEGVs in the
Rust bindings, the latter with a corrupted/oversized HNSW index on 1.5.5.

**This fits every convmem-side observation that the payload hypothesis could not:**

| Observation | Explained by a multithreaded `updatePoint` race |
|---|---|
| Fresh client, 1,200 upserts, no crash | An empty collection has no existing elements to *update* |
| `LATEST.md` (11 KB) crashes too | Also an upsert over existing ids |
| `refine` crashes | `update_unit_metadata` is an update path |
| Rebuild buys ~2 h | Rebuild drops 153,626 elements / 73,545 tombstones to 81,575 / 566; a smaller, less-tombstoned graph means shorter repair walks and a narrower race window, which re-widens as it grows |
| Survival curve is stochastic | A data race fires probabilistically, not at a fixed chunk |
| `tokio-rt-worker` threads faulting inside `chromadb_rust_bindings.abi3.so` | The faulting threads are index-update workers |

**Our exposure:** `chroma_store.py:213-214` creates collections with `metadata={"hnsw:space":
"cosine"}` and **never sets `hnsw:num_threads`**, so Chroma's default applies —
`multiprocessing.cpu_count()`, which is **24** on this host.

**Honest limits of the match:** the upstream report is macOS 26.5 beta / Apple M5 / Python 3.13 /
`chroma-hnswlib` 0.7.6; we are Linux x86_64 / Python 3.11 / chromadb 1.5.9 Rust bindings. The
trigger shape matches, the binary does not. Treat it as a strong lead, not a confirmed match.

**Version reality:** `requirements.txt:3` already pins `chromadb==1.5.9`, and **1.5.9 is the
latest published release** — there is no upgrade to move to. The only version move available is a
downgrade below 1.5.4, which is a large step back. So the mitigation to test is the thread setting,
not a version bump.

### New arm — and it should run FIRST, because it does not need the platform gate

Replay the 436-unit live set against a scratch copy twice: once with the collections as they are,
once created with `{"hnsw:num_threads": 1}`. A **positive** result (crashes with default threads,
none single-threaded) is informative even with platform noise in the background, because noise
cannot explain a systematic difference between two otherwise identical arms. Only a negative
result stays ambiguous until the platform is quiet.

Note the trade-off if this becomes the fix: single-threaded HNSW updates are slower, and
`hnsw:num_threads` is set at collection creation — whether it can be changed on an existing
collection via `modify()` or needs a rebuild is for the implementer to determine, not to assume.

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
