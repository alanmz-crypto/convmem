"""Eval corpus package — capture, reconstruct, fingerprint, validate, runner (Phase A).

R1 scope: library + CLI surfaces + hermetic tests. No live capture, real shadow
builds, model ops, or evaluation against live/shadow stores.
"""

from __future__ import annotations

RECONSTRUCTION_SCHEMA_VERSION = "eval-corpus-v1"
CAPTURE_SCHEMA_VERSION = "eval-capture-v1"

__all__ = [
    "RECONSTRUCTION_SCHEMA_VERSION",
    "CAPTURE_SCHEMA_VERSION",
]
