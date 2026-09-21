# Arc Brief — Poison Pill (convmem indexer SIGSEGV / Chroma upsert crash)

**Arc codename:** Poison Pill · **Slug:** `chroma-upsert-crash`
**Opened:** 2026-09-20 · **State:** **ACCEPTED (2026-09-21, Ryan authority) — downgraded to
hardening-only.** BIOS-misconfiguration fix accepted on an ~18 h writer-loaded clean window
(0 crashes, §4.2 structural OVERALL PASS under load); the literal ≥24 h bar was waived by Ryan.
Remaining work is the §7 hardening backlog in Cursor's lane; nothing blocks normal operation.
See [`EXECUTION-poison-pill-resume.md`](EXECUTION-poison-pill-resume.md) §8 decision record.

---

## 1. What This Is For (product goal)

convmem's corpus is only trustworthy if ingest is trustworthy. From 2026-09-18 the indexer died
repeatedly with SIGSEGV/SIGABRT during Chroma writes, the watcher retried crashing files forever,
and the HNSW index was rebuilt and quarantined twice. The arc is done when the cause is known, the
watcher can no longer loop on a crashing input, and the corpus can be written to again with
confidence.

## 2. System Design (how the pieces connect)

`convmem.py index --file <p>` → `ingest.index/_index_impl` (wrapped in `production_writer_boundary`
→ exclusive flock) → `_index_one_file` → `_process_file_chunks` → `build_chunk_artifact`
(summarize + distill + `ollama_embed` per unit) → `commit_chunk_artifact` → `_commit_chunk_to_stores`
→ `ChromaStore.add_summary` (`chroma_store.py:227`) and `add_unit` (`:282`), both `upsert` over
**deterministic, content-addressed ids**, then `_prune_completed_reindex`.

The watcher spawns one child per file: `<python> convmem.py index --file <path>`, no `--force`,
under `systemd-run --scope -p MemoryMax=12G -p MemorySwapMax=0`. Writers (ingest, `refine`,
`monitor`, `propose_decision`) serialise through `exclusive_writer_lease`
(`chroma_write_store.py:502`). **Readers do not** — and nine long-lived `mcp_server.py` processes
hold the live store open whenever the editors are running.

## 3. What Exists Right Now (file map)

| Surface | State |
|---|---|
| `docs/inter-model/KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md` | On this branch. Remediation spec (Part A/B) valid; **root-cause premise superseded** |
| `docs/inter-model/KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` | On this branch. Phase C′ design, offline findings, and the matrix result that retires most of it |
| `~/.cache/arc-poison-pill/{probe.py,matrix.sh,matrix.log}` | Scratch probe + results, retained. The 4.5 GB index copies were deleted (reproducible in ~2 s from the quarantine) |
| `~/.local/share/convmem/chroma.corrupt-2026-09-19` (4.7 G), `…-2026-09-20` (4.5 G) | Quarantined evidence; forensically examined, **structurally sound** |
| Live `~/.local/share/convmem/chroma` | Rebuilt 2026-09-20 04:57. Still written by MCP readers even with all units down |
| `docs/plans/EXECUTION-poison-pill-resume.md` | On this branch. Staged resumption, pre-registered proof, tripwires, hardening backlog |
| Poison-pill quarantine / circuit breaker | **Does not exist** — no code written |
| Phase C′ replay harness | **Not needed as designed** — see § 4 |

## 4. Completion State

- [x] Crash characterised; C0 code trace (upsert-not-insert, `ingest.distill` seam, no export→Chroma rebuild)
- [x] Chroma writers stopped and **disabled** (survive reboot); quiet window from 2026-09-20T09:57:02-05:00
- [x] Forensics: no structural corruption in either quarantined index, nor in the live index at crash time
- [x] Replay fidelity proven offline — 3,548/3,548 assertion ids reconstruct from the export
- [x] Replay set corrected — 436 live units, not the 3,548 export rows spanning ~67 generations
- [x] **Ryan platform gate**: Intel defaults restored (PL2 4095 W → 253 W), XMP off, memory at 4533 MT/s (normal four-DIMM downclock)
- [x] **Upsert matrix: 15/15 CLEAN** — 300,000 update-in-place upserts into the crashing index across
      default threads, `num_threads=1`, and nine-concurrent-readers. Software cause excluded
