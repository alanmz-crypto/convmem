"""Deterministic, absent-leaf enrichment materialization for evaluation arms."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eval_corpus.secure_fs import copy_immutable_input, receipt_for_path


class EnrichmentMaterializationError(PermissionError):
    """Enrichment source/destination bytes or filesystem identity are unsafe."""


def materialize_enrichment(
    source: Path | str,
    destination: Path | str,
    *,
    approved_root: Path | str,
) -> dict[str, Any]:
    """Copy and validate one enrichment file from one exact source snapshot."""
    source_path = Path(source).expanduser()
    destination_path = Path(destination).expanduser()
    copy_receipt = copy_immutable_input(
        source_path,
        destination_path,
        approved_root=approved_root,
    )
    raw = destination_path.read_bytes()
    destination_after = receipt_for_path(destination_path, require_regular=True)
    destination_before = copy_receipt["destination"]
    if (
        destination_after["device"] != destination_before["device"]
        or destination_after["inode"] != destination_before["inode"]
    ):
        raise EnrichmentMaterializationError(
            "destination path identity changed before provenance read"
        )
    from ledger_recent import approved_bytes_snapshot

    rows, provenance = approved_bytes_snapshot(raw, destination_path)
    if provenance["sha256"] != copy_receipt["sha256"]:
        raise EnrichmentMaterializationError(
            "destination bytes changed between copy and provenance read"
        )
    return {
        "source": copy_receipt["source"],
        "destination": copy_receipt["destination"],
        "source_sha256": copy_receipt["sha256"],
        "destination_sha256": provenance["sha256"],
        "row_count": len(rows),
        "semantic_fingerprint": provenance["semantic_fingerprint"],
        "reader_provenance": provenance,
    }


__all__ = ["EnrichmentMaterializationError", "materialize_enrichment"]
