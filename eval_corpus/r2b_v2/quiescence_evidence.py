"""Quiescence evidence JSON writers for R2b v2 transactions (I4–I6)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from eval_corpus.io_atomic import atomic_write_json, sha256_file


def canonical_evidence_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_quiescence_open(
    path: Path,
    *,
    run_id: str,
    gate_identity: str,
    gate_path: str,
    open_evidence_digest: str,
    writer_coverage_digest: str,
    implementation_revision: str,
    monotonic_deadline: float,
) -> str:
    body = {
        "evidence_kind": "quiescence-open",
        "run_id": run_id,
        "gate_identity": gate_identity,
        "gate_path": gate_path,
        "open_evidence_digest": open_evidence_digest,
        "writer_coverage_digest": writer_coverage_digest,
        "implementation_revision": implementation_revision,
        "monotonic_deadline": monotonic_deadline,
    }
    atomic_write_json(path, body)
    return sha256_file(path)


def write_quiescence_close(  # pylint: disable=too-many-arguments
    path: Path,
    *,
    run_id: str,
    terminal_disposition: str,
    marker_result: str,
    final_source_result: str,
    deadline_state: str,
    gate_identity: str,
    release_intent: bool,
    preceding_digests: dict[str, str],
) -> str:
    body = {
        "evidence_kind": "quiescence-close",
        "run_id": run_id,
        "terminal_disposition": terminal_disposition,
        "marker_result": marker_result,
        "final_source_result": final_source_result,
        "deadline_state": deadline_state,
        "gate_identity": gate_identity,
        "release_intent": release_intent,
        "release_success_claimed": False,
        "post_release_observation": None,
        "preceding_digests": preceding_digests,
    }
    atomic_write_json(path, body)
    return sha256_file(path)


def write_quiescence_release(
    path: Path,
    *,
    run_id: str,
    close_digest: str,
    release_result: str,
    post_release_observation: dict[str, Any],
) -> str:
    body = {
        "evidence_kind": "quiescence-release",
        "run_id": run_id,
        "close_digest": close_digest,
        "release_result": release_result,
        "post_release_observation": post_release_observation,
    }
    atomic_write_json(path, body)
    return sha256_file(path)
