# Implementation plan — JudgeBench-driven judge upgrades

**Based on:** Claude's review of `CRUSH-2026-08-07-judge-bench-analysis.md`
**Plan author:** Crush
**Date:** 2026-08-07
**Status:** ready for Claude implementation

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

**What:** Change the fallback in `resolve_judge_model()` from `llama3.1:8b` to `qwen2.5-coder:14b`. We already benchmarked this model on Aug 4 specifically for QA judgment quality — it fits 12GB VRAM and produced professional results. This is an evidence-backed swap, not speculation.

**File:** `eval_judge.py:84-96`

```python
# Current (line 96):
return str(models.get("summarize_model", "llama3.1:8b")), False

# New:
return str(models.get("judge_fallback_model", "qwen2.5-coder:14b")), False
```

**Also:** Treat fallback-model scores as low-confidence/informational by default — not just when non-independent. A weak judge is weak in general, not specifically weak-relative-to-strong-model-output. Add a `low_confidence: bool` field to `JudgeResult` that is `True` when `deepseek_active=False`.

### 2. Upgrade judge prompt to "reason before scoring" — `eval_judge.py`

**Why:** Arena-Hard's pairwise structure doesn't map cleanly to 1-5 grading, but the underlying trick — force the judge to generate/reason before committing to a score — is a known anti-laziness technique that transfers independently. The Arena-Hard name should not be cited as the expected payoff mechanism; it's a different mechanism producing an unknown gain.

**What:** Add a "generate a reference summary of the source, then score the candidate against it" step to `_JUDGE_PROMPT`. Keep the existing SCORE/REASON two-line output format.

**File:** `eval_judge.py:27-56`

New prompt structure:
```
{rubric}

Step 1: Summarize what the source says in 1-2 sentences.
Step 2: Compare the model output to the source. Does the output faithfully reflect the source?
Step 3: Score 1-5.

Respond with EXACTLY these lines:
REFERENCE: <your 1-2 sentence summary of the source>
SCORE: <integer 1-5>
REASON: <one sentence>
```

### 3. Add confidence field — `eval_judge.py`

**Why:** JudgeBench's own ceiling (~80% even for best reasoning models) confirms this is hard. A judge that can flag "low confidence" on ambiguous cases is more useful than one that forces a number every time. Cheap addition given the advisory-only posture already in place.

**What:** Extend the output format with an optional `CONFIDENCE: low|med|high` line. Add `confidence: str | None` to `JudgeResult`. When `deepseek_active=False` (local fallback), auto-set `confidence="low"` and `low_confidence=True`.

**File:** `eval_judge.py`

Changes:
- `_JUDGE_PROMPT`: add `CONFIDENCE: low/med/high` line after REASON
- `_parse_score()`: parse confidence field
- `JudgeResult`: add `confidence: str | None` field
- `judge()`: when not using DeepSeek, override confidence to "low"

### 4. Soften the gain estimates in the analysis doc

**Why:** The "+25-30 combined" number is a straight sum of two independently-measured ablations applied to a different task shape. No guarantee they're additive, and this is being applied to absolute grading not pairwise preference.

**What:** Edit `CRUSH-2026-08-07-judge-bench-analysis.md` to:
- Add the pairwise-vs-absolute caveat at the top of the Gap Analysis section
- Replace "+25-30 combined" with a note that gains are directionally expected but uncalibrated for our task
- Update the Q2 recommendation to reference `qwen2.5-coder:14b` (benchmarked) instead of `ornith:9b`/`qwen3.6:35b` (speculative)

**File:** `docs/inter-model/CRUSH-2026-08-07-judge-bench-analysis.md`

### 5. Update tests

**What:** After changes 1-3, update:
- `tests/test_eval_methodology.py` — `FakeJudgeResult` needs `confidence` and `low_confidence` fields
- `tests/test_doctor.py:223-228` — the inline judge call snippet may need updating
- `tests/test_ask_trace.py` — check if eval_trace expectations need `confidence`

---

## What NOT to do (Claude's cautions)

- **Don't add pairwise comparison.** Our task is absolute grading, not A-vs-B. The paper's position-swap methodology doesn't apply.
- **Don't cite Arena-Hard's +12pt figure** as the expected gain for our prompt change — different mechanism, different task.
- **Don't treat "+25-30 combined" as a target.** It's directionally suggestive, not calibrated.
- **Don't over-index on self-judging bias for the fallback model.** The problem with `llama3.1:8b` isn't that it's self-judging — it's that it's a bad judge at 40.9% accuracy on any task. Independence is a separate, real concern, but general judge weakness matters more here.
- **Don't add multi-agent/panel judging.** ChatEval got 34% on JudgeBench — worse than single-agent. Not worth the complexity.

---

## Files to modify (summary)

| File | Change | Priority |
|------|--------|----------|
| `eval_judge.py:84-96` | Swap fallback to `qwen2.5-coder:14b`; add `low_confidence` | 1 |
| `eval_judge.py:27-56` | Upgrade prompt to "reason before scoring" + REFERENCE line | 2 |
| `eval_judge.py:59-74` | Add `confidence` and `low_confidence` to `JudgeResult` | 3 |
| `eval_judge.py:99-110` | Parse `CONFIDENCE:` in `_parse_score()` | 3 |
| `eval_judge.py:113-166` | Override confidence to "low" when not using DeepSeek | 3 |
| `docs/inter-model/CRUSH-2026-08-07-judge-bench-analysis.md` | Soften gain estimates; add pairwise/absolute caveat; fix Q2 rec | 4 |
| `tests/test_eval_methodology.py` | Update `FakeJudgeResult` with new fields | 5 |
| `tests/test_doctor.py:223-228` | Update inline judge snippet if needed | 5 |

---

## Verification

After implementation, run:
```bash
cd /home/lauer/Projects/convmem
python -m pytest tests/test_eval_methodology.py tests/test_doctor.py -x -q
python scripts/eval-synthesis.py --judge  # spot-check judge still works
```
