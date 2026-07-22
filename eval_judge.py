"""LLM-as-judge for eval harnesses — independence-aware, advisory only.

The judge grades summarization/synthesis output on a 1-5 rubric. It is *advisory*:
callers use deterministic checks as the hard gate and treat judge scores as
supporting signal.

Independence policy (see docs plan "Model quality eval harness"):
  - A judge whose weights == the model under test is grading its own output.
    Its blind spots correlate with the thing it's judging, so its score is
    demoted to informational-only and MUST NOT feed regression-gate decisions.
  - `judge()` returns ``independent: False`` in that case. Independence is
    decided structurally: ``judge_model != under_test_model``.
  - With a DeepSeek key set, the judge runs on DeepSeek; when the model under
    test is the local ``llama3.1:8b`` (summarization / local synth fallback),
    that judge is independent. We deliberately do NOT require a second local
    model just for judging (shared-VRAM cost is disproportionate for an
    advisory score) — instead we flag non-independence honestly.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from llm import generate

_JUDGE_RUBRIC = {
    "summary": (
        "You are grading a SUMMARY of an AI coding conversation against the source excerpt.\n"
        "Score 1-5 on faithfulness + specificity:\n"
        "  5 = every claim is supported by the excerpt and specific (tools, files, decisions).\n"
        "  3 = broadly correct but vague or missing key specifics.\n"
        "  1 = unsupported, hallucinated, or uselessly generic.\n"
    ),
    "synthesis": (
        "You are grading an ANSWER synthesized from retrieved excerpts.\n"
        "Score 1-5 on groundedness + relevance:\n"
        "  5 = every claim is traceable to a retrieved excerpt and directly answers the question.\n"
        "  3 = mostly grounded but drifts or leaves the question partly unanswered.\n"
        "  1 = ungrounded, invented, or off-topic.\n"
    ),
}

_JUDGE_PROMPT = """{rubric}
Respond with EXACTLY two lines and nothing else:
SCORE: <integer 1-5>
REASON: <one sentence>

--- INPUT UNDER TEST ---
{source_label}:
{source}

MODEL OUTPUT:
{output}
"""


@dataclass
class JudgeResult:
    score: int | None
    reason: str
    independent: bool
    judge_model: str
    under_test_model: str

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "reason": self.reason,
            "independent": self.independent,
            "judge_model": self.judge_model,
            "under_test_model": self.under_test_model,
        }


def resolve_deepseek_key() -> str:
    """DEEPSEEK_API_KEY from os.environ, then ~/.config/convmem/env.{local,systemd}."""
    from config import resolve_deepseek_key as _resolve

    return _resolve()


def resolve_judge_model(cfg: dict) -> tuple[str, bool]:
    """Return (judge_model, deepseek_active).

    Prefer the DeepSeek distill model when a key is available; otherwise fall
    back to the local summarize model (same weights as the local generators).
    """
    models = cfg.get("models") or {}
    key = resolve_deepseek_key()
    if key:
        # Make the key visible to llm.generate for this process.
        os.environ.setdefault("DEEPSEEK_API_KEY", key)
        return str(models.get("distill_model", "deepseek-v4-flash")), True
    return str(models.get("summarize_model", "llama3.1:8b")), False


def _parse_score(text: str) -> tuple[int | None, str]:
    score: int | None = None
    reason = ""
    m = re.search(r"SCORE:\s*([1-5])", text, re.IGNORECASE)
    if m:
        score = int(m.group(1))
    r = re.search(r"REASON:\s*(.+)", text, re.IGNORECASE)
    if r:
        reason = r.group(1).strip()
    if not reason:
        reason = text.strip().splitlines()[-1][:200] if text.strip() else "no reason"
    return score, reason


def judge(
    kind: str,
    source: str,
    output: str,
    *,
    under_test_model: str,
    cfg: dict,
) -> JudgeResult:
    """Grade ``output`` against ``source`` on a 1-5 rubric.

    Args:
        kind: "summary" or "synthesis" (selects the rubric).
        source: the excerpt (summary eval) or question+context (synthesis eval).
        output: the model output being graded.
        under_test_model: the model that produced ``output`` — used to decide
            independence. Judge is independent iff its model differs.
        cfg: loaded convmem config.

    Returns a JudgeResult. ``independent=False`` scores are informational only
    and must never feed regression-gate decisions.
    """
    if kind not in _JUDGE_RUBRIC:
        raise ValueError(f"unknown judge kind: {kind!r}")

    models = cfg.get("models") or {}
    judge_model, _deepseek = resolve_judge_model(cfg)
    independent = judge_model.strip() != (under_test_model or "").strip()

    source_label = "SOURCE EXCERPT" if kind == "summary" else "QUESTION + RETRIEVED EXCERPTS"
    prompt = _JUDGE_PROMPT.format(
        rubric=_JUDGE_RUBRIC[kind],
        source_label=source_label,
        source=source[:8000],
        output=output[:8000],
    )
    try:
        raw = generate(
            prompt,
            model=judge_model,
            ollama_host=models.get("ollama_host", "http://localhost:11434"),
            deepseek_base_url=models.get("deepseek_base_url", "https://api.deepseek.com"),
            timeout=120,
        )
        score, reason = _parse_score(raw)
    except Exception as exc:  # judge is advisory — never break the eval
        score, reason = None, f"judge error: {type(exc).__name__}: {exc}"

    return JudgeResult(
        score=score,
        reason=reason,
        independent=independent,
        judge_model=judge_model,
        under_test_model=(under_test_model or "").strip(),
    )


def aggregate(results: list[JudgeResult]) -> dict:
    """Mean judge score + independence flag for a batch.

    ``independent`` is True only if EVERY graded item used an independent judge;
    a mixed or all-self-graded batch is reported as non-independent so the
    scorecard/baseline logic keeps it out of gating.
    """
    scored = [r.score for r in results if r.score is not None]
    judge_mean = round(sum(scored) / len(scored), 3) if scored else None
    independent = bool(results) and all(r.independent for r in results)
    return {
        "judge_mean": judge_mean,
        "judge_independent": independent,
        "judge_n": len(scored),
        "judge_model": results[0].judge_model if results else None,
    }
