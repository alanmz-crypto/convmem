"""Scratch-path isolation guards for I4–I6 hermetic execution."""

from __future__ import annotations

import tempfile
from pathlib import Path

from chroma_write_store import DEFAULT_ATTEST_DIR, DEFAULT_WRITER_LOCK


class ScratchIsolationError(RuntimeError):
    """Scratch transaction attempted to touch production state."""


_PRODUCTION_MARKERS = (
    str(DEFAULT_WRITER_LOCK),
    str(DEFAULT_ATTEST_DIR),
    "/.local/share/convmem/eval/",
)


def _is_under_temp(path: Path) -> bool:
    try:
        resolved = path.expanduser().resolve(strict=False)
        temp_root = Path(tempfile.gettempdir()).resolve()
    except OSError:
        return False
    try:
        return resolved == temp_root or resolved.is_relative_to(temp_root)
    except (ValueError, AttributeError):
        prefix = str(temp_root)
        text = str(resolved)
        return text == prefix or text.startswith(prefix + "/")


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
