# Codex handoff — JudgeBench-driven judge upgrades (approved, ready to implement)

**From:** Crush (literature review + plan drafting) → Claude (3-round review, approved)
**To:** Codex (implementation)
**Date:** 2026-08-07
**Status:** ✅ **COMPLETED — implemented by Crush (Codex sandbox blocked shell) and merged as PR #153 (`bfb5b7e`, 2026-08-09)**. All 5 tasks landed; calibration gate passed; pylint gate PASS; 89 targeted tests pass. Retain as implementation reference for future judge work.
**Literature:** Tan, Zhuang, Montgomery et al. — *"JudgeBench: A Benchmark for Evaluating LLM-based Judges"* (ICLR 2025, UC Berkeley / WashU)

---

## What this is

We reviewed convmem's LLM judge (`eval_judge.py`) against the JudgeBench literature and found our Vanilla-style prompted judge is ~2 generations behind SOTA. Claude reviewed the analysis and plan across 3 rounds — all must-fix conditions are incorporated, plan is approved.

This handoff contains everything needed to implement: task list with code-level detail, verification script, and what NOT to do.

---

## Context (5 Ws)

**Who:** Crush did the literature review and drafted the plan. Claude (cloud, advisory lane) reviewed across 3 rounds and approved. Codex implements.

**What:** Three targeted upgrades to `eval_judge.py`'s LLM judge: swap the local fallback model, upgrade the prompt to reason-before-scoring, add a confidence field. Plus doc updates and test fixes.

**When:** Now — the plan is approved with no blockers. Branch `plan/2026-08-07-2026-08-07-judge-bench-analysis` is pushed.

**Why:** Our current judge setup has two problems:
- Local fallback model `llama3.1:8b` scores 40.9% on JudgeBench — near-random. A structurally "independent" judge that's just bad at the task passes the independence check and still produces noise.
- Vanilla prompt (one-pass 1-5 rubric, no reasoning step) is the weakest prompt style tested. The underlying trick of forcing the judge to reason before committing to a score is a known anti-laziness technique.

**How:** Three changes to `eval_judge.py`, one doc edit, test updates. All changes are surgical — no new files, no new dependencies, no architecture changes.

---

## Key caveat (read first)

JudgeBench measures **pairwise preference accuracy** (pick correct from a contrastive pair). Our judge does **absolute single-item 1-5 grading** (grade one output against a rubric). These are related but distinct — calibrated absolute judgment is harder than forced-choice discrimination. The paper's specific point-gain numbers (+10-12, +15-20) are directionally right (reasoning models and better prompts help both tasks) but the magnitudes are **unvalidated for our task**. Do not treat them as calibrated targets.

---

## Related files (read these before editing)

| File | Lines | What it does |
|------|-------|-------------|
| `eval_judge.py` | 185 | Judge implementation: prompt, model selection, scoring, aggregation |
| `eval_methodology.py` | 62 | Negative controls (known-false outputs must score <3) |
| `llm.py:250-267` | 18 | `generate()` — the actual LLM call path the judge uses |
| `tests/test_eval_methodology.py` | ~130 | Tests for negative controls and FakeJudgeResult |
| `tests/test_doctor.py:223-228` | 6 | Doctor probe verifying judge wiring in eval scripts |

---

## Implementation tasks

### Task 1: Replace local fallback model

**File:** `eval_judge.py:84-96`

**Current code (line 96):**
```python
return str(models.get("summarize_model", "llama3.1:8b")), False
```

**Replace with:**
```python
return str(models.get("judge_fallback_model", "qwen2.5-coder:14b")), False
```

**Evidence caveat:** The Aug 4 Crush session benchmarked `qwen2.5-coder:14b` on "QA judgment tests" with professional results, but it's unclear whether those tests measured *code* QA (matching the model's coder specialization) or *prose faithfulness* QA (what `eval_judge.py` actually does — grading summarization/synthesis faithfulness). Treat this as a reasonable candidate, not a validated swap. The calibration gate in verification will catch if it's wrong.

