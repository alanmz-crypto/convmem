"""Shadow config allowlist + data_dir query-time read audit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Keys that may differ between live and shadow configs (paths + embed model).
SHADOW_CONFIG_ALLOWLIST = frozenset(
    {
        ("index", "chroma_dir"),
        ("index", "processed_log"),
        ("index", "units_export"),
        ("sources", "inventory"),
        ("models", "embed_model"),
        ("models", "ollama_host"),
        ("eval", "retrieval_view"),
    }
)


def _flatten(cfg: dict, prefix: tuple[str, ...] = ()) -> dict[tuple[str, ...], Any]:
    out: dict[tuple[str, ...], Any] = {}
    for k, v in cfg.items():
        key = prefix + (str(k),)
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def config_diff_violations(live: dict, shadow: dict) -> list[str]:
    """Return human-readable violations when non-allowlisted keys differ."""
    a = _flatten(live)
    b = _flatten(shadow)
    keys = set(a) | set(b)
    violations: list[str] = []
    for key in sorted(keys):
        if a.get(key) == b.get(key):
            continue
        if key in SHADOW_CONFIG_ALLOWLIST:
            continue
        # Allow entirely new eval section keys under allowlisted retrieval_view only
        violations.append(
            f"unauthorized diff at {'.'.join(key)}: live={a.get(key)!r} shadow={b.get(key)!r}"
        )
    return violations


def query_time_data_dir_files() -> list[dict[str, str]]:
    """Enumerate data_dir(cfg)-derived files relevant to query closure.

    pending_decisions.jsonl is NOT read by query_units (Kiro verified) — documented
    as irrelevant to read-only query closure; no freeze required in shadow parents.
    """
    return [
        {
            "path_relative": "decisions-approved.jsonl",
            "reader": "propose_decision.approved_path / ledger_recent.approved_decision_hit / query._ledger_lookup_hits",
            "query_time": "yes",
            "disposition": "freeze_byte_identical_both_arms",
        },
        {
            "path_relative": "pending_decisions.jsonl",
            "reader": "propose_decision.queue_path (propose/approve/conflict only)",
            "query_time": "no",
            "disposition": "no_freeze_required",
            "rationale": (
                "Not in query_units closure; read only during propose/approve/"
                "conflict-event operations (Kiro execution-plan scope check)."
            ),
        },
        {
            "path_relative": "chroma/chroma.sqlite3",
            "reader": "chroma_readonly (SQLite mode=ro) + PersistentClient query under index.chroma_dir",
            "query_time": "yes",
            "disposition": "isolated_via_shadow_chroma_dir",
        },
    ]
