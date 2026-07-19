"""Corpus acceptance via separate adjudications file (capture artifacts immutable)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_corpus.io_atomic import atomic_write_json, sha256_file


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_adjudications_file(
    adjudications: dict[str, Any],
    spot_check: dict[str, Any],
) -> list[str]:
    """Return error messages; empty = ok."""
    errors: list[str] = []
    sample = list(spot_check.get("sample_ids") or [])
    rows = adjudications.get("adjudications")
    if not isinstance(rows, list):
        return ["adjudications must be a list"]
    by_id = {}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("adjudication row must be object")
            continue
        uid = str(row.get("id") or "")
        verdict = str(row.get("verdict") or "")
        if not uid:
            errors.append("adjudication missing id")
            continue
        if verdict not in ("ok", "anomaly_explained", "systematic_stop"):
            errors.append(f"invalid verdict for {uid}: {verdict!r}")
        by_id[uid] = verdict
    for uid in sample:
        if uid not in by_id:
            errors.append(f"missing adjudication for sample id {uid}")
    if any(v == "systematic_stop" for v in by_id.values()):
        errors.append("systematic_stop adjudication blocks acceptance")
    return errors


def emit_corpus_acceptance(
    *,
    capture_dir: Path,
    adjudications_path: Path,
    reviewer: str = "ryan",
) -> dict[str, Any]:
    """Write corpus_acceptance.json binding SHAs of immutable capture artifacts.

    Never modifies historical_spot_check.json or other capture products.
    """
    capture_dir = Path(capture_dir)
    adjudications_path = Path(adjudications_path)
    report_path = capture_dir / "capture_report.json"
    package_path = capture_dir / "corpus_package.jsonl"
    overlap_path = capture_dir / "overlap_validation.json"
    spot_path = capture_dir / "historical_spot_check.json"

    for p in (report_path, package_path, overlap_path, spot_path, adjudications_path):
        if not p.is_file():
            raise FileNotFoundError(str(p))

    report = load_json(report_path)
    overlap = load_json(overlap_path)
    spot = load_json(spot_path)
    adjs = load_json(adjudications_path)

    if report.get("status") != "CAPTURE_COMPLETE":
        raise RuntimeError(
            f"capture status must be CAPTURE_COMPLETE, got {report.get('status')!r}"
        )
    if overlap.get("overall") != "PASS":
        raise RuntimeError(f"overlap overall must be PASS, got {overlap.get('overall')!r}")

    errs = validate_adjudications_file(adjs, spot)
    if errs:
        raise RuntimeError("adjudication rejected: " + "; ".join(errs))

    acceptance = {
        "status": "CORPUS_ACCEPTED",
        "accepted_at": _now(),
        "reviewer": reviewer,
        "capture_id": report.get("capture_id"),
        "bound_sha256": {
            "capture_report": sha256_file(report_path),
            "corpus_package": sha256_file(package_path),
            "overlap_validation": sha256_file(overlap_path),
            "historical_spot_check": sha256_file(spot_path),
            "adjudications": sha256_file(adjudications_path),
        },
        "unit_corpus_fingerprint": report.get("unit_corpus_fingerprint"),
        "package_sha256": report.get("package_sha256"),
        "adjudications_path": adjudications_path.name,
    }
    out = capture_dir / "corpus_acceptance.json"
    atomic_write_json(out, acceptance)
    return acceptance


def verify_corpus_acceptance_hashes(capture_dir: Path) -> list[str]:
    """Revalidate acceptance bindings; used by builders before accepting corpus."""
    capture_dir = Path(capture_dir)
    acc_path = capture_dir / "corpus_acceptance.json"
    if not acc_path.is_file():
        return ["missing corpus_acceptance.json"]
    acc = load_json(acc_path)
    if acc.get("status") != "CORPUS_ACCEPTED":
        return [f"acceptance status not CORPUS_ACCEPTED: {acc.get('status')!r}"]
    bound = acc.get("bound_sha256") or {}
    mapping = {
        "capture_report": capture_dir / "capture_report.json",
        "corpus_package": capture_dir / "corpus_package.jsonl",
        "overlap_validation": capture_dir / "overlap_validation.json",
        "historical_spot_check": capture_dir / "historical_spot_check.json",
        "adjudications": capture_dir / str(acc.get("adjudications_path") or "adjudications.json"),
    }
    errors: list[str] = []
    for key, path in mapping.items():
        if not path.is_file():
            errors.append(f"missing {path.name}")
            continue
        got = sha256_file(path)
        want = bound.get(key)
        if got != want:
            errors.append(f"{key} hash mismatch: got {got} expected {want}")
    return errors
