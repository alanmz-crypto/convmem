"""Versioned rubric loading for JudgeBench offline semantic calibration.

Rubrics live under a corpus root's ``rubrics/`` directory, named
``<rubric_id>.json``. Each carries its own ``id`` and ``version``. The loader
resolves a ``rubric_id`` to a parsed :class:`Rubric`; it errors on unknown ids.

No semantic inference here: the loader only resolves and returns the rubric
data. Judgments-of-judgments (justified vs unjustified abstention) live in the
validator (S6) and are driven by this rubric's data, not by code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class RubricNotFoundError(KeyError):
    """Raised when no rubric matches the requested ``rubric_id``."""

    def __init__(self, rubric_id: str, rubric_dir: Path):
        self.rubric_id = rubric_id
        self.rubric_dir = rubric_dir
        super().__init__(
            f"unknown rubric_id '{rubric_id}' (not found in {rubric_dir})"
        )


class RubricFormatError(ValueError):
    """Raised when a rubric file is missing required structural fields."""


@dataclass
class Rubric:
    id: str
    version: int
    task: str
    rules: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rubric":
        if not isinstance(data, dict):
            raise RubricFormatError("rubric must be a JSON object")
        try:
            rubric_id = data["id"]
            version = int(data["version"])
            task = data["task"]
        except KeyError as exc:
            raise RubricFormatError(
                f"rubric missing required field '{exc.args[0]}'"
            ) from exc
        except (TypeError, ValueError) as exc:
            raise RubricFormatError(
                f"rubric 'version' must be an integer, got {data.get('version')!r}"
            ) from exc
        rules = data.get("rules")
        if not isinstance(rules, dict):
            rules = {}
        return cls(id=rubric_id, version=version, task=task, rules=rules)


def rubric_path(rubric_dir: Path | str, rubric_id: str) -> Path:
    """The file path for a rubric id under a rubric directory."""
    return Path(rubric_dir) / f"{rubric_id}.json"


def load_rubric(rubric_dir: Path | str, rubric_id: str) -> Rubric:
    """Load and parse a versioned rubric; raise RubricNotFoundError if absent.

    The file must carry an ``id`` matching the requested ``rubric_id`` (a stale
    copy under the wrong name is refused rather than silently trusted).
    """
    path = rubric_path(rubric_dir, rubric_id)
    if not path.is_file():
        raise RubricNotFoundError(rubric_id, Path(rubric_dir))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RubricFormatError(
            f"rubric file not valid JSON: {path}: {exc}"
        ) from exc
    rubric = Rubric.from_dict(raw)
    if rubric.id != rubric_id:
        raise RubricFormatError(
            f"rubric file '{path}' declares id '{rubric.id}' but was loaded as "
            f"'{rubric_id}'"
        )
    return rubric
