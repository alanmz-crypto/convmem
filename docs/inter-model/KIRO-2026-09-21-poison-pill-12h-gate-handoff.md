# Design Review Handoff: Arc Poison Pill — the 12-hour gate reading

**Date:** 2026-09-21
**Author:** Claude Opus 5 (Kiro design/plan lane)
**For:** Kiro (design review / sign-off — **no implementation**)
**Authorization:** Ryan, 2026-09-21 (verbal — "create a handoff to inform Kiro")
**Arc:** Poison Pill (`chroma-upsert-crash`)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` |
| **Branch** | `fix/2026-09-20-chroma-upsert-poison-pill` |
| **Tip SHA** | see `git log -1` on this branch (this file is the tip commit) |
| **Push status** | `pushed to origin` |
| **PR** | `not opened` |
| **Ryan GATE** | Stage 2 enable command is verified and unrun. Ryan says go before writers return. |
| **Track A ingest** | `~/.claude/projects/-home-lauer-null/acc5de45-d55c-424f-ac74-f4e5d9dffd45.jsonl` (2026-09-20 forensics session, still unindexed — gated until stage 2 opens) |

---

## Why you are reading this

The observation window pre-registered in `EXECUTION-poison-pill-resume.md` §3 has returned its
first reading. The numeric verdict is not in doubt. **Three design questions the plan did not
settle are**, and they all bear on the ≥24 h "accepted" threshold rather than on today's ≥6 h
"credible" one. That is what I want your ruling on. Nothing here asks you to write code.

---

## The reading (verified independently, not taken from the monitor)

Haiku's monitor line at the gate: `CLEAN | 14.95h since boot | faults=0 | dumps=0`.

I re-ran §9's check block myself rather than relaying it:

```
boot: 2026-09-20 10:48:52   now: 2026-09-21 01:46:52   up 14 hours, 57 minutes
kernel_faults=0
No coredumps found.
mce / machine-check / hardware-error lines: 0
```

**Against §3:** ≥6 loaded hours clean → the provisional fix is **credible** → enter stage 2.
Not the ≥24 h that would make it *accepted*, so the arc does not downgrade to hardening and
stage 3 stays shut. Pre-fix baseline was 0.57 faults/hour machine-wide; fifteen clean loaded hours
is far past the pre-registered <5% threshold.

**No tripwire fired** (§5): no non-convmem core dump, no convmem child killed by a signal, no
structural failure.

### Structural check — §4.2 had no implementation, so I wrote one

§6 requires re-running the §4.2 validator at every stage transition. §4.2 names
`~/.cache/arc-poison-pill/` as holding the reference implementation. **It does not.** That
directory contains only `probe.py` (the upsert reproduction) and the matrix log, and the §4.1 /
§4.2 `doctor` checks are still unbuilt in the repo (`grep` for `platform_faults` /
`hnsw_structural` returns nothing). The stage transition had no instrument.

I wrote one to the §4.2 spec — read-only, mmaps the segment files, writes nothing. It lives at
`~/.cache/arc-poison-pill/hnsw_validate.py` and is reproduced verbatim in the appendix below,
because a cache directory is not durable storage and this is currently the only copy.

Two corrections were needed against stock hnswlib, both worth recording for whoever ports this:

1. Chroma's persistent fork writes a **4-byte prefix** before `offsetLevel0_`; the stock field
   offsets are all shifted by 4.
2. `data_level0.bin` holds **`cur_element_count`** elements, not `max_elements` — the fork does not
   dump the preallocated tail. §4.2's "elements × bytes-per-element" is right; a reader who
   substitutes `max_elements` will see a false failure.

Result on the live index:

| Segment | Elements | Level-0 links ≤ maxM0 | link_lists walk | Labels | id_to_label |
|---|---|---|---|---|---|
| `5e85bc5f…` knowledge units | 82,335 (806 delete-marked) | pass, after masking `0x10000` | 704428/704428 — exact EOF | 82,335 unique | 81,529 = 82,335 − 806 ✓ |
| `5cda8744…` summaries | 4,000 (0 delete-marked) | pass | 35448/35448 — exact EOF | 4,000 unique | 4,000 ✓ |

**OVERALL: PASS.** All neighbour ids in range, `length.bin` and `data_level0.bin` sizes exact,
entrypoint in range, `size_data_per_element` consistent with maxM0/dim/label (dim 768, M 16,
maxM0 32, 3212 bytes/element).

### Two state changes since the plan was written

**The rollback point is no longer stale.** §2.2 had the resumption proceeding on `e51f849a…`
(00:19 on 2026-09-20) with an eleven-hour gap, because `ensure_current_snapshot`
(`backup_workflows.py:128`) is a guarantee function with no force path. The daily timer has since
fired: today's complete-data-v2 snapshot is **`8034fe4d…`**, offsite copy **`a344fdc3…`**, both
verified current by `doctor`. Stage 2 starts on a fresh rollback point. §7.5 remains a real gap —
there is still no on-demand pre-change checkpoint — but it does not bite today.

**The store was never frozen.** Chroma went **81,290 → 81,701 knowledge units (+411)** across the
stage-1 window with every writer unit disabled and verified disabled. This is §7.3 reproducing
itself in the open: `convmem index --file` does not honour the freeze. Not a tripwire, nothing
faulted — but "readers and queries only" described intent, not enforcement, for the entire
observation window.

---

## What I want ruled on (design questions, in order of consequence)

### Q1 — Does the ≥24 h clock restart at stage-2 enable?

This is the sharp one. §3 counts "loaded hours", and the fifteen hours were genuinely loaded:
journal volume runs 1,500–3,700 lines in *every* hour since boot with no idle gap, 281 files
touched under the work dirs, and `claude` / `chrome` / `electron` processes carrying 700–2,600 s of
CPU. But that load was desktop and agent work. **It contained no sustained Chroma upsert load**,
because the writers were disabled — which is exactly what stage 2 reintroduces.

So the window is strong evidence for the *platform* claim (PL2 unenforced at 4095 W; unrelated
programs were faulting too) and materially weaker for "upsert under load is safe". Reading the
fifteen hours as fifteen hours of the ≥24 h "accepted" clock would let the arc downgrade to
hardening on evidence that never exercised the crashing workload.

**My recommendation: the ≥24 h clock restarts when stage 2 is enabled**, and §3 gains an explicit
definition of "loaded" that requires writer load, not merely a non-idle machine. Today's reading
still stands on its own as the ≥6 h credible gate — that threshold was about the platform.

### Q2 — Is an absolute structural check sufficient at a stage transition?

Stage 0 called for recording a structural baseline "so later corruption is detectable by comparison
rather than by a crash". **No baseline was ever recorded** — stage 0 was interrupted by the
snapshot blocker in §2.2 and the validator did not exist. Today's PASS is therefore an *absolute*
check against the invariants, not a comparison against a known-good state.

For the invariants §4.2 lists, I believe absolute is sufficient: they are structural truths, not
drift measures, and a violation is corruption regardless of history. From today's run forward there
is a baseline. But it is your call whether that satisfies §6's "re-run at each stage transition"
intent, or whether the transition needs something stronger.

### Q3 — The freeze is unenforceable. Say so normatively, or make it enforceable.

§7.3 and §7.4 are both flagged **"design question, unowned"**. They are now observed twice: an
agent wrote ~234 units inside a declared quiet window on 2026-09-20, and another +411 units landed
across the stage-1 observation window. Nine `mcp_server.py` readers hold the live store outside the
writer lease.

The plan already states the honest position — *"either the freeze becomes enforceable (a flag the
CLI honours) or we stop claiming the store is frozen"*. This needs an owner and a ruling, because
every future arc that says "writers stopped" inherits the same false claim. It is a design
decision, which makes it yours; the implementation, whichever way it goes, is Cursor's.

---

## What NOT to do

- **Do not implement.** The §4.1 / §4.2 `doctor` checks and the §7.1 circuit breaker are Cursor's.
  The appendix script is a reference implementation for porting, not a repo script, and I have
  deliberately not added it to `scripts/`.
- **Do not enable stage 2.** The command is verified and unrun, awaiting Ryan.
- **Do not re-open the software hypothesis.** The upsert matrix closed it (15/15 clean, 300,000
  update-in-place upserts). §5 is explicit on this.
- **Do not describe the cause as established.** §1 still holds: the BIOS correction and the clean
  matrix fall in the same window and cannot be separated by anything we have run. Fifteen clean
  hours raise confidence; they do not convert the assumption into a finding.
- **Do not delete the quarantined indices** (`chroma.corrupt-2026-09-19`, `…-2026-09-20`, 9.2 GB).
  They remain the only surviving pre-fix artefacts until the arc closes.

---

## Acceptance criteria (for this review)

- [ ] Q1 ruled: does the ≥24 h clock restart at stage-2 enable, and does §3 gain a writer-load
      definition of "loaded hours"?
- [ ] Q2 ruled: absolute structural check accepted at stage transitions, or something stronger
      required.
- [ ] Q3 ruled and owned: enforceable freeze, or drop the claim — with the §7.3/§7.4 items assigned.
- [ ] If Q1 changes §3, `EXECUTION-poison-pill-resume.md` is amended (design edit, your lane) and
      the arc brief Update Log gets one line.

---

## Related files

| What | Path |
|------|------|
| Resume plan (thresholds §3, tripwires §5, runbook §9) | `docs/plans/EXECUTION-poison-pill-resume.md` |
| Arc brief | `docs/plans/STATUS-chroma-upsert-crash.md` |
| Prior Kiro handoff (phase C) | `docs/inter-model/KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` |
| Original remediation spec | `docs/inter-model/KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md` |
| Structural validator (reference impl) | `~/.cache/arc-poison-pill/hnsw_validate.py` + appendix below |
| Upsert reproduction probe + matrix | `~/.cache/arc-poison-pill/{probe.py,matrix.sh,matrix.log}` |
| Snapshot guarantee function (§7.5 gap) | `backup_workflows.py:128` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` bullet updated with resume state
- [x] `STATUS-chroma-upsert-crash.md` Update Log line
- [x] Branch pushed

