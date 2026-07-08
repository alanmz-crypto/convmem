"""Planning Guide Contract — single source of truth for doctor enforcement."""

from __future__ import annotations

from pathlib import Path

CONTRACT_VERSION = "v1"
PROBE_VERSION = "v1"

REQUIRED_HEADINGS: tuple[str, ...] = (
    "## Phase Initialization",
    "## Objective",
    "## Responsibilities",
    "## Exit Criteria",
)

REQUIRED_METADATA: tuple[str, ...] = (
    "Phase",
    "Characters",
    "Functions",
    "Lanes",
    "Authority",
)

HITL_STOP_MARKERS: tuple[str, ...] = (
    "Cursor must stop here.",
    "Await HITL.",
)

# Guides under docs/planning/ checked by doctor (CONTRACT.md is meta, not a guide).
GUIDE_GLOB = "*.md"
CONTRACT_FILENAME = "CONTRACT.md"


def planning_guides_dir(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent
    return base / "docs" / "planning"


def iter_guide_paths(root: Path | None = None) -> list[Path]:
    guides_dir = planning_guides_dir(root)
    if not guides_dir.is_dir():
        return []
    paths = sorted(guides_dir.glob(GUIDE_GLOB))
    return [p for p in paths if p.name != CONTRACT_FILENAME]


def validate_planning_guides(root: Path | None = None) -> list[str]:
    """Return human-readable violations of Planning Guide Contract v1."""
    base = root or Path(__file__).resolve().parent
    paths = iter_guide_paths(base)
    if not paths:
        return ["no planning guides found under docs/planning/"]
    problems: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            problems.append(f"{path.name}: unreadable ({exc})")
            continue
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                problems.append(f"{path.name}: missing heading {heading!r}")
        for marker in HITL_STOP_MARKERS:
            if marker not in text:
                problems.append(f"{path.name}: missing HITL marker {marker!r}")
        init_idx = text.find("## Phase Initialization")
        init_slice = text[init_idx : init_idx + 2500] if init_idx >= 0 else ""
        for field in REQUIRED_METADATA:
            if field not in init_slice:
                problems.append(f"{path.name}: missing metadata field {field!r} in Phase Initialization")
    return problems
