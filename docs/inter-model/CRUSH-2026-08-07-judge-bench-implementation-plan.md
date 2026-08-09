# Implementation plan — JudgeBench-driven judge upgrades

**Based on:** Claude's review of `CRUSH-2026-08-07-judge-bench-analysis.md`
**Plan author:** Crush
**Date:** 2026-08-07
**Status:** ✅ **COMPLETED — implemented and merged as PR #153 (`bfb5b7e`, 2026-08-09)**. All 5 tasks landed. Calibration gate passed (local judge scored good synthesis 5/5, contradictory 1/5). Pylint regression gate PASS. 89 targeted tests pass.

---

## Claude's verdict (one-line)

The analysis direction is right but the numbers are imported from a different task (pairwise preference vs. our absolute 1-5 grading); the real fire is the local fallback model at 40.9% — near-random, swap it first.

---

## Caveat: pairwise vs. absolute grading

JudgeBench measures pairwise preference accuracy (pick correct from a contrastive pair). `eval_judge.py` does absolute single-item 1-5 grading. These are related but distinct — calibrated absolute judgment is harder than forced-choice discrimination. The +10-12 and +15-20 point gains from the paper are *directionally* right (reasoning models and better prompts help both tasks) but the magnitudes are unvalidated for our task shape. Do not treat "+25-30 combined" as a calibrated target.

---

## Implementation tasks (ordered by impact)

### 1. Replace local fallback model — `eval_judge.py`

**Why first:** `llama3.1:8b` at 40.9% on JudgeBench is near-random. A structurally "independent" judge that's bad at the task will pass the independence check and still produce noise. Fix this before anything else.

**What:** Change the fallback in `resolve_judge_model()` from `llama3.1:8b` to `qwen2.5-coder:14b` (9GB, fits RTX 3060 12GB).

**Evidence caveat:** The Aug 4 Crush session benchmarked `qwen2.5-coder:14b` on "QA judgment tests" and reported professional results — but it's unclear whether those tests measured *code* QA (matching the model's coder specialization) or *prose faithfulness* QA (the summarization/synthesis grading `eval_judge.py` actually does). A coder-specialized model may judge natural-language faithfulness differently than code correctness. Treat this as a *reasonable candidate* rather than a *validated swap* until confirmed.

**Calibration gate (must-pass before trusting fallback scores):** After the swap, run the judge against 5-10 known synthesis eval rows (mix of good and bad answers) and spot-check that scores directionally align with expectations. Fixture source: the eval-synthesis harness reads from its default row set (controlled by `CONVMEM_EVAL_SYNTHESIS_ROWS` env var or the built-in fixture path). If no fixture exists yet, assemble 5-10 rows manually before running this gate. If scores are nonsensical, fall back to `ornith:9b` as next candidate.

**File:** `eval_judge.py:84-96`

```python
# Current (line 96):
return str(models.get("summarize_model", "llama3.1:8b")), False

# New:
return str(models.get("judge_fallback_model", "qwen2.5-coder:14b")), False
```

**Also:** Treat fallback-model scores as low-confidence/informational by default — not just when non-independent. A weak judge is weak in general, not specifically weak-relative-to-strong-model-output. `low_confidence` is derivable from `deepseek_active`; use a property on `JudgeResult` rather than a stored field that can drift:

```python
@property
def low_confidence(self) -> bool:
    return not self._deepseek_active
```

### 2. Upgrade judge prompt + add confidence field (single pass) — `eval_judge.py`

**Why:** Claude's review says merge tasks 2 and 3 into one prompt-template edit — less parser churn, one negative-control re-check instead of two. The underlying trick (force reasoning before scoring) transfers from Arena-Hard even though the pairwise structure doesn't.

**What:** Single pass over `_JUDGE_PROMPT` and `_parse_score()` to add:
- "Reason before scoring" step (generate reference summary of source → compare → score)
- Optional `CONFIDENCE: low|med|high` line (defensive parser — weaker models less reliable at format-following)

**File:** `eval_judge.py:27-56` and `eval_judge.py:99-110`

New `_JUDGE_PROMPT`:
```
{rubric}

Step 1: Summarize what the source says in 1-2 sentences.
Step 2: Compare the model output to the source. Does the output faithfully reflect the source?
Step 3: Score 1-5.

Respond with EXACTLY these lines:
REFERENCE: <your 1-2 sentence summary of the source>
SCORE: <integer 1-5>
REASON: <one sentence>
CONFIDENCE: low|med|high
```

