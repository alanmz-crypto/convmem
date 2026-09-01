"""Fail-closed checks for common provider credential formats.

The scanner intentionally reports pattern names only. It never prints matched
text, because this command runs in developer hooks and CI logs.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable


PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "DeepSeek API key",
        re.compile(r"(?<![A-Za-z0-9])sk-[0-9A-Fa-f]{32}(?![A-Za-z0-9])"),
    ),
    (
        "GitHub personal access token",
        re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9_]{20,}(?![A-Za-z0-9])"),
    ),
    (
        "AWS access key ID",
        re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])"),
    ),
    (
        "Slack token",
        re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{20,}(?![A-Za-z0-9])"),
    ),
    (
        "private key material",
        re.compile(r"-{5}BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-{5}"),
    ),
)


def find_secret_types(text: str) -> tuple[str, ...]:
    """Return matched provider-pattern labels without returning secret text."""
    return tuple(label for label, pattern in PATTERNS if pattern.search(text))


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git command failed"
        raise RuntimeError(detail)
    return result.stdout


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("not inside a Git repository")
    return Path(result.stdout.strip())


def _staged_additions(repo: Path) -> Iterable[str]:
    diff = _git(
        repo,
        "diff",
        "--cached",
        "--no-ext-diff",
        "--no-color",
        "--unified=0",
        "--binary",
    )
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            yield line[1:]


def _range_additions(repo: Path, base: str, head: str) -> Iterable[str]:
    diff = _git(
        repo,
        "diff",
        base,
        head,
        "--no-ext-diff",
        "--no-color",
        "--unified=0",
        "--binary",
    )
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            yield line[1:]


def _tracked_tree(repo: Path) -> Iterable[str]:
    paths = _git(repo, "ls-files", "-z").split("\0")
    for relative in paths:
        if not relative:
            continue
        path = repo / relative
        try:
            yield path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeError(
                f"unable to read tracked path {relative!r}: {exc}"
            ) from exc


def _scan(texts: Iterable[str]) -> set[str]:
    found: set[str] = set()
    for text in texts:
        found.update(find_secret_types(text))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan repository content without printing matches"
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--staged", action="store_true", help="scan staged additions (default)"
    )
    modes.add_argument("--tree", action="store_true", help="scan tracked files")
    modes.add_argument(
        "--diff-range",
        nargs=2,
        metavar=("BASE", "HEAD"),
        help="scan additions between two Git revisions",
    )
    args = parser.parse_args(argv)

    try:
        repo = _repo_root()
        if args.tree:
            texts = _tracked_tree(repo)
            scope = "tracked tree"
        elif args.diff_range:
            texts = _range_additions(repo, *args.diff_range)
            scope = f"diff {args.diff_range[0]}..{args.diff_range[1]}"
        else:
            texts = _staged_additions(repo)
            scope = "staged additions"
        found = sorted(_scan(texts))
    except RuntimeError as exc:
        print(f"Secret scan error: {exc}", file=sys.stderr)
        return 2

    if not found:
        print(f"Secret scan passed ({scope}); matched text was not emitted.")
        return 0

    print(
        "Secret scan blocked: "
        + ", ".join(found)
        + f" pattern(s) detected in {scope}; matched text was not emitted.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