**Reviewer (picking up):**

- [ ] Read `EXECUTION-poison-pill-resume.md` §§3–6 before ruling — the thresholds are
      pre-registered and Q1 is a request to amend a pre-registration, which deserves that friction
- [ ] State Goal / role / system state / next action per the arc brief
- [ ] Rule on Q1–Q3; do not implement

---

## Appendix — `hnsw_validate.py` (reference implementation, §4.2)

Read-only. Run as `python hnsw_validate.py [chroma_dir]`; exits non-zero on structural failure.
Reproduced here because `~/.cache/` is not durable and this is the only copy.

```python
"""Arc Poison Pill §4.2 — HNSW structural validator. READ-ONLY.

Asserts, per segment:
  1. data_level0.bin == cur_element_count x size_data_per_element
  2. level-0 link counts <= maxM0 (after masking hnswlib delete-mark bit 0x10000)
  3. neighbour ids in range [0, cur_element_count)
  4. clean link_lists.bin walk landing on exact EOF
  5. unique labels
  6. len(id_to_label) == cur_element_count - delete-marked
"""
import os, sys, struct, pickle, mmap

DELETE_MARK = 0x10000

def read_header(p):
    """Chroma's persistent hnswlib fork: 4-byte prefix, then the hnswlib fields.
    Only cur_element_count elements are dumped to data_level0.bin (not max_elements)."""
    b = open(p, "rb").read()
    g = lambda fmt, off: struct.unpack_from(fmt, b, off)[0]
    return dict(prefix=g("<I", 0), offset_level0=g("<Q", 4), max_elements=g("<Q", 12),
                cur_count=g("<Q", 20), size_per_elem=g("<Q", 28), label_offset=g("<Q", 36),
                offset_data=g("<Q", 44), maxlevel=g("<i", 52), enterpoint=g("<I", 56),
                maxM=g("<Q", 60), maxM0=g("<Q", 68), M=g("<Q", 76),
                mult=g("<d", 84), ef_construction=g("<Q", 92))

def check(seg):
    name = os.path.basename(seg)
    h = read_header(os.path.join(seg, "header.bin"))
    fails, notes = [], []
    dim = (h["size_per_elem"] - (h["maxM0"] * 4 + 4) - 8) // 4
    notes.append(f"elements={h['cur_count']} max_alloc={h['max_elements']} dim={dim} "
                 f"M={h['M']} maxM0={h['maxM0']} bytes/elem={h['size_per_elem']}")

    # 1. size invariant
    d0 = os.path.join(seg, "data_level0.bin")
    actual, expect = os.path.getsize(d0), h["cur_count"] * h["size_per_elem"]
    if actual != expect:
        fails.append(f"data_level0.bin size {actual} != elements*bytes {expect}")

    lb = os.path.join(seg, "length.bin")
    if os.path.exists(lb):
        want_len = h["cur_count"] * 4
        if os.path.getsize(lb) != want_len:
            fails.append(f"length.bin size {os.path.getsize(lb)} != elements*4 {want_len}")
    if h["enterpoint"] >= h["cur_count"]:
        fails.append(f"enterpoint {h['enterpoint']} >= cur_element_count {h['cur_count']}")
    if h["size_per_elem"] != h["maxM0"] * 4 + 4 + dim * 4 + 8:
        fails.append("size_data_per_element inconsistent with maxM0/dim/label")

    # 2/3/5. walk level 0
    n, sz = h["cur_count"], h["size_per_elem"]
    labels, deleted, bad_cnt, bad_nb = set(), 0, 0, 0
    dup = 0
    with open(d0, "rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        for i in range(n):
            base = i * sz
            raw = struct.unpack_from("<I", mm, base)[0]
            if raw & DELETE_MARK:
                deleted += 1
            cnt = raw & 0xFFFF
            if cnt > h["maxM0"]:
                bad_cnt += 1
                if bad_cnt <= 3:
                    fails.append(f"elem {i}: level-0 link count {cnt} > maxM0 {h['maxM0']} (raw=0x{raw:x})")
            for j in range(cnt):
                nb = struct.unpack_from("<I", mm, base + 4 + j * 4)[0]
                if nb >= n:
                    bad_nb += 1
                    if bad_nb <= 3:
                        fails.append(f"elem {i}: neighbour id {nb} >= cur_element_count {n}")
            lab = struct.unpack_from("<Q", mm, base + h["label_offset"])[0]
            if lab in labels:
                dup += 1
                if dup <= 3:
                    fails.append(f"elem {i}: duplicate label {lab}")
            labels.add(lab)
        mm.close()
    if bad_cnt > 3: fails.append(f"...{bad_cnt} elements total with oversized link counts")
    if bad_nb > 3: fails.append(f"...{bad_nb} out-of-range neighbour ids total")
    if dup > 3:    fails.append(f"...{dup} duplicate labels total")
    notes.append(f"delete-marked={deleted} unique_labels={len(labels)}")

    # 4. link_lists.bin exact walk
    ll = os.path.join(seg, "link_lists.bin")
    size, off, higher = os.path.getsize(ll), 0, 0
    with open(ll, "rb") as fh:
        data = fh.read()
    for i in range(n):
        if off + 4 > size:
            fails.append(f"link_lists.bin truncated at elem {i} (off={off} size={size})")
            break
        lsz = struct.unpack_from("<I", data, off)[0]
        off += 4
        if lsz:
            higher += 1
            if off + lsz > size:
                fails.append(f"link_lists.bin elem {i} claims {lsz}B past EOF (off={off} size={size})")
                break
            off += lsz
    else:
        if off != size:
            fails.append(f"link_lists.bin walk ended at {off}, EOF is {size} (delta {size-off})")
    notes.append(f"elements_with_higher_levels={higher} link_lists_walk_end={off}/{size}")

    # 6. id_to_label cardinality
    meta = os.path.join(seg, "index_metadata.pickle")
    if os.path.exists(meta):
        with open(meta, "rb") as fh:
            m = pickle.load(fh)
        idmap = m.get("id_to_label") if isinstance(m, dict) else None
        if idmap is not None:
            want = h["cur_count"] - deleted
            notes.append(f"id_to_label={len(idmap)} expected={want}")
            if len(idmap) != want:
                fails.append(f"len(id_to_label) {len(idmap)} != elements-deleted {want}")
        else:
            notes.append(f"id_to_label absent; pickle keys={list(m)[:8] if isinstance(m, dict) else type(m)}")
    return name, notes, fails

root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.local/share/convmem/chroma")
segs = sorted(os.path.join(root, d) for d in os.listdir(root)
              if os.path.isdir(os.path.join(root, d))
              and os.path.exists(os.path.join(root, d, "header.bin")))
rc = 0
for s in segs:
    name, notes, fails = check(s)
    print(f"=== segment {name}")
    for x in notes: print(f"    {x}")
    if fails:
        rc = 1
        print("    RESULT: STRUCTURAL FAILURE")
        for f in fails: print(f"      - {f}")
    else:
        print("    RESULT: PASS")
print("\nOVERALL:", "PASS" if rc == 0 else "FAIL")
sys.exit(rc)
```