**Defensive `_parse_score()` rules (must-fix #3):**
- `REFERENCE:` line: optional — if missing, reason fallback uses first sentence of output
- `SCORE:` line: required — if missing, score is `None`
- `REASON:` line: required — if missing, fall back to last line of output
- `CONFIDENCE:` line: **strictly optional** — if missing, parser returns `None` for confidence; the override logic in `judge()` later sets it to `"low"` for fallback models. Must not silently misparse REASON as CONFIDENCE.

Parser should handle:
- Missing CONFIDENCE line (most likely from weak models)
- Extra lines before/after the expected format
- Lines in wrong order (regex-based extraction, not position-based)

### 3. Add `confidence` field to `JudgeResult` — `eval_judge.py:59-74`

```python
@dataclass
class JudgeResult:
    score: int | None
    reason: str
    independent: bool
    judge_model: str
    under_test_model: str
    confidence: str | None  # "low" | "med" | "high" | None (unparsed)
    _deepseek_active: bool  # private, feeds low_confidence property

    @property
    def low_confidence(self) -> bool:
        """True when using local fallback model (non-DeepSeek)."""
        return not self._deepseek_active

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "reason": self.reason,
            "independent": self.independent,
            "judge_model": self.judge_model,
            "under_test_model": self.under_test_model,
            "confidence": self.confidence,
            "low_confidence": self.low_confidence,
        }
```

In `judge()`: when not using DeepSeek, override `confidence` to `"low"` if it wasn't already parsed.

### 4. Soften the gain estimates in the analysis doc

**File:** `docs/inter-model/CRUSH-2026-08-07-judge-bench-analysis.md`

- Add the pairwise-vs-absolute caveat at the top of the Gap Analysis section
- Replace "+25-30 combined" with a note that gains are directionally expected but uncalibrated for our task
- Update the Q2 recommendation to reference `qwen2.5-coder:14b` (benchmarked, with the evidence caveat) instead of `ornith:9b`/`qwen3.6:35b` (speculative)

### 5. Update tests

- `tests/test_eval_methodology.py` — `FakeJudgeResult` needs `confidence`, `low_confidence`, `_deepseek_active`
- `tests/test_doctor.py:223-228` — the inline judge call snippet may need updating for new prompt format
- `tests/test_ask_trace.py` — check if eval_trace expectations need `confidence`

---

## What NOT to do (Claude's cautions)

- **Don't add pairwise comparison.** Our task is absolute grading, not A-vs-B.
- **Don't cite Arena-Hard's +12pt figure** as the expected gain for our prompt change — different mechanism, different task.
- **Don't treat "+25-30 combined" as a target.** Directionally suggestive, not calibrated.
- **Don't over-index on self-judging bias for the fallback model.** The problem with `llama3.1:8b` isn't self-judging — it's general weakness.
- **Don't add multi-agent/panel judging.** ChatEval got 34% on JudgeBench — worse than single-agent.
- **Don't store `low_confidence` as an independent field** — it's derivable from `_deepseek_active`; use a property to prevent drift.

---

## Files to modify (summary)

| File | Change | Priority |
|------|--------|----------|
| `eval_judge.py:84-96` | Swap fallback to `qwen2.5-coder:14b`; pass `_deepseek_active` to JudgeResult | 1 |
| `eval_judge.py:27-56` | Single-pass prompt upgrade: reason-before-scoring + REFERENCE + CONFIDENCE lines | 2 |
| `eval_judge.py:59-74` | Add `confidence`, `_deepseek_active`, `low_confidence` property to `JudgeResult` | 2 |
| `eval_judge.py:99-110` | Defensive `_parse_score()` — CONFIDENCE strictly optional, regex-based extraction | 2 |
| `eval_judge.py:113-166` | `judge()`: override confidence to `"low"` when `deepseek_active=False` | 2 |
| `docs/inter-model/CRUSH-2026-08-07-judge-bench-analysis.md` | Soften gain estimates; add pairwise/absolute caveat; fix Q2 rec with evidence caveat | 4 |
| `tests/test_eval_methodology.py` | Update `FakeJudgeResult` with new fields | 5 |
| `tests/test_doctor.py:223-228` | Update inline judge snippet if needed | 5 |

---

## Verification (must-fix #2: negative-control re-check is the regression risk)

After implementation, run in this order:

```bash
cd /home/lauer/Projects/convmem

# 1. Unit tests (plumbing)
python -m pytest tests/test_eval_methodology.py tests/test_doctor.py -x -q

# 2. CRITICAL: negative controls must still fail closed under new prompt
#    Run both with DeepSeek (API) and local fallback to confirm known-false
#    synthesis still scores < 3 in both paths. under_test_model stays constant
#    (the model that *would* produce the output being judged); only the judge
#    model changes between calls. Setting it to the fallback model name would
#    create a self-judging pair (judge_model == under_test_model), which
#    convmem's independence check correctly flags as informational-only —
#    defeating the gate.
python -c "
from config import load_config
from eval_methodology import run_judge_negative_control
import os

cfg = load_config()
models = cfg.get('models', {})
under_test = models.get('summarize_model', 'llama3.1:8b')

# DeepSeek path
rc = run_judge_negative_control('synthesis', under_test_model=under_test, cfg=cfg)
print(f'DeepSeek negative control: passed={rc[\"passed\"]} score={rc[\"score\"]} model={rc[\"judge_model\"]}')

# Local fallback path (unset DEEPSEEK_API_KEY temporarily)
key = os.environ.pop('DEEPSEEK_API_KEY', None)
rc2 = run_judge_negative_control('synthesis', under_test_model=under_test, cfg=cfg)
if key: os.environ['DEEPSEEK_API_KEY'] = key
print(f'Local fallback negative control: passed={rc2[\"passed\"]} score={rc2[\"score\"]} model={rc2[\"judge_model\"]}')

# Confirm the two runs actually used different judge models
assert rc['judge_model'] != rc2['judge_model'], \
    f'Both runs used same judge model ({rc[\"judge_model\"]}) — env key may not have been set'
print('OK: different judge models confirmed')
"

# 3. Spot-check calibration (must-pass gate from task 1)
#    Fixture: use existing eval-synthesis rows (the harness reads from
#    CONVMEM_EVAL_SYNTHESIS_ROWS or its default fixture path). If no fixture
#    exists yet, assemble 5-10 known synthesis rows (mix of good/bad answers)
#    before running this gate.
python scripts/eval-synthesis.py --judge 2>&1 | head -40
```

**Gate:** Negative controls must pass for both paths AND the two runs must use different judge models. If the new prompt breaks negative-control detection (score ≥ 3 on known-false), revert and iterate on the prompt format.