- [x] Working assumption adopted (Ryan, 2026-09-20): BIOS misconfiguration, mitigated — resume plan written
- [ ] **Observation window** — ≥6 loaded hours clean = credible; ≥24 h = accepted (pre-registered)
- [ ] Stage 0: fresh restic snapshot while quiescent (newest is `e51f849a…`, taken 00:19 = pre-rebuild)
- [ ] If faults return: two-DIMM test, then RMA under Intel's extended warranty
- [ ] Remediation: per-file quarantine + global crash circuit breaker (Cursor)
- [ ] Ledger corrections to the three `obs_` records (Ryan)

## 5. Your Role (read this to know what you're here to do)

**Read [`EXECUTION-poison-pill-resume.md`](EXECUTION-poison-pill-resume.md) first** — Ryan adopted the
BIOS-misconfiguration assumption on 2026-09-20, so work proceeds in staged resumption with
pre-registered proof thresholds and tripwires. Nothing below licenses closing the arc.

The diagnostic phase is essentially finished and the answer is **not a convmem bug**. Do not restart
the Phase C′ replay experiment — the matrix already answered the question it was designed to ask.

If you are picking this up to **build**: the remaining convmem work is the circuit breaker (§ 6.3),
which is worth doing regardless of cause because it is what let one file burn 67 DeepSeek passes.

If you are picking this up to **assess the platform**: read § 6.1. The instrument is elapsed loaded
time, not another test.

Do not restart the watcher, do not open the live Chroma with a client, and do not revive the
"poison transcript" framing — it is refuted.

## 6. What Remains Before "Live" (sequential)

1. **Observation window (Ryan).** At the pre-fix rate (~0.57 faults/hour machine-wide) the chance of
   a wholly clean stretch falls below 5% at roughly 5–6 loaded hours. Watch `coredumpctl` under
   normal workload. A clean day makes the BIOS correction credible.
2. **If faults return.** Pull two of the four DIMMs — four sticks is the hardest case for the memory
   controller that degrades on this generation. If they persist on two, it is an RMA conversation
   (Intel extended the warranty to 5 years for affected 13th/14th-gen parts), not more tuning.
3. **Remediation (Cursor).** Per-file quarantine **plus** a global circuit breaker: if N index
   children die from signals within M minutes regardless of file, stop spawning and raise an
   observation. File-scoped logic alone would have quarantined `LATEST.md`, which the corpus needs.
4. **Reader discipline (design question, unowned).** Nine `mcp_server.py` processes hold the live
   store outside the writer lease, and one wrote to it at 11:01:48 with every unit disabled. The
   store cannot be frozen while editors run, which breaks any future after-proof.
5. **Ledger correction (Ryan).** Three `obs_` records assert a two-problem split and a file-specific
   cause that the evidence contradicts.

**Hypothesis status.** (a) poison payload — **refuted**: `LATEST.md` and `refine` crash identically.
(b) index size / accumulated state — **refuted for the upsert path**: 300,000 upserts into the
153,626-element pre-rebuild index, clean. (c) residual on-disk corruption — **unsupported**: every
structural check passes. (d) platform — **favoured**: faults concentrate 78% on CPUs 4, 8 and 10
(including both Turbo Boost Max favoured cores at 5400 MHz), unrelated programs fault (udevadm at
boot, `git` SIGBUS, chrome, electron, borg), and PL2 was unenforced at 4095 W against a correct
253 W PL1. **Unproven** — the BIOS change and the matrix happened in the same window, so the two
cannot be fully separated; only elapsed clean time settles it.

## 7. Hard Stops (models cannot cross)

- No live-store writes; no Chroma-client open on the live directory.
- No watcher restart until the circuit breaker exists.
- No corpus-wide reindex, no external provider calls, no hardware/BIOS action by a model.
- Ledger writes and merges are Ryan's.

