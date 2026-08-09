#!/usr/bin/env python3
"""Evaluate ask/synthesis answer quality against golden_answers.jsonl.

Hard gate = deterministic checks: must_include facts present, inline [n]
citations exist when required and are within range (no hallucinated cites), and
correct abstention on the negative-control rows. Optional `--judge` adds an
advisory groundedness score; a non-independent judge (same weights as the
synthesizer) is surfaced but NEVER feeds the regression gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
GOLDEN = FIXTURES / "golden_answers.jsonl"
BASELINE = FIXTURES / "golden_answers_baseline.json"


def load_golden(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _synth_model(cfg: dict) -> str:
    """The model that actually produced the answer (for judge independence).

    Mirrors ask.py / llm.generate_stream: deepseek distill model when a key is
    present, else the local fallback. Delegates the swap to
    ``llm._resolve_fallback_model`` so the provider-fallback decision (and its
    warn-once / CONVMEM_FAIL_ON_FALLBACK behavior) lives in one place.
    """
    import os

    import llm

    models = cfg["models"]
    distill = models.get("distill_model", "deepseek-v4-flash")
    if "deepseek-v4" in distill and not os.environ.get("DEEPSEEK_API_KEY"):
        return llm._resolve_fallback_model(distill)
    return distill


def eval_row(row: dict, cfg: dict, *, use_judge: bool, legacy: bool) -> dict:
    from ask import ask
    from eval_grading import grade_answer

    # evidence=False mirrors the CLI `ask` default and gives better topical
    # recall for a synthesis-quality eval (evidence rerank force-prepends recent
    # decisions, which buries topic-specific targets).
    out = ask(
        row["question"],
        top_k=6,
        evidence=False,
        return_eval_trace=use_judge,
    )
    answer = out["answer"]
    n_cites = len(out.get("citations") or [])
    grade = grade_answer(
        answer,
        n_citations=n_cites,
        must_include=row.get("must_include") or [],
        must_cite=bool(row.get("must_cite")),
        should_abstain=bool(row.get("should_abstain")),
    )
    result = {
        "id": row.get("id"),
        "pass": grade["pass"],
        "mode": grade["mode"],
        "n_citations": n_cites,
        "detail": {k: v for k, v in grade.items() if k not in ("pass", "mode")},
        "answer": answer,
    }
    if use_judge and not row.get("should_abstain"):
        from eval_judge import judge

        eval_trace = out.get("eval_trace") or {}
        context = (
            f"Question: {eval_trace.get('question', row['question'])}\n\n"
            f"Retrieved excerpts:\n{eval_trace.get('context', '')}"
        )
        jr = judge(
            "synthesis",
            context,
            answer,
            under_test_model=(eval_trace.get("model") or _synth_model(cfg)),
            cfg=cfg,
            legacy=legacy,
        )
        result["judge"] = jr.to_dict()
    return result


def summarize_report(results: list[dict], *, use_judge: bool) -> dict:
    from eval_judge import JudgeResult, aggregate

    n = len(results) or 1
    report = {
        "count": len(results),
        "pass_rate": round(sum(1 for r in results if r["pass"]) / n, 4),
        "abstain_correct": all(
            r["pass"] for r in results if r["mode"] == "abstain"
        ),
        "results": results,
    }
    if use_judge:
        jrs = [
            JudgeResult(
                score=r["judge"]["score"],
                reason=r["judge"]["reason"],
                independent=r["judge"]["independent"],
                judge_model=r["judge"]["judge_model"],
                under_test_model=r["judge"]["under_test_model"],
                confidence=r["judge"].get("confidence"),
            )
            for r in results
            if "judge" in r
        ]
        report.update(aggregate(jrs))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden synthesis/ask eval")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--judge", action="store_true", help="Add advisory LLM-judge score")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Explicitly opt into the legacy 1-5 judge path (required with --judge)",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    from config import load_config
    from eval_methodology import (
        enforce_legacy_judge_gate,
        exit_if_judge_negative_control_failed,
        finalize_eval_against_baseline,
        print_judge_summary,
    )
    from eval_provenance import model_context

    legacy_exit = enforce_legacy_judge_gate(args.judge, args.legacy)
    if legacy_exit is not None:
        return legacy_exit

    cfg = load_config()
    rows = load_golden(args.golden)
    results = [eval_row(r, cfg, use_judge=args.judge, legacy=args.legacy) for r in rows]
    report = summarize_report(results, use_judge=args.judge)
    synth_model = _synth_model(cfg)
    report["provenance"] = model_context(cfg, synth_model, args.golden)
    if args.judge:
        from eval_methodology import run_judge_negative_control

        report["negative_control"] = run_judge_negative_control(
            "synthesis", under_test_model=synth_model, cfg=cfg, legacy=True
        )

    print(f"Golden answers: {report['count']}")
    print(f"Pass rate: {report['pass_rate']:.2%}")
    print(f"Abstain control correct: {report['abstain_correct']}")
    if args.judge:
        print_judge_summary(report)
    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"  [{mark}] {r['id']} ({r['mode']}) cites={r['n_citations']} {r['detail']}")

    nc_exit = exit_if_judge_negative_control_failed(args.judge, report)
    if nc_exit is not None:
        return nc_exit

    return finalize_eval_against_baseline(
        baseline_path=args.baseline,
        update_baseline=args.update_baseline,
        report=report,
        metric_key="pass_rate",
    )


if __name__ == "__main__":
    raise SystemExit(main())
