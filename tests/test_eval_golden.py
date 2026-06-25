"""Golden evaluation harness (P1b).

Reads tests/fixtures/golden_questions.jsonl, runs each query against the live
convmem CLI, and grades the output. No LLM — just ledger_id / substring
presence in top-N search results or CLI stdout.

Pass bar: ≥ 8/10 before adding MCP tools (P2).
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "golden_questions.jsonl"
PASS_BAR = 8
TIMEOUT = 60  # seconds per query
SEARCH_DEFAULT_TOP = 5


def load_questions(path: Path = FIXTURE) -> list[dict]:
    questions: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            questions.append(json.loads(line))
    return questions


def run_convmem(args: list[str], *, timeout: int = TIMEOUT) -> tuple[str, int]:
    """Run `convmem <args>`, return (stdout+stderr, exit_code)."""
    cmd = [sys.executable, "-m", "convmem"] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    return (result.stdout + result.stderr), result.returncode


def grade_search(output: str, expected: str, top_n: int = 3) -> tuple[bool, str]:
    """Check that expected substring appears in the first N result panels.

    We split the output by Rich panel boundaries: each result panel starts
    with a box-drawing header like '╭─ [N]' or '┌─ [N]'. Count panels and
    check that `expected` appears before panel top_n+1.
    """
    lines = output.split("\n")
    panel_boundaries: list[int] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("╭─", "┌─", "╔─")) and "]  " in stripped:
            panel_boundaries.append(i)

    if not panel_boundaries:
        return False, "no result panels found in output"

    # The search text spans from panel_start to next panel_start (or end).
    effective_n = min(top_n, len(panel_boundaries))
    end_of_top = (
        panel_boundaries[effective_n]
        if effective_n < len(panel_boundaries)
        else len(lines)
    )

    top_slice = "\n".join(lines[panel_boundaries[0] : end_of_top])
    if expected in top_slice:
        return True, f"found in top {effective_n} results"
    return False, f"not found in top {effective_n} results"


def grade_stdout(output: str, expected: str) -> tuple[bool, str]:
    if expected in output:
        return True, f"'{expected[:60]}' found"
    return False, f"'{expected[:60]}' not found in output"


class GoldenEvalTests(unittest.TestCase):
    def test_golden_questions(self):
        questions = load_questions()
        passed = 0
        failed = 0
        lines: list[str] = []
        lines.append(
            f"\nGolden eval — {len(questions)} questions (pass bar: ≥{PASS_BAR}/10)\n"
        )

        for q in questions:
            qid = q["id"]
            qtype = q["type"]
            desc = q.get("query") or " ".join(q.get("args", []))
            expected = q["value"]

            with self.subTest(q=f"Q{qid:02d} {qtype}: {desc[:50]}"):
                if qtype == "search":
                    top_n = q.get("top_n", SEARCH_DEFAULT_TOP)
                    output, rc = run_convmem(["search", q["query"], "--top", str(top_n)])
                    ok, detail = grade_search(output, expected, top_n=top_n)
                elif qtype == "unresolved":
                    output, rc = run_convmem(["unresolved"] + q.get("args", []))
                    ok, detail = grade_stdout(output, expected)
                elif qtype == "related":
                    output, rc = run_convmem(["related"] + q.get("args", []))
                    ok, detail = grade_stdout(output, expected)
                elif qtype == "brief":
                    output, rc = run_convmem(["brief"] + q.get("args", []))
                    ok, detail = grade_stdout(output, expected)
                else:
                    ok, detail = False, f"unknown question type: {qtype}"

                status = "✓" if ok else "✗"
                marker = "PASS" if ok else "FAIL"
                report_line = f"  [{status}] Q{qid:02d} ({qtype}): {desc[:64]}"
                if not ok:
                    report_line += f"\n        {detail}"
                lines.append(report_line)

                if ok:
                    passed += 1
                else:
                    failed += 1

                self.assertTrue(ok, f"Q{qid:02d}: {detail}")

        lines.append(
            f"\n  Result: {passed}/{len(questions)} passed, {failed} failed"
        )
        if passed >= PASS_BAR:
            lines.append(f"  ✓ Meets pass bar ({PASS_BAR}+)")
        else:
            lines.append(f"  ✗ Below pass bar ({PASS_BAR}+ required)")

        report = "\n".join(lines)
        print(report, file=sys.stderr)

        if passed < PASS_BAR:
            self.fail(
                f"Golden eval: {passed}/{len(questions)} below pass bar of {PASS_BAR}. "
                "See stderr for details."
            )


if __name__ == "__main__":
    unittest.main()
