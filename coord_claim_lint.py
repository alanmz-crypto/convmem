"""Lint inter-model markdown for unsigned status claims in verdict sections.

EXPERIMENTAL / OPTIONAL — not default protocol.
Primary: brief stale alarm + convmem propose_decision -i.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VERDICT_HEADINGS = frozenset({"## state", "## decision", "## verdict"})
DECISION_ID = re.compile(r"dec_prop_[0-9a-z_]+", re.I)
# High-confidence cross-model status claims (not casual prose).
VERDICT_PHRASE = re.compile(
    r"\b(soak\s+)?passed\b|"
    r"\bsigned\s+off\b|"
    r"\bwatch\s+stability:\s*signed\b|"
    r"\bverdict:\s*.*\bpassed\b|"
    r"\b(?:status|soak)\s*:\s*passed\b",
    re.I,
)


def lint_inter_model_text(text: str, *, path: str = "") -> list[str]:
    """Return human-readable violation messages.

    Each line in State/Decision/Verdict that matches a verdict phrase must
  carry dec_prop_* on that same line (no paragraph-level exemption).
    """
    violations: list[str] = []
    section: str | None = None

    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("## "):
            section = stripped.lower()
            continue
        if section not in VERDICT_HEADINGS:
            continue
        if not stripped:
            continue
        if VERDICT_PHRASE.search(raw) and not DECISION_ID.search(raw):
            violations.append(
                f"{path}:{line_no}: verdict claim without dec_prop_* on this line "
                f"in {section}: {stripped[:80]}"
            )

    return violations


def lint_path(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"{path}: cannot read: {e}"]
    return lint_inter_model_text(text, path=str(path))


def is_inter_model_path(path: Path) -> bool:
    parts = path.parts
    return "inter-model" in parts and path.suffix == ".md" and path.name not in (
        "README.md",
        "LATEST.md",
    )


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    paths = [Path(p) for p in args] if args else []
    if not paths:
        print("coord_claim_lint: no files", file=sys.stderr)
        return 0

    violations: list[str] = []
    for path in paths:
        if not is_inter_model_path(path):
            continue
        violations.extend(lint_path(path))

    if violations:
        print("Coordination claim lint failed:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(
            "  Fix: add dec_prop_* on the same line or use propose_decision pipeline.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
