#!/usr/bin/env python3
"""Append-only evidence recorder for Portland baseline Agent-B sessions."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ActionRecord:
    action_number: int
    tool_class: str
    query_or_instruction: str
    output: str
    output_ref: str = ""
    agent_interpretation: str = ""


@dataclass
class QuestionEvidence:
    run_id: str
    condition: str
    question_id: str
    question_text: str
    session_id: str
    started_at: str
    completed_at: str = ""
    effort_budget_n: int = 5
    actions: list = field(default_factory=list)
    final_answer: str = ""
    source_path: str = ""
    source_class: str = ""
    action_count: int = 0
    outcome: str = ""  # correct | incorrect | budget-exhausted | incomplete


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Record or finalize Agent-B question evidence")
    sub = parser.add_subparsers(dest="cmd", required=True)

    start = sub.add_parser("start")
    start.add_argument("--run-id", required=True)
    start.add_argument("--condition", choices=["c0", "c1"], required=True)
    start.add_argument("--question-id", required=True)
    start.add_argument("--question", required=True)
    start.add_argument("--session-id", required=True)
    start.add_argument("--budget", type=int, default=5)
    start.add_argument("--evidence-dir", type=Path, required=True)

    act = sub.add_parser("action")
    act.add_argument("--evidence-file", type=Path, required=True)
    act.add_argument("--number", type=int, required=True)
    act.add_argument("--tool-class", required=True)
    act.add_argument("--query", required=True)
    act.add_argument("--output", default="")
    act.add_argument("--output-ref", default="")
    act.add_argument("--interpretation", default="")

    done = sub.add_parser("finalize")
    done.add_argument("--evidence-file", type=Path, required=True)
    done.add_argument("--final-answer", default="")
    done.add_argument("--source-path", default="")
    done.add_argument("--source-class", default="")
    done.add_argument("--outcome", required=True)

    args = parser.parse_args()

    if args.cmd == "start":
        ev = QuestionEvidence(
            run_id=args.run_id,
            condition=args.condition,
            question_id=args.question_id,
            question_text=args.question,
            session_id=args.session_id,
            started_at=utc_now(),
            effort_budget_n=args.budget,
        )
        args.evidence_dir.mkdir(parents=True, exist_ok=True)
        out = args.evidence_dir / f"{args.condition}_{args.question_id}.json"
        out.write_text(json.dumps(asdict(ev), indent=2) + "\n", encoding="utf-8")
        print(out)
        return 0

    data = json.loads(args.evidence_file.read_text(encoding="utf-8"))

    if args.cmd == "action":
        data["actions"].append(
            asdict(
                ActionRecord(
                    action_number=args.number,
                    tool_class=args.tool_class,
                    query_or_instruction=args.query,
                    output=args.output,
                    output_ref=args.output_ref,
                    agent_interpretation=args.interpretation,
                )
            )
        )
        data["action_count"] = len(data["actions"])
        args.evidence_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return 0

    data["final_answer"] = args.final_answer
    data["source_path"] = args.source_path
    data["source_class"] = args.source_class
    data["outcome"] = args.outcome
    data["completed_at"] = utc_now()
    data["action_count"] = len(data["actions"])
    args.evidence_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
