#!/usr/bin/env python3
"""JudgeBench offline semantic calibration dry-run.

Loads the frozen semantic-v1 corpus, runs identity preflight, and captures the
comparison signature. By default no live semantic judge is invoked (empty corpus
or ``--no-invoke``). Chroma is prohibited in this path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS = REPO / "eval_corpus/fixtures/judgebench/semantic-v1"
DEFAULT_REGISTRY = REPO / "eval_corpus/fixtures/judgebench/identity-registry-v1.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="JudgeBench offline semantic calibration")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--under-test-model", required=True)
    parser.add_argument(
        "--no-invoke",
        action="store_true",
        help="Skip live semantic judge calls (default when corpus has zero cases)",
    )
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help="Allow non-cross_family independence (skip canonical preflight)",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    from config import load_config
    from eval_judgebench.runner import run_judgebench
    from eval_model_identity import CanonicalPreflightError

    cfg = load_config()
    try:
        result = run_judgebench(
            args.corpus,
            cfg=cfg,
            judge_model=args.judge_model,
            under_test_model=args.under_test_model,
            registry_path=args.registry,
            semantic_judge=None if args.no_invoke else None,
            canonical=not args.exploratory,
        )
    except CanonicalPreflightError as exc:
        print(f"preflight refused: {exc}", file=sys.stderr)
        return 1

    summary = {
        "case_count": len(result.cases),
        "independence_class": result.independence_class.value,
        "pinned_judge_model": result.pinned_judge_model,
        "gold_hash_unchanged": result.gold_hash_before == result.gold_hash_after,
        "comparison_signature_digest": result.provenance.get("comparison_signature_digest"),
    }
    print(json.dumps(summary, indent=2))
    for case in result.cases:
        inv = case.invocation
        status = inv.status.value if inv else "missing"
        agree = case.agrees_with_gold
        print(f"  case {case.case_id}: mechanical={case.mechanical.passed} j1={status} agree={agree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
