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


def eval_row(row: dict, cfg: dict, *, use_judge: bool) -> dict:
    from ask import ask
    from eval_grading import grade_answer

    # evidence=False mirrors the CLI `ask` default and gives better topical
    # recall for a synthesis-quality eval (evidence rerank force-prepends recent
    # decisions, which buries topic-specific targets).
    out = ask(row["question"], top_k=6, evidence=False)
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

        context = row["question"] + "\n\n" + "\n\n".join(
            (c.get("title") or "") + " " + (str(c.get("ledger_id") or ""))
            for c in (out.get("citations") or [])
        )
        jr = judge(
            "synthesis",
            context,
            answer,
            under_test_model=_synth_model(cfg),
            cfg=cfg,
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
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    from config import load_config
    from eval_provenance import EXIT_OK, classify, model_context

    cfg = load_config()
    rows = load_golden(args.golden)
    results = [eval_row(r, cfg, use_judge=args.judge) for r in rows]
    report = summarize_report(results, use_judge=args.judge)
    report["provenance"] = model_context(cfg, _synth_model(cfg), args.golden)

    print(f"Golden answers: {report['count']}")
    print(f"Pass rate: {report['pass_rate']:.2%}")
    print(f"Abstain control correct: {report['abstain_correct']}")
    if args.judge:
        indep = report.get("judge_independent")
        tag = "INDEPENDENT" if indep else "NON-INDEPENDENT (informational only)"
        print(f"Judge mean: {report.get('judge_mean')} [{tag}] model={report.get('judge_model')}")
    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"  [{mark}] {r['id']} ({r['mode']}) cites={r['n_citations']} {r['detail']}")

    if args.update_baseline:
        args.baseline.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote baseline {args.baseline}")
        return EXIT_OK

    if not args.baseline.is_file():
        print(f"\nNo baseline at {args.baseline} — run with --update-baseline", file=sys.stderr)
        return 1

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    regressed = report["pass_rate"] < baseline.get("pass_rate", 0)
    if (
        report.get("judge_independent")
        and baseline.get("judge_independent")
        and report.get("judge_mean") is not None
        and baseline.get("judge_mean") is not None
        and report["judge_mean"] < baseline["judge_mean"]
    ):
        regressed = True

    code, msg = classify(
        regressed=regressed,
        current_ctx=report["provenance"],
        baseline_ctx=baseline.get("provenance", {}),
    )
    print(f"\n{msg}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
