"""Shared helpers for exclude --purge unit tests."""

from __future__ import annotations

from pathlib import Path


def purge_cfg(td: Path) -> dict:
    return {
        "index": {
            "processed_log": str(td / "processed.json"),
            "units_export": str(td / "knowledge_units.jsonl"),
            "chroma_dir": str(td / "chroma"),
        }
    }
