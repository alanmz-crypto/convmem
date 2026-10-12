"""Config-derived watch source paths without importing ingest or watch."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from file_generation_contract import canonical_source_path


def eligible_watch_source_paths(cfg: Mapping[str, Any]) -> list[str]:
    watch_cfg = cfg.get("watch") or {}
    base = watch_cfg.get("paths") or (cfg.get("sources") or {}).get("paths") or []
    extra = watch_cfg.get("extra_paths") or []
    paths = [str(p) for p in list(base) + list(extra)]
    canonical: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        try:
            resolved = canonical_source_path(raw)
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        canonical.append(resolved)
    return canonical
