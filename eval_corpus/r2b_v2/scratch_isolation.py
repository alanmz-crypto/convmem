"""Scratch-path isolation guards for I4–I6 hermetic execution."""

from __future__ import annotations

from pathlib import Path

from chroma_write_store import DEFAULT_ATTEST_DIR, DEFAULT_WRITER_LOCK
from eval_corpus.run_manifest import path_is_temp_contained


class ScratchIsolationError(RuntimeError):
    """Scratch transaction attempted to touch production state."""


_PRODUCTION_MARKERS = (
    str(DEFAULT_WRITER_LOCK),
    str(DEFAULT_ATTEST_DIR),
    "/.local/share/convmem/eval/",
)


def _is_under_temp(path: Path) -> bool:
    return path_is_temp_contained(path)


def assert_scratch_source_paths(
    export: Path | str,
    processed: Path | str,
    chroma_dir: Path | str,
) -> None:
    """Validate export/processed/chroma paths for scratch execution."""
    assert_scratch_paths(
        ("export", export),
        ("processed", processed),
        ("chroma_dir", chroma_dir),
    )


def assert_scratch_transaction_path_dict(
    auth_dir: Path,
    paths: dict[str, str],
) -> None:
    """Validate all packet paths for scratch execution."""
    assert_scratch_paths(
        ("auth_dir", auth_dir),
        ("export", paths["export"]),
        ("processed", paths["processed"]),
        ("chroma_dir", paths["chroma_dir"]),
        ("capture_dir", paths["capture_dir"]),
    )


def assert_scratch_path(path: Path | str, *, label: str) -> Path:
    """Require path under tempfile and absent from production markers."""
    p = Path(path).expanduser()
    text = str(p)
    for marker in _PRODUCTION_MARKERS:
        if marker in text and not _is_under_temp(p):
            raise ScratchIsolationError(
                f"{label} resolves to production marker {marker!r}: {text}"
            )
    if not _is_under_temp(p):
        raise ScratchIsolationError(
            f"{label} must be under tempfile root for scratch execution: {text}"
        )
    return p


def assert_scratch_paths(*labeled_paths: tuple[str, Path | str]) -> None:
    for label, path in labeled_paths:
        assert_scratch_path(path, label=label)


def assert_scratch_transaction_paths(
    *,
    paths: dict[str, str],
    auth_dir: Path,
    root: Path | None = None,
) -> None:
    """Validate all scratch transaction paths stay under tempfile."""
    labeled: list[tuple[str, Path | str]] = []
    if root is not None:
        labeled.append(("root", root))
    assert_scratch_transaction_path_dict(auth_dir, paths)
    if labeled:
        assert_scratch_paths(*labeled)
