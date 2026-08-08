"""No-Chroma import guard for the JudgeBench semantic calibration package.

JudgeBench offline semantic calibration must never reach into Chroma stores,
the read-only Chroma adapter, or the live ask pipeline. This static AST guard
fails the suite if any module under ``eval_judgebench/`` imports
``chroma_store``, ``chroma_readonly``, or ``ask`` (directly, or as a dotted
path segment).

Defense in depth: the contracts/validators already avoid Chroma; this guard is
the regression tripwire so a future edit can't silently wire one in.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "eval_judgebench"

FORBIDDEN = {"chroma_store", "chroma_readonly", "ask"}


def _iter_judgebench_py_files() -> list[Path]:
    return sorted(PKG.rglob("*.py"))


def _forbidden_segment(names: list[str]) -> list[str]:
    """Return forbidden bare names present in an import alias name list."""
    return [n for n in names if n in FORBIDDEN]


def _dotted_segments_full(name: str) -> list[str]:
    """Split a dotted import path into its modules (yes, even mid-path)."""
    return list(name.split("."))


def scan_forbidden_imports() -> list[tuple[str, str]]:
    """Return [(module_file, offending_import)] for any forbidden import."""
    hits: list[tuple[str, str]] = []
    for py in _iter_judgebench_py_files():
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError:
            # A broken source module is reported elsewhere; do not hide it.
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    segs = _dotted_segments_full(alias.name)
                    if _forbidden_segment(segs):
                        hits.append((str(py), f"import {alias.name}"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                segs = _dotted_segments_full(module)
                if _forbidden_segment(segs):
                    hits.append((str(py), f"from {module} import ..."))
                for alias in node.names:
                    if alias.name in FORBIDDEN:
                        shown = module or f"{alias.name}"
                        hits.append((str(py), f"from {module} import {alias.name}"))
    return hits


class NoChromaImportGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hits = scan_forbidden_imports()

    def test_no_chroma_or_ask_imports_in_judgebench_package(self):
        self.assertEqual(
            self.hits,
            [],
            "eval_judgebench imports a forbidden module (chroma_store / "
            f"chroma_readonly / ask): {self.hits}",
        )

    def test_package_modules_are_importable(self):
        # Sanity: the guarded package exists and has source files to scan.
        files = _iter_judgebench_py_files()
        self.assertTrue(files, "eval_judgebench package has no .py files to guard")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    unittest.main()
