"""Narrow production path grants for the default-off incremental JSONL route.

The tokenized IsolationBoundary is for hermetic test workers. This boundary
validates the selected live source and exact mutable roles without modifying
that test contract or granting a whole home/data directory for writes.
"""

# The boundary keeps each granted role explicit for auditability.
# pylint: disable=too-many-instance-attributes

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from config import CONFIG_PATH, IncrementalJsonlConfigError, incremental_jsonl_settings
from incremental_jsonl_isolation import (
    IsolationViolation,
    open_source_readonly,
    validate_regular_source,
)


def _checked_path(raw: Path | str, *, label: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise IsolationViolation(f"{label} must be absolute")
    path = path.absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise IsolationViolation(f"{label} contains a symlink: {current}")
    return path.resolve(strict=False)


def _inside(path: Path, root: Path) -> bool:
    return path.is_relative_to(root)


class ProductionBoundary:
    """Validate one source and the coordinator's exact production data roles."""

    def __init__(
        self,
        cfg: Mapping[str, Any],
        source: Path | str,
        *,
        config_path: Path | str = CONFIG_PATH,
    ) -> None:
        settings = incremental_jsonl_settings(cfg)
        if not settings.enabled:
            raise IsolationViolation("incremental production route is disabled")
        self.source = _checked_path(source, label="source")
        if str(self.source) not in settings.live_sources:
            raise IsolationViolation("source lacks an exact live grant")
        self.config_path = _checked_path(config_path, label="config")
        index = cfg.get("index")
        if not isinstance(index, Mapping):
            raise IncrementalJsonlConfigError("invalid_index", "index table missing")
        try:
            self.chroma = _checked_path(index["chroma_dir"], label="chroma")
            self.processed = _checked_path(index["processed_log"], label="processed")
            self.export = _checked_path(index["units_export"], label="export")
        except KeyError as exc:
            raise IncrementalJsonlConfigError(
                "missing_index_path", f"required index path missing: {exc.args[0]}"
            ) from exc
        self.state = _checked_path(settings.state_dir, label="incremental state")
        self.data_root = self.chroma.parent
        if self.data_root == Path(self.data_root.anchor):
            raise IsolationViolation("production data root is filesystem root")
        for label, path in (
            ("processed", self.processed),
            ("export", self.export),
            ("incremental state", self.state),
        ):
            if not _inside(path, self.data_root) or path == self.data_root:
                raise IsolationViolation(f"{label} is outside production data root")
        if _inside(self.source, self.data_root) or _inside(self.data_root, self.source):
            raise IsolationViolation("source overlaps mutable production data")
        if _inside(self.state, self.chroma) or _inside(self.chroma, self.state):
            raise IsolationViolation("incremental state overlaps Chroma")
        if len({self.chroma, self.processed, self.export, self.state}) != 4:
            raise IsolationViolation("production data roles overlap")

        locks = _checked_path(self.data_root / "locks", label="writer locks")
        attest = _checked_path(self.data_root / "writer_attestations", label="writer attestations")
        census = _checked_path(self.data_root / "writer_census", label="writer census")
        self._layout = {
            "user_config": self.config_path,
            "chroma": self.chroma,
            "processed": self.processed,
            "export": self.export,
            "state": self.state,
            "dedupe": self.data_root,
            "locks": locks,
            "attest": attest,
            "census": census,
        }
        self._exact_roles = {
            self.chroma,
            self.processed,
            self.export,
            self.data_root,
            locks,
            attest,
            census,
            self.data_root / "dedupe_queue.jsonl",
            self.data_root / "ingest_duplicate_suppressions.jsonl",
        }
        for label, path in self._layout.items():
            _checked_path(path, label=label)
        for path in self._exact_roles:
            if path != self.data_root and _inside(path, self.state):
                raise IsolationViolation("incremental state overlaps another data role")
        fd = open_source_readonly(self.source)
        try:
            validate_regular_source(fd, expected_uid=os.getuid())
        finally:
            os.close(fd)

    @property
    def layout(self) -> dict[str, Path]:
        return dict(self._layout)

    def resolve_source(self, path: Path | str, *, label: str) -> Path:
        candidate = _checked_path(path, label=label)
        if candidate != self.source:
            raise IsolationViolation("source differs from exact live grant")
        return candidate

    def resolve_mutable(self, path: Path | str, *, label: str) -> Path:
        candidate = _checked_path(path, label=label)
        if candidate in self._exact_roles or _inside(candidate, self.state):
            return candidate
        raise IsolationViolation(f"{label} outside granted production role: {candidate}")
