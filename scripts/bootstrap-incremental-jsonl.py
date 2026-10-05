#!/usr/bin/env python3
"""One-shot exact-source checkpoint bootstrap; never called by watch/ingest.

The grant file is a reviewed operational input, not self-authorization. Run
only after Ryan approves the named source, digest, chunk cap, backup, and paid
provider budget. This script does not edit live config or control the watcher.
"""

# The imports below follow the repo-root path insertion used by standalone scripts.
# ruff: noqa: I001
# The hyphenated script name follows scripts/ convention; exact int checks reject bool.
# pylint: disable=invalid-name,unidiomatic-typecheck

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.detect import detect_format  # pylint: disable=wrong-import-position
from adapters.kiro_session_jsonl import parse_complete_prefix  # pylint: disable=wrong-import-position
from config import CONFIG_PATH, load_config  # pylint: disable=wrong-import-position
from incremental_jsonl import IncrementalJsonlCoordinator  # pylint: disable=wrong-import-position
from incremental_jsonl_production import ProductionBoundary  # pylint: disable=wrong-import-position
from ingest import chunk_messages  # pylint: disable=wrong-import-position


def _read_grant(path: Path) -> dict:
    raw = path.expanduser().absolute()
    if raw.resolve(strict=True) != raw or raw.is_symlink():
        raise ValueError("grant path contains a symlink")
    info = raw.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("grant must be an owned regular file")
    if info.st_mode & 0o077:
        raise ValueError("grant must have mode 0600 or stricter")
    grant = json.loads(raw.read_text(encoding="utf-8"))
    if not isinstance(grant, dict):
        raise TypeError("grant must be a JSON object")
    required = {
        "source",
        "prefix_sha256",
        "complete_boundary",
        "max_chunks",
        "embed_dimension",
        "backup_snapshot",
    }
    if set(grant) != required:
        raise ValueError(f"grant must contain exactly {', '.join(sorted(required))}")
    for key in ("source", "prefix_sha256", "backup_snapshot"):
        if not isinstance(grant[key], str) or not grant[key].strip():
            raise ValueError(f"grant {key} must be a non-empty string")
    if len(grant["prefix_sha256"]) != 64:
        raise ValueError("grant prefix_sha256 must be a 64-character digest")
    try:
        int(grant["prefix_sha256"], 16)
    except ValueError as exc:
        raise ValueError("grant prefix_sha256 is not hexadecimal") from exc
    for key in ("complete_boundary", "max_chunks", "embed_dimension"):
        if type(grant[key]) is not int or grant[key] < 1:
            raise ValueError(f"grant {key} must be a positive integer")
    source = Path(grant["source"]).expanduser()
    if not source.is_absolute() or any(char in grant["source"] for char in "*?[]"):
        raise ValueError("grant source must be one exact absolute path")
    return grant


def _require_watcher_disabled() -> None:
    result = subprocess.run(
        ["systemctl", "--user", "show", "convmem-watch.service", "-p", "ActiveState", "-p", "UnitFileState"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if fields != {"ActiveState": "inactive", "UnitFileState": "disabled"}:
        raise RuntimeError("watcher must be inactive and disabled before bootstrap")


def bootstrap(grant: dict) -> dict:
    """Apply one reviewed grant; return counters for the operator receipt."""
    _require_watcher_disabled()
    source = Path(grant["source"]).expanduser().absolute()
    cfg = load_config()
    index = cfg.get("index")
    if not isinstance(index, dict):
        raise TypeError("index configuration missing")
    table = dict(index.get("incremental_jsonl") or {})
    table.update(
        enabled=True,
        live_sources=[str(source)],
        embed_dimension=grant["embed_dimension"],
        allow_full_rebuild=False,
    )
    index["incremental_jsonl"] = table
    boundary = ProductionBoundary(cfg, source, config_path=CONFIG_PATH)
    if detect_format(source) != "jsonl_kiro_session":
        raise ValueError("first bootstrap slice supports one Kiro JSONL source")
    view = parse_complete_prefix(str(source))
    if (
        view.prefix_sha256 != grant["prefix_sha256"]
        or view.complete_boundary != grant["complete_boundary"]
    ):
        raise ValueError("source prefix differs from the reviewed grant")
    chunk_size = int(index.get("chunk_size", 2))
    overlap = int(index.get("chunk_overlap", 0))
    chunks = len(chunk_messages(view.messages, chunk_size, overlap))
    if chunks > grant["max_chunks"]:
        raise ValueError("source exceeds the reviewed transform-chunk cap")
    distill = cfg.get("distill") or {}
    coordinator = IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        models=cfg.get("models") or {},
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=float(distill.get("min_confidence", 0.6)),
        embed_dimension=grant["embed_dimension"],
        bootstrap_existing=True,
        expected_prefix_sha256=grant["prefix_sha256"],
        max_bootstrap_chunks=grant["max_chunks"],
    )
    result = coordinator.run()
    if result.outcome != "committed":
        raise RuntimeError(f"one-shot bootstrap refused: {result.outcome}")
    return {
        "source": str(source),
        "prefix_sha256": grant["prefix_sha256"],
        "backup_snapshot": grant["backup_snapshot"],
        "mode": result.mode,
        "chunks": result.chunks,
        "units": result.units,
        "provider_calls": result.counters.as_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grant-file", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="run the reviewed one-shot bootstrap")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required for the reviewed one-shot bootstrap")
    receipt = bootstrap(_read_grant(args.grant_file))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
