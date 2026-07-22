# Verify Plan — semantic-dedupe-hygiene

```
Planning Status

Phase:        Verify (semantic-dedupe-hygiene)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** `<branch or main tip SHA after Phase A+>`  
**PR(s):**  
**EXECUTION / ARCHITECTURE:**
[`ARCHITECTURE-semantic-dedupe-hygiene.md`](ARCHITECTURE-semantic-dedupe-hygiene.md),
[`EXECUTION-2026-07-22-semantic-dedupe-hygiene.md`](EXECUTION-2026-07-22-semantic-dedupe-hygiene.md)  
**Goal:** Prove queue growth is paused correctly and any applies were banded + reversible.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
**GATE** = Ryan process step; not a mechanical agent PASS.

**Flow:** Complete **V0–V7** → Mechanical PASS|FAIL → independent sign-off → Ryan GATE.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Ingest `queue_max_depth` pause; example config comments; live job alignment; banded `--approve-dedupe` evidence | Ranking / source_trust / Phase D snapshot purge unless Ryan expanded scope |
| Pending count + undo snapshots | Blind `--approve-dedupe all` without sample evidence |

---

## V0 — Preconditions

```bash
convmem doctor
git rev-parse HEAD
gh pr view <N> --json number,state,headRefOid
```

| ID | Check | PASS |
|----|-------|------|
| V0a | Doctor write_lane / chroma OK (warns OK) | … |
| V0b | Tip SHA recorded | … |

---

## V1 — Config / jobs alignment

```bash
rg -n 'jobs|queue_max_depth' ~/.config/convmem/config.toml config.example.toml
```

| ID | Check | PASS |
|----|-------|------|
| V1a | Live jobs omit `semantic_dedupe` **or** Ryan-written exception in VERIFY evidence | … |
| V1b | Example config documents pause / optional job | … |

---

## V2 — Ingest depth pause (code)

```bash
# unit test and/or dry observation
rg -n 'queue_max_depth|semantic_queue_at_max_depth|pause' ingest_dedupe.py refine.py tests/
python -m unittest tests.test_ingest_dedupe tests.test_refine -q
```

| ID | Check | PASS |
|----|-------|------|
| V2a | Ingest path refuses append when depth ≥ max (test or code review) | … |
| V2b | Focused tests exit 0 | … |

---

## V3 — Queue metrics

```bash
# same classify snippet as EXECUTION snapshot
wc -l ~/.local/share/convmem/dedupe_queue.jsonl
```

| ID | Check | PASS |
|----|-------|------|
| V3a | Before/after pending counts recorded | … |
| V3b | If applies ran: band + sample size documented | … |

---

## V4 — Apply safety (only if Phase C ran)

```bash
ls -lt ~/.local/share/convmem/refine_undo/semantic_dedupe/ | head
```

| ID | Check | PASS |
|----|-------|------|
| V4a | Undo snapshot(s) exist for applied tombstones | … |
| V4b | No `--approve-dedupe all` without sample note | … |
| V4c | Ranking code / golden fixture untouched | … |

---

## V5 — Growth stopped

| ID | Check | PASS |
|----|-------|------|
| V5a | After A3+A1: pending count stable or down over one watch/index cycle (no unbounded climb) | … |

---

## V6 — Docs / handoff

| ID | Check | PASS |
|----|-------|------|
| V6a | LATEST points at this arc | … |
| V6b | Phase D explicit defer or separate brief | … |

---

## V7 — Independent sign-off

| ID | Check | PASS |
|----|-------|------|
| V7a | Written PASS/FAIL naming tip SHA and residuals | … |

Verifier performs **no** cleanup or correction.

---

## Evidence log

```text
VERIFY-semantic-dedupe-hygiene — tip <sha> — runner <lane> — <ISO-8601>
V0: …
…
Mechanical: PASS|FAIL
Sign-off: …
```
