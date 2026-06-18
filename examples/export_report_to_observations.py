#!/usr/bin/env python3
"""Thin wrapper — canonical exporter lives at repo root."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "export_report_to_observations.py"), run_name="__main__")
