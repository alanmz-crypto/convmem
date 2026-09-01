# Cursor completion — JudgeBench T2/T3/T4/T5

**Who/What:** Cursor lane completed the Tier 5–8 escalation wall routed from Crush
via [`CURSOR-2026-08-09-judgebench-T2-T5-handoff.md`](CURSOR-2026-08-09-judgebench-T2-T5-handoff.md).
**When:** 2026-08-09, branch tip after T2–T5 Execute + dry-run CLI.
**Why:** G2 execution was approved; Flash S1–S9 prep landed on `main`; remaining
identity/provenance/runner/legacy work was OFF-LIMITS below Tier 5.
**Branch:** `fix/2026-08-09-judgebench-arch-lock-chroma-rebuild` (pushed to origin).

---

## Delivered (T2–T5)

| Task | Artifact | VERIFY |
|------|----------|--------|
| T2 | [`eval_model_identity.py`](../../eval_model_identity.py) — fail-closed classify | — |
| T3 | [`eval_provenance.py`](../../eval_provenance.py) comparison signature | CHK-004 |
| T4 | [`eval_judgebench/runner.py`](../../eval_judgebench/runner.py) — offline runner + gold hash guard | CHK-007 partial, CHK-008 |
| T5 | [`eval_judge.py`](../../eval_judge.py) `legacy=True` gate; scripts require `--legacy` with `--judge` | CHK-005, CHK-006 |

**Tests:** `tests/test_judgebench_contracts.py` (S3/S4 contracts + T2–T5 escalation)
+ existing JudgeBench suite — all green.

**Dry-run (no live judge):**

```bash
python -c "
from eval_judgebench.runner import run_judgebench
from pathlib import Path
run_judgebench(
    Path('eval_corpus/fixtures/judgebench/semantic-v1'),
    cfg={'models': {'ollama_host': 'http://localhost:11434'}},
    judge_model='deepseek-v4-pro',
    under_test_model='llama3.1:8b',
    semantic_judge=None,
)
"
```

---

## Delegate-down wall — handoff required

Cursor cannot proceed past **Ryan HITL gates** without owner lock:

| Gate | Blocker | Ryan action |
|------|---------|-------------|
| **G3** | Corpus gold/split lock | Version and populate `semantic-v1` cases/gold (incl. calibration fixture) |
| **G4** | Judge selection | Choose v1 judge after calibration-split experiments |
| **CHK-007 full** | Corpus-backed conformance | Depends on G3 populated fixtures + G4 pinned judge |

T6 E2E scaffold (`eval_corpus/fixtures/convmem-e2e/synthesis-v1/`) is **structure-only**
from S2 — gold population also waits on G3.

**Do not:** author semantic case content, mutate locked gold, bless a judge model,
wire live `ask.py` judging, or add Chroma to the semantic path.

---

## Suggested PR

**Title:** Add JudgeBench identity, provenance, runner, and legacy judge shim

See prior Cursor turn for full PR body (consequence-first shape). Squash merge OK.

**Merge reading:** [`ARCHITECTURE-judgebench.md`](../plans/ARCHITECTURE-judgebench.md) ·
[`EXECUTION-judgebench.md`](../plans/EXECUTION-judgebench.md) ·
[`VERIFY-judgebench.md`](../plans/VERIFY-judgebench.md)

---

## Next lane after merge

1. Ryan: G3 gold lock → populate semantic cases (then CHK-007 can go full PASS)
2. Ryan: G4 judge selection after calibration experiments
3. Optional: live semantic judge wiring in runner (post-G4 only)

Dense consult: skipped — no contested owner fork; gates are Ryan stops by design.
