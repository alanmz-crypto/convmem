"""Fresh-process qualification for hermetic file generations.

The CLI is intentionally narrow so tests can close a staging client, spawn a
new interpreter, reopen persistent Chroma, and validate the manifest's exact
expected set before pointer promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from file_generation_contract import validate_generation_manifest
from file_generation_store import FileGenerationStore

BAR_P_DURABILITY = {
    "process_crash": "fresh-process exact generation recovery is required",
    "storage_contract": "SQLite journal_mode=DELETE with synchronous=FULL behavior",
    "residual_power_loss_risk": (
        "FULL does not fsync the parent directory after journal unlink; a recent "
        "Chroma transaction may roll back after power loss. Restart qualification "
        "must fail closed; CG-1 does not claim full power-loss durability."
    ),
}


def chroma_sequence_positions(chroma_dir: str | Path) -> dict[str, Any]:
    """Read queue/segment sequence positions without opening a writer."""
    db = Path(chroma_dir) / "chroma.sqlite3"
    uri = f"file:{db.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        queue_min, queue_max = conn.execute(
            "SELECT MIN(seq_id), MAX(seq_id) FROM embeddings_queue"
        ).fetchone()
        segments: dict[str, int] = {}
        query = """
            SELECT c.name, s.scope, m.seq_id
            FROM max_seq_id m
            JOIN segments s ON s.id = m.segment_id
            JOIN collections c ON c.id = s.collection
        """
        for name, scope, value in conn.execute(query):
            if value is not None:
                segments[f"{name}:{scope}"] = int(value)
        return {
            "queue_min_seq_id": None if queue_min is None else int(queue_min),
            "queue_max_seq_id": None if queue_max is None else int(queue_max),
            "segment_max_seq_ids": segments,
        }
    finally:
        conn.close()


def cold_validate(chroma_dir: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Reopen Chroma and require the exact immutable manifest identity set."""
    validate_generation_manifest(manifest)
    active = {str(manifest["owner_digest"]): str(manifest["generation_id"])}
    started = time.perf_counter()
    with FileGenerationStore(chroma_dir, active_generations=lambda: active) as store:
        validation = store.validate_manifest_exact(manifest)
    elapsed = time.perf_counter() - started
    if validation.get("state") != "HEALTHY":
        raise RuntimeError(f"generation exact validation failed: {validation}")
    return {
        "valid": True,
        "generation_id": manifest["generation_id"],
        "owner_digest": manifest["owner_digest"],
        "elapsed_seconds": elapsed,
        "sequence_positions": chroma_sequence_positions(chroma_dir),
        "validation": validation,
    }


def run_cold_validation(
    chroma_dir: str | Path,
    manifest_path: str | Path,
    *,
    expected_manifest_sha256: str | None = None,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Run the exact validator in a new interpreter process."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "file_generation_validate",
            "--chroma-dir",
            str(chroma_dir),
            "--manifest",
            str(manifest_path),
            *(
                ["--expected-manifest-sha256", expected_manifest_sha256]
                if expected_manifest_sha256 is not None
                else []
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"cold generation validation failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    result = json.loads(proc.stdout)
    if not result.get("valid"):
        raise RuntimeError(f"cold generation validation refused: {result}")
    if (
        expected_manifest_sha256 is not None
        and result.get("manifest_sha256") != expected_manifest_sha256
    ):
        raise RuntimeError("cold generation validation manifest hash mismatch")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chroma-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args(argv)
    manifest_bytes = Path(args.manifest).read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if (
        args.expected_manifest_sha256 is not None
        and manifest_sha256 != args.expected_manifest_sha256
    ):
        raise RuntimeError("cold generation validation manifest hash mismatch")
    manifest = json.loads(manifest_bytes)
    result = cold_validate(args.chroma_dir, manifest)
    result["manifest_sha256"] = manifest_sha256
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