---

## Post-unfreeze verification (Kiro, 2026-09-21)

After Ryan authorized the staged unfreeze (refine → watcher + reconcile.timer, all against the
rebuilt-clean index), the arc advanced past the freeze. Recorded state at unfreeze +~7h / boot +18h26m:

- **Platform:** 18h26m uptime on the post-BIOS-fix boot, **zero coredumps this boot** (the standing
  crash-watch list is all ≤10:24 on *prior* boots — stale, not new faults).
- **Writers:** `convmem-refine` (incl. `chroma_dedupe`), `convmem-reconcile.timer`, and
  `convmem-watch` all active and healthy; **zero crashes since unfreeze (05:11)**. This is the first
  sustained *writer-loaded* operation on the rebuilt index post-fix.
- **§4.2 structural integrity (read-only validator run against the LIVE index):** **OVERALL PASS**
  on both segments —
  - summaries segment: 4000 elements, 0 delete-marked, unique labels, link_lists walk 35448/35448 exact EOF, id_to_label=4000 ✓
  - units segment: 82335 elements, 806 delete-marked, unique labels, link_lists walk 704428/704428 exact EOF, id_to_label=81529=expected ✓

Interpretation: the index the writers have been actively mutating since unfreeze is **structurally
intact under load**, corroborating (beyond an idle machine) that the platform fix holds. This is the
post-unfreeze baseline for §4.2 (per Kiro Q2 ruling). The ≥24 h writer-loaded "accepted" clock
(Kiro Q1 ruling) is now running from the 05:11 unfreeze.

Still open (Cursor lane, unchanged): circuit breaker (§7.1), crash-vs-provider-drop accounting,
enforceable writer-lease (Q3), and porting the validator from `~/.cache/arc-poison-pill/` +
this appendix into `scripts/`.
