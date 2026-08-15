"""AST fitness check for direct Chroma/storage read boundaries.

CG-1 does not wire these production callers.  The frozen inventory makes every
new direct constructor, raw vector query, or direct Chroma-SQLite connection an
explicit classification decision before CG-2 activation.
"""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (path, function, operation) -> (expected occurrences, classification)
EXPECTED = {
    ("chroma_readonly.py", "_connect_readonly", "sqlite3.connect[chroma]"): (
        1,
        "core-storage",
    ),
    ("chroma_store.py", "open_chroma_for_read", "ChromaStore"): (1, "core-storage"),
    ("chroma_store.py", "open_chroma_for_verify", "ChromaStore"): (1, "core-storage"),
    ("chroma_store.py", "__init__", "PersistentClient"): (1, "core-storage"),
    ("chroma_store.py", "query_summaries", "raw.query"): (1, "core-storage"),
    ("chroma_store.py", "query_units", "raw.query"): (2, "core-storage"),
    ("chroma_write_store.py", "open_chroma_for_write", "ChromaStore"): (
        1,
        "stable-governed-infrastructure",
    ),
    (
        "complete_data_restore.py",
        "chroma_logical_snapshot",
        "sqlite3.connect[chroma]",
    ): (1, "excluded-administrative"),
    ("complete_data_restore.py", "_validate_imports", "sqlite3.connect[chroma]"): (
        1,
        "excluded-administrative",
    ),
    ("convmem.py", "monitor_command", "ChromaStore"): (1, "excluded-administrative"),
    ("eval_corpus/capture.py", "_connect_readonly", "sqlite3.connect[chroma]"): (
        1,
        "excluded-administrative",
    ),
    ("eval_corpus/shadow_build.py", "run_shadow_build", "PersistentClient"): (
        1,
        "excluded-administrative",
    ),
    ("file_generation_store.py", "__init__", "ChromaStore"): (1, "generation-mediated"),
    (
        "mixed_mode_control.py",
        "build_authority_clean_control",
        "ChromaStore",
    ): (1, "generation-mediated"),
    (
        "mixed_mode_proof.py",
        "run_mixed_mode_proof",
        "ChromaStore",
    ): (1, "generation-mediated"),
    (
        "mixed_mode_retrieval.py",
        "query_units_mixed_ann",
        "raw.query",
    ): (1, "generation-mediated"),
    (
        "cg2_rehearsal.py",
        "run_legacy_gateway_rehearsal",
        "ChromaStore",
    ): (1, "generation-mediated"),
    (
        "file_generation_validate.py",
        "chroma_sequence_positions",
        "sqlite3.connect[chroma]",
    ): (1, "generation-mediated"),
    ("scripts/chroma_orphan_inventory.py", "_raw_query", "raw.query"): (
        1,
        "excluded-administrative",
    ),
    (
        "scripts/chroma_restore_drill.py",
        "fingerprint_logical",
        "sqlite3.connect[chroma]",
    ): (1, "excluded-administrative"),
    ("shadow_canary.py", "_prepare_validation_fixture", "ChromaStore"): (
        1,
        "excluded-administrative",
    ),
    ("shadow_canary.py", "_run_workload", "ChromaStore"): (
        1,
        "excluded-administrative",
    ),
    ("shadow_canary.py", "worker", "ChromaStore"): (1, "excluded-administrative"),
    ("shadow_replay.py", "open_replay_store", "ChromaStore"): (
        1,
        "excluded-administrative",
    ),
}


# AST hooks retain Python's visitor API spelling.
# pylint: disable=invalid-name
class _BoundaryVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        relative: str,
        text: str,
        discovered: Counter[tuple[str, str, str]],
    ) -> None:
        self.relative = relative
        self.text = text
        self.discovered = discovered
        self.contexts: list[str] = []

    def visit_FunctionDef(self, node):
        self.contexts.append(node.name)
        self.generic_visit(node)
        self.contexts.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        kind = None
        if isinstance(node.func, ast.Name) and node.func.id in {
            "ChromaStore",
            "PersistentClient",
        }:
            kind = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr == "PersistentClient":
                kind = "PersistentClient"
            elif node.func.attr == "query":
                kind = "raw.query"
            elif (
                node.func.attr == "connect"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "sqlite3"
                and "chroma.sqlite3" in self.text
            ):
                kind = "sqlite3.connect[chroma]"
        if kind:
            context = self.contexts[-1] if self.contexts else "<module>"
            self.discovered[(self.relative, context, kind)] += 1
        self.generic_visit(node)


def _discover() -> Counter[tuple[str, str, str]]:
    discovered: Counter[tuple[str, str, str]] = Counter()
    for path in sorted(ROOT.rglob("*.py")):
        if "tests" in path.parts or any(part.startswith(".") for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not any(
            token in text
            for token in (
                "ChromaStore",
                "chromadb",
                "chroma_store",
                "chroma_readonly",
                "chroma.sqlite3",
            )
        ):
            continue
        tree = ast.parse(text, filename=str(path))
        _BoundaryVisitor(
            relative=path.relative_to(ROOT).as_posix(),
            text=text,
            discovered=discovered,
        ).visit(tree)
    return discovered


def test_all_direct_chroma_read_boundaries_are_explicitly_classified() -> None:
    discovered = _discover()
    expected_counts = Counter({key: value[0] for key, value in EXPECTED.items()})
    assert discovered == expected_counts
    assert {classification for _, classification in EXPECTED.values()} == {
        "generation-mediated",
        "excluded-administrative",
        "stable-governed-infrastructure",
        "core-storage",
    }