## 8. Relationship to ConvMem (the bigger picture)

With writers disabled the corpus is frozen: `brief`/`doctor` counts go stale and Track A session
indexing is paused. Adjacent to **Trapdoor Hunt / #268** (watcher OOM) but distinct. The platform
question reaches past convmem — `git` took a SIGBUS — so repo work on this machine carried risk
during the fault window, though a full `git fsck` came back clean.

## 9. Key Design Files (for deep dives)

| What | Path |
|---|---|
| Phase C′ design + findings + matrix result | `docs/inter-model/KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` |
| Original remediation spec | `docs/inter-model/KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md` |
| Crash surface | `chroma_store.py:227`, `:282` |
| Id determinism | `ingest.py:918-922`, `:121-144` |
| Writer serialisation | `chroma_write_store.py:502-575` |
| Watcher spawn + caps | `watch.py:160`, `:169`, `:203-233`; `config.toml` `[watch]` |

## 10. How to Update This Brief (departure protocol)

Overwrite §§ 3–6 to reflect reality now. Delete completed items, rewrite § 5 for the next model, do
not append session narrative — that belongs in Track A. One line in the Update Log. Test: could a
fresh model read only this file and orient itself?

## Update Log

- 2026-09-21 — Kiro (design/review lane): **ARC ACCEPTED on Ryan authority.** Ryan waived the
  literal ≥24 h bar and accepted the ~18 h 40 m writer-loaded window (0 crashes this boot, 0 since
  the 05:11 unfreeze, §4.2 structural OVERALL PASS on both live segments under load). Arc downgraded
  from active incident to hardening-only; §7 backlog remains in Cursor's lane, non-blocking.
  Decision recorded in EXECUTION §8.
- 2026-09-21 — Kiro (design/review lane): post-unfreeze verification. Staged unfreeze executed
  (refine → watcher + reconcile.timer) against rebuilt-clean index; 18h+ boot, 0 crashes, 0 since
  unfreeze. Read-only §4.2 validator run on the LIVE index = OVERALL PASS (both segments,
  4000 + 82335 elements, clean walks to exact EOF). Index structurally intact under writer load;
  ≥24 h writer-loaded "accepted" clock running from 05:11 unfreeze. Details in
  `KIRO-2026-09-21-poison-pill-12h-gate-handoff.md` post-unfreeze section.
- 2026-09-21 — Kiro (design/review lane): ruled Q1–Q3 in `EXECUTION-poison-pill-resume.md`
  (§3, §4.2, §7.3). Q1: ≥24 h "accepted" clock RESTARTS at stage-2 enable, "loaded" = writer-load.
  Q2: absolute §4.2 structural check sufficient, no stage-0 baseline needed. Q3: freeze is advisory,
  not enforced, until an owned CLI writer-lease exists (Cursor lane). Platform then 17 h clean this
  boot; staged unfreeze authorised by Ryan.
- 2026-09-21 — Claude Opus 5 (Kiro design/plan lane): first observation reading — 14.97 clean
  loaded hours (0 faults / 0 dumps / 0 MCEs) and §4.2 structural PASS on both live segments;
  §3 ≥6 h credible gate met, stage 2 authorised-pending-Ryan, stage 3 still shut. §4.2 had no
  implementation, so a read-only validator was written; three design questions raised for Kiro
  in `KIRO-2026-09-21-poison-pill-12h-gate-handoff.md`.
- 2026-09-20 — Claude Opus 5 (Kiro design/plan lane): Ryan adopted the BIOS-misconfiguration
  assumption; staged resume plan + pre-registered proof written to `EXECUTION-poison-pill-resume.md`.
- 2026-09-20 — Claude Opus 5 (Kiro design/plan lane): arc opened; writers stopped and disabled;
  forensics found no index corruption; replay fidelity proven offline; Intel defaults restored;
  upsert matrix 15/15 clean excluded the software cause; platform favoured, awaiting an
  observation window.
