"""Eval corpus package — capture, reconstruct, fingerprint, validate (Phase A harness).

R1 scope: library + hermetic tests only. No live capture, shadow build, or evaluation.
"""

from __future__ import annotations

RECONSTRUCTION_SCHEMA_VERSION = "eval-corpus-v1"
CAPTURE_SCHEMA_VERSION = "eval-capture-v1"

__all__ = [
    "RECONSTRUCTION_SCHEMA_VERSION",
    "CAPTURE_SCHEMA_VERSION",
]