**Also add `_deepseek_active` to JudgeResult:** The `resolve_judge_model()` function returns `(judge_model, deepseek_active)`. Currently `judge()` at line 138 unpacks only the model name — save the boolean too and pass it to `JudgeResult` for the `low_confidence` property (task 3).

---

### Task 2: Upgrade judge prompt + add confidence field (single pass)

**File:** `eval_judge.py:27-56` (`_JUDGE_PROMPT`) and `eval_judge.py:99-110` (`_parse_score()`)

**Replace `_JUDGE_PROMPT` (lines 45-56) with:**
```python
_JUDGE_PROMPT = """{rubric}

Step 1: Summarize what the source says in 1-2 sentences.
Step 2: Compare the model output to the source. Does the output faithfully reflect the source?
Step 3: Score 1-5.

Respond with EXACTLY these lines:
REFERENCE: <your 1-2 sentence summary of the source>
SCORE: <integer 1-5>
REASON: <one sentence>
CONFIDENCE: low|med|high
"""
```

**Replace `_parse_score()` (lines 99-110) with defensive parser:**

```python
def _parse_score(text: str) -> tuple[int | None, str, str | None]:
    """Parse SCORE, REASON, and optional CONFIDENCE from judge output.

    CONFIDENCE is strictly optional — weaker models may drop it. The parser
    uses regex-based extraction (not position-based) so line order doesn't
    matter. Must not silently misparse REASON as CONFIDENCE.
    """
    score: int | None = None
    reason = ""
    confidence: str | None = None

    m = re.search(r"SCORE:\s*([1-5])", text, re.IGNORECASE)
    if m:
        score = int(m.group(1))

    r = re.search(r"REASON:\s*(.+)", text, re.IGNORECASE)
    if r:
        reason = r.group(1).strip()
    if not reason:
        reason = text.strip().splitlines()[-1][:200] if text.strip() else "no reason"

    c = re.search(r"CONFIDENCE:\s*(low|med|high)", text, re.IGNORECASE)
    if c:
        confidence = c.group(1).lower()

    return score, reason, confidence
```

**Update callers:** `_parse_score()` now returns 3 values instead of 2. In `judge()` at line 156, update:
```python
# Old:
score, reason = _parse_score(raw)
# New:
score, reason, parsed_confidence = _parse_score(raw)
```

---

### Task 3: Add `confidence` and `low_confidence` to `JudgeResult`

**File:** `eval_judge.py:59-74`

**Replace the `JudgeResult` dataclass with:**
```python
@dataclass
class JudgeResult:
    score: int | None
    reason: str
    independent: bool
    judge_model: str
    under_test_model: str
    confidence: str | None  # "low" | "med" | "high" | None (unparsed)
    _deepseek_active: bool = False  # private, feeds low_confidence property

    @property
    def low_confidence(self) -> bool:
        """True when using local fallback model (non-DeepSeek).

        Derivative of _deepseek_active — not an independent stored field
        to prevent the two from drifting out of sync.
        """
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

**Update `judge()` (lines 113-166):** After the `resolve_judge_model()` call, save `deepseek_active` and pass it to `JudgeResult`. After parsing, override confidence for fallback models:

```python
# At line 138 — save deepseek_active:
judge_model, deepseek_active = resolve_judge_model(cfg)

# After parsing (around line 156) — override confidence for fallback:
if parsed_confidence is None and not deepseek_active:
    parsed_confidence = "low"

