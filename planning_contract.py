"""Planning Guide Contract — single source of truth for doctor enforcement."""

from __future__ import annotations

from pathlib import Path

CONTRACT_VERSION = "v2"
PROBE_VERSION = "v2"

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
    "Probe Version",
)

HITL_STOP_MARKERS: tuple[str, ...] = (
    "Active phase lane must stop here.",
    "Await HITL.",
)


def probe_version_row() -> str:
    """Exact Phase Initialization table row for the current probe version."""
    return f"| **Probe Version** | {PROBE_VERSION} |"


# Guides under docs/planning/ checked by doctor (meta files excluded).
GUIDE_GLOB = "*.md"
CONTRACT_FILENAME = "CONTRACT.md"
EXECUTION_CLOSURE_PREFIX = "EXECUTION-CLOSURE"


def _is_meta_planning_doc(name: str) -> bool:
    if name == CONTRACT_FILENAME:
        return True
    if name.startswith(EXECUTION_CLOSURE_PREFIX):
        return True
    return False


def planning_guides_dir(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent
    return base / "docs" / "planning"


def iter_guide_paths(root: Path | None = None) -> list[Path]:
    guides_dir = planning_guides_dir(root)
    if not guides_dir.is_dir():
        return []
    paths = sorted(guides_dir.glob(GUIDE_GLOB))
    return [p for p in paths if not _is_meta_planning_doc(p.name)]


def validate_planning_guides(root: Path | None = None) -> list[str]:
    """Return human-readable violations of Planning Guide Contract v2."""
    base = root or Path(__file__).resolve().parent
    paths = iter_guide_paths(base)
    if not paths:
        return ["no planning guides found under docs/planning/"]
    problems: list[str] = []
    probe_row = probe_version_row()
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
        if init_slice and probe_row not in init_slice:
            problems.append(
                f"{path.name}: Probe Version value must be {PROBE_VERSION!r} "
                f"in Phase Initialization (expected row {probe_row!r})"
            )
    return problems
