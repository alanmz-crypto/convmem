"""Real comparison must consume the exact package accepted by R2b."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eval_corpus.adjudicate import verify_accepted_package


def _write_accepted_capture(root: Path) -> Path:
    capture = root / "capture"
    capture.mkdir()
    artifacts = {
        "capture_report.json": {"status": "CAPTURE_COMPLETE"},
        "corpus_package.jsonl": {"id": "u1", "document": "hello"},
        "overlap_validation.json": {"overall": "PASS"},
        "historical_spot_check.json": {"sample_ids": []},
        "adjudications.json": {"adjudications": []},
    }
    for name, value in artifacts.items():
        path = capture / name
        if name.endswith(".jsonl"):
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        else:
            path.write_text(json.dumps(value), encoding="utf-8")
    # Acceptance uses artifact names without filename suffixes as keys.
    hashes = {
        "capture_report": hashlib.sha256(
            (capture / "capture_report.json").read_bytes()
        ).hexdigest(),
        "corpus_package": hashlib.sha256(
            (capture / "corpus_package.jsonl").read_bytes()
        ).hexdigest(),
        "overlap_validation": hashlib.sha256(
            (capture / "overlap_validation.json").read_bytes()
        ).hexdigest(),
        "historical_spot_check": hashlib.sha256(
            (capture / "historical_spot_check.json").read_bytes()
        ).hexdigest(),
        "adjudications": hashlib.sha256(
            (capture / "adjudications.json").read_bytes()
        ).hexdigest(),
    }
    acceptance = {
        "status": "CORPUS_ACCEPTED",
        "bound_sha256": hashes,
        "package_sha256": hashes["corpus_package"],
        "unit_corpus_fingerprint": "f" * 64,
        "adjudications_path": "adjudications.json",
    }
    (capture / "corpus_acceptance.json").write_text(
        json.dumps(acceptance), encoding="utf-8"
    )
    return capture / "corpus_package.jsonl"


def test_accepted_package_is_bound_to_capture_bytes(tmp_path):
    package = _write_accepted_capture(tmp_path)
    result = verify_accepted_package(package)
    assert result["status"] == "CORPUS_ACCEPTED"
    assert result["package_sha256"] == hashlib.sha256(package.read_bytes()).hexdigest()


def test_changed_acceptance_artifact_rejects_package(tmp_path):
    package = _write_accepted_capture(tmp_path)
    (package.parent / "overlap_validation.json").write_text(
        '{"overall":"FAIL"}', encoding="utf-8"
    )
    result = verify_accepted_package(package)
    assert result["status"] == "INVALID"
    assert any("overlap_validation" in error for error in result["errors"])


def test_package_outside_capture_directory_is_rejected(tmp_path):
    package = _write_accepted_capture(tmp_path)
    outside = tmp_path / "elsewhere.jsonl"
    outside.write_bytes(package.read_bytes())
    result = verify_accepted_package(outside)
    assert result["status"] == "INVALID"
    assert result["errors"]