# At line 160 — pass _deepseek_active to JudgeResult:
return JudgeResult(
    score=score,
    reason=reason,
    independent=independent,
    judge_model=judge_model,
    under_test_model=(under_test_model or "").strip(),
    confidence=parsed_confidence,
    _deepseek_active=deepseek_active,
)
```

**Check `resolve_judge_model` return unpacking:** At line 138, currently:
```python
judge_model, _deepseek = resolve_judge_model(cfg)
```
Change to:
```python
judge_model, deepseek_active = resolve_judge_model(cfg)
```

---

### Task 4: Soften gain estimates in the analysis doc

**File:** `docs/inter-model/CRUSH-2026-08-07-judge-bench-analysis.md`

- Add the pairwise-vs-absolute caveat at the top of the Gap Analysis section
- Replace "+25-30 combined" with: "Directionally expected but magnitudes are uncalibrated for our absolute-grading task"
- Update the Q2 recommendation section to reference `qwen2.5-coder:14b` (benchmarked, with evidence caveat) instead of `ornith:9b`/`qwen3.6:35b` (speculative)

---

### Task 5: Update tests

**File:** `tests/test_eval_methodology.py`

`FakeJudgeResult` needs the new fields. Find the class (around line 15-20) and add:
```python
confidence: str | None = None
_deepseek_active: bool = True
```

Add `low_confidence` as a property if the test expects it, or just set the field:
```python
low_confidence: bool = False
```

**File:** `tests/test_doctor.py:223-228`

The inline judge call snippet may need updating if it references the old 2-value return from `_parse_score()` or the old prompt format. Check that the snippet still matches reality.

**File:** `tests/test_ask_trace.py:221-225`

Check if `eval_trace` expectations need `confidence` or `low_confidence` fields added.

---

## What NOT to do

- **Don't add pairwise comparison.** Our task is absolute grading, not A-vs-B. The paper's position-swap methodology doesn't apply.
- **Don't cite Arena-Hard's +12pt figure** as the expected gain for our prompt change — different mechanism (pairwise vs. absolute), different task.
- **Don't treat "+25-30 combined" as a target.** Directionally suggestive, not calibrated.
- **Don't add multi-agent/panel judging.** ChatEval got 34% on JudgeBench — worse than single-agent.
- **Don't store `low_confidence` as an independent field** — use the property derived from `_deepseek_active`.
- **Don't make `CONFIDENCE` required in the parser** — weaker models are less reliable at instruction-following and more likely to drop optional lines.

---

## Verification (run in this order after all tasks)

```bash
cd /home/lauer/Projects/convmem

# 1. Unit tests (plumbing)
python -m pytest tests/test_eval_methodology.py tests/test_doctor.py -x -q

# 2. CRITICAL: negative controls must still fail closed under new prompt.
#    under_test stays constant (the model whose output is being graded);
#    only the judge model changes between calls. The assertion catches
#    silent env misconfiguration where both runs use the same judge.
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

# Local fallback path (pop DEEPSEEK_API_KEY to force fallback)
key = os.environ.pop('DEEPSEEK_API_KEY', None)
rc2 = run_judge_negative_control('synthesis', under_test_model=under_test, cfg=cfg)
if key: os.environ['DEEPSEEK_API_KEY'] = key
print(f'Local fallback negative control: passed={rc2[\"passed\"]} score={rc2[\"score\"]} model={rc2[\"judge_model\"]}')

# Confirm different judge models were used
assert rc['judge_model'] != rc2['judge_model'], \
    f'Both runs used same judge model ({rc[\"judge_model\"]}) — env key may not have been set'
print('OK: different judge models confirmed')
"

# 3. Spot-check calibration (must-pass gate from task 1).
#    Fixture: eval-synthesis harness reads from CONVMEM_EVAL_SYNTHESIS_ROWS
#    or its built-in default fixture path. Assemble 5-10 rows if none exist.
python scripts/eval-synthesis.py --judge 2>&1 | head -40
```

**Gate:** Negative controls must pass (score <3) for both paths, AND the two paths must use different judge models. If the new prompt breaks negative-control detection, revert and iterate on the prompt format.

---

## Claude's final notes (from round 3 approval)

> One thing worth knowing going in, not a blocker: popping `DEEPSEEK_API_KEY` only works if the DeepSeek client checks the env var at call time rather than caching credentials at import/module load. If it's cached, both negative-control runs would use the same judge and the new assert would catch it (and correctly fail the script) — so worst case here is a loud failure pointing at the real issue, not a silent pass. Worth confirming which behavior `resolve_judge_model()` actually has while you're in `eval_judge.py` for task 1 anyway.
