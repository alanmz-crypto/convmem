#!/usr/bin/env python3
"""Evaluate summarization quality against golden_summaries.jsonl.

Hard gate = deterministic structural checks (3 sentences + Keywords 5-8, no
banned vague phrases, must_mention present) and keyword recall. Optional
`--judge` adds an advisory faithfulness score; a non-independent judge score
(same weights as the summarizer) is surfaced but NEVER feeds the regression gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
GOLDEN = FIXTURES / "golden_summaries.jsonl"
BASELINE = FIXTURES / "golden_summaries_baseline.json"


def load_golden(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def eval_row(row: dict, cfg: dict, *, use_judge: bool) -> dict:
    from eval_grading import grade_summary, keyword_recall
    from llm import summarize

    models = cfg["models"]
    summarize_model = models.get("summarize_model", "llama3.1:8b")
    excerpt = row["source_excerpt"]
    summary = summarize(
        excerpt,
        summarize_model,
        models["ollama_host"],
        models.get("deepseek_base_url", "https://api.deepseek.com"),
    )
    grade = grade_summary(summary, must_mention=row.get("must_mention") or [])
    recall = keyword_recall(summary, row.get("must_include_keywords") or [])
    out = {
        "id": row.get("id"),
        "structural_pass": grade["structural_pass"],
        "keyword_recall": round(recall, 3),
        "n_sentences": grade["n_sentences"],
        "n_keywords": grade["n_keywords"],
        "missing_mentions": grade["missing_mentions"],
        "summary": summary,
    }
    if use_judge:
        from eval_judge import judge

        jr = judge(
            "summary",
            excerpt,
            summary,
            under_test_model=summarize_model,
            cfg=cfg,
        )
        out["judge"] = jr.to_dict()
    return out


def summarize_report(results: list[dict], *, use_judge: bool) -> dict:
    from eval_judge import JudgeResult, aggregate

    n = len(results) or 1
    report = {
        "count": len(results),
        "structural_pass_rate": round(sum(1 for r in results if r["structural_pass"]) / n, 4),
        "keyword_recall": round(sum(r["keyword_recall"] for r in results) / n, 4),
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
    parser = argparse.ArgumentParser(description="Golden summarization eval")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--judge", action="store_true", help="Add advisory LLM-judge score")
    parser.add_argument(
        "--structural-min", type=float, default=None,
        help="Override [eval].summary_structural_min pass threshold",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    from config import load_config
    from eval_provenance import EXIT_OK, classify, model_context

    cfg = load_config()
    rows = load_golden(args.golden)
    results = [eval_row(r, cfg, use_judge=args.judge) for r in rows]
    report = summarize_report(results, use_judge=args.judge)

    summarize_model = cfg["models"].get("summarize_model", "llama3.1:8b")
    report["provenance"] = model_context(cfg, summarize_model, args.golden)

    print(f"Golden summaries: {report['count']}")
    print(f"Structural pass rate: {report['structural_pass_rate']:.2%}")
    print(f"Keyword recall: {report['keyword_recall']:.2%}")
    if args.judge:
        indep = report.get("judge_independent")
        tag = "INDEPENDENT" if indep else "NON-INDEPENDENT (informational only)"
        print(f"Judge mean: {report.get('judge_mean')} [{tag}] model={report.get('judge_model')}")
    for r in results:
        mark = "PASS" if r["structural_pass"] else "FAIL"
        extra = "" if r["structural_pass"] else (
            f" (sent={r['n_sentences']}, kw={r['n_keywords']}, "
            f"missing={r['missing_mentions']})"
        )
        print(f"  [{mark}] {r['id']} recall={r['keyword_recall']:.0%}{extra}")

    if args.update_baseline:
        args.baseline.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote baseline {args.baseline}")
        return EXIT_OK

    if not args.baseline.is_file():
        print(f"\nNo baseline at {args.baseline} — run with --update-baseline", file=sys.stderr)
        return 1

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    # Regression = structural pass rate dropped below baseline (deterministic gate).
    # Judge mean is compared ONLY when independent — otherwise informational.
    regressed = report["structural_pass_rate"] < baseline.get("structural_pass_rate", 0)
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
