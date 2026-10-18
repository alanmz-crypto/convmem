"""Publication site catalog for T2 evidence mapping (Arc #286)."""

from __future__ import annotations

ATOMIC_STAGES = (
    "before_tmp_write",
    "before_tmp_fsync",
    "before_replace",
    "after_replace",
    "before_dir_fsync",
    "after_dir_fsync",
)

APPEND_STAGES = (
    "before_append",
    "before_file_fsync",
    "before_dir_fsync",
    "after_dir_fsync",
)

PUBLICATION_SITES = {
    "initial_authority": {"kind": "atomic", "stages": ATOMIC_STAGES},
    "recovery_authority": {"kind": "atomic", "stages": ATOMIC_STAGES},
    "progress_authority": {"kind": "atomic", "stages": ATOMIC_STAGES},
    "terminal_receipt": {"kind": "atomic", "stages": ATOMIC_STAGES},
    "terminal_authority": {"kind": "atomic", "stages": ATOMIC_STAGES},
    "journal_mirror": {"kind": "append", "stages": APPEND_STAGES},
    "v2_permit": {"kind": "append", "stages": APPEND_STAGES},
}


def all_barrier_stage_names() -> list[str]:
    names: list[str] = []
    for site, spec in PUBLICATION_SITES.items():
        for stage in spec["stages"]:
            names.append(f"{site}.{stage}")
    return names
