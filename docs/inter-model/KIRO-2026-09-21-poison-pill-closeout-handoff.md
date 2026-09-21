# Close-out Handoff: Arc Poison Pill — accepted, hardening backlog open

**Date:** 2026-09-21
**Author:** Kiro (design/review lane)
**For:** Cursor (implementation) + whoever resumes Arc Poison Pill
**Purpose:** This Kiro session is closing permanently. This is the single durable anchor so no
future work is lost. LATEST.md points here.

---

## Resume state

| Field | Value |
|-------|--------|
| **Arc** | Poison Pill (convmem indexer SIGSEGV / Chroma upsert crash) |
| **State** | **ACCEPTED (2026-09-21, Ryan authority) — hardening-only.** Not an active incident. |
| **Branch** | `fix/2026-09-20-chroma-upsert-poison-pill` (pushed) |
| **Arc brief** | `docs/plans/STATUS-chroma-upsert-crash.md` |
| **Execution/decision record** | `docs/plans/EXECUTION-poison-pill-resume.md` (§7 backlog, §8 decision) |
| **Prior handoffs** | `KIRO-2026-09-21-poison-pill-12h-gate-handoff.md` (Q1–Q3 + validator appendix), `KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` |

---

## What was resolved (do NOT re-investigate)

- **Root cause = platform, not software.** The multi-subsystem crashes (convmem/comfyui python,
  udevadm-as-root, git SIGBUS, copilot, electron) were an unstable memory subsystem: XMP demanding
  rated speed from a memory controller left under-volted after a CPU-overclock reduction, on an
  i7-13700K / Z790 AORUS ELITE AX. **Fix: XMP off + Intel defaults restored (PL1 253 W, PL2 no
  longer unenforced).** Accepted on ~18–19 h writer-loaded clean window (0 crashes, §4.2 structural
  OVERALL PASS under load).
- **The Chroma index corruption was a *symptom*** of the platform instability (torn writes during
  lockups), not an independent Chroma bug. The index was rebuilt clean from SQLite; corrupt
  originals quarantined as `chroma.corrupt-2026-09-19/20`.
- **These observations are now STALE / superseded by acceptance** — a resumer should treat them as
  historical, not open bugs to chase:
  - `obs_a09dbfa9e237` (two-problems), `obs_c1499a660d4f` (root-cause-corrected),
    `obs_e8db779df8c3` (Chroma 1.5.9 _upsert heap corruption). These described the crash while its
    cause was still unknown; the accepted conclusion is that they were platform-driven. Keep for
    provenance; do not reopen unless crashes RECUR on the current BIOS settings.

---

## Open future work — the hardening backlog (Cursor lane, none blocking)

All of these are in `EXECUTION-poison-pill-resume.md §7`. Consolidated here so nothing is lost:

1. **Circuit breaker (§7.1)** — poison-pill skiplist: after N native-fault crashes (returncode in
   {-11,-6,-7}; NOT -9/-15/timeouts) on the same path, quarantine it. Timeouts get their own
   threshold M. Key by path; reset on success; append-safe (byte-prefix rule). Atomic persistence.
   CLI: `convmem watch --clear-quarantine[-all]`. (Full spec in the phase-C handoff.)
2. **Crash-vs-provider-drop accounting** — a native crash must not be counted as a provider drop;
   add a distinct `native_crash_count` doctor field; do NOT rename/overload `ingest_degraded`
   (`doctor.py:440 _check_synthesis_gate`).
3. **Enforceable writer-lease (Q3 ruling)** — the "freeze" is currently advisory only and has failed
   twice (agents ran `convmem index` inside a declared quiet window). Either make it enforceable (a
   lease/flag the `index`/`add` CLI paths honour) or keep docs honest that it is advisory. Owner:
   propose Cursor, pending Ryan.
4. **Port the §4.2 HNSW structural validator into `scripts/`** — it currently lives only in the
   non-durable `~/.cache/arc-poison-pill/hnsw_validate.py` AND is preserved as an appendix in
   `KIRO-2026-09-21-poison-pill-12h-gate-handoff.md`. Port with the two hnswlib deviations noted
   (4-byte header prefix; `cur_element_count` not `max_elements`).
5. **On-demand pre-op snapshot (§7.5)** — backups are once-daily; there is no `take_snapshot(reason=…)`
   for checkpointing before a risky op. Must preserve complete-data-v2 lineage; intersects the
   Recovery Authority arc.
6. **Export/projection drift (§7.6)** — 3,548 export rows vs 436 live units for one source; ~3,100
   of `doctor index_drift`'s historical-only ids come from that file; compaction can't reclaim them.
7. **`phase1-crash-watch` hook is a FALSE POSITIVE** (`obs_4aefca3bbb49`) — it re-emits stale
   prior-boot coredumps as "new" every turn; the current boot has 0. Fix: key its baseline to boot
   start (`uptime -s` / `journalctl -b 0`). Cosmetic but it masks any genuinely new crash.
8. **OpenClaw native output is unwatched** (`obs_3d9dc004a0d3`) — the OpenClaw 2026.3.2 install (via
   Grok/Cursor) is auto-recorded because Cursor transcripts are watched, but OpenClaw's OWN
   runtime/session output has no path in `[sources].paths`. To capture post-install OpenClaw
   activity long-term, add its data dir once it exists. Integrate against installed capabilities
   (2026.3.2 has no top-level `mcp` command).

---

## Parked, separate arc (NOT Poison Pill)

- **`obs_68435fbdab34` — RTX 3060 GPU Xid faults on one SM (GPC2/TPC0/SM1).** Parked at Ryan's
  request early in the incident. This is a *distinct* hardware question (a possibly-defective GPU
  SM or a specific CUDA kernel), independent of the accepted platform fix. If ComfyUI/CUDA work
  resumes and Xid faults recur on that same SM, pick this up as its own investigation. Do not fold
  it into Poison Pill.

---

## For the resumer

1. Read this file, then `STATUS-chroma-upsert-crash.md` (arc brief) and `EXECUTION §7/§8`.
2. Check `convmem unresolved` — the 3 Chroma obs are historical (see above); 4aef/3d9d/6843 are the
   live future items.
3. If crashes RECUR on current BIOS settings, the acceptance is revoked (EXECUTION §5 tripwires) and
   this becomes an active incident again — start from the platform, not the software.
4. Hardening items are non-blocking; schedule via Cursor when convenient. None gate normal operation.
