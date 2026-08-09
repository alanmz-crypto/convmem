"""Emit the read-only export-to-Chroma projection completeness report."""

# ruff: noqa: I001 -- repository imports follow the deliberate sys.path bootstrap.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pylint: disable=wrong-import-position
from chroma_readonly import collection_metadata_rows
from chroma_store import UNITS
from config import load_config
from projection_parity import build_projection_parity_report


LOCKED_LEDGER_IDS = (
    "obs_staging2_monitor_header-referrer-policy",
    "ver_staging2_mon_referrer-policy",
)


def _jsonl_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="also write the JSON report here")
    args = parser.parse_args()

    cfg = load_config()["index"]
    export_path = Path(cfg["units_export"]).expanduser()
    processed_path = Path(cfg["processed_log"]).expanduser()
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    report = build_projection_parity_report(
        _jsonl_rows(export_path),
        collection_metadata_rows(cfg["chroma_dir"], UNITS),
        processed,
        required_ledger_ids=LOCKED_LEDGER_IDS,
    )
    report["inputs"] = {
        "chroma_dir": str(Path(cfg["chroma_dir"]).expanduser()),
        "processed_log": str(processed_path),
        "units_export": str(export_path),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["gates"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
