"""Validate or review a JudgeBench corpus package without invoking a judge."""

# The repository root must be added before importing the local package.
# pylint: disable=wrong-import-position

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_judgebench.corpus_validate import read_jsonl, validate_corpus

DEFAULT_CORPUS = (
    Path(__file__).resolve().parent.parent
    / "eval_corpus/fixtures/judgebench/semantic-v1"
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--require-locked",
        action="store_true",
        help="fail unless every gold row carries Ryan's locked status",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="print a compact case/split/verdict review table",
    )
    return parser


def _print_review(corpus: Path) -> None:
    cases = read_jsonl(corpus / "cases.jsonl")
    gold = {
        str(row.get("case_id")): row for row in read_jsonl(corpus / "gold.jsonl")
    }
    print("case_id\tsplit\ttask\tj0\tj1\tlock\ttags")
    for case in cases:
        case_id = str(case["case_id"])
        gold_row = gold.get(case_id, {})
        print(
            "\t".join(
                [
                    case_id,
                    str(case.get("split", "")),
                    str(case.get("task_kind", "")),
                    str((gold_row.get("j0") or {}).get("expected_pass", "")),
                    str((gold_row.get("j1") or {}).get("verdict", "")),
                    str((gold_row.get("lock") or {}).get("status", "")),
                    ",".join(case.get("tags") or []),
                ]
            )
        )


def main() -> int:
    args = _parser().parse_args()
    result = validate_corpus(args.corpus, require_locked=args.require_locked)
    if args.review:
        _print_review(args.corpus)
    if not result.valid:
        for violation in result.violations:
            print(f"FAIL: {violation}", file=sys.stderr)
        return 1
    print(
        "PASS: "
        f"cases={result.case_count} calibration={result.calibration_count} "
        f"holdout={result.holdout_count} lock={result.lock_status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
