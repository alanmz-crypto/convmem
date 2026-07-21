"""Hermetic tests for R2b capture marker: write order, inventory, FAILED no marker."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from eval_corpus.capture import (
    compute_chroma_capture_identity,
    run_capture,
)
from eval_corpus.io_atomic import sha256_file
from eval_corpus.r2b_capture_auth import (
    bind_r2b_capture,
    canonical_source_snapshot_sha256,
)
from eval_corpus.run_manifest import (
    canonical_manifest_body_sha256,
    make_r2b_run_manifest_for_tests,
    write_approval_sidecar,
)


def _write_json(path: Path, body: dict) -> Path:
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def _create_chroma_fixture(
    chroma_dir: Path,
    records: list[dict],
    collection_name: str = "knowledge_units",
    collection_id: str = "test-coll-uuid",
) -> None:
    """Create a minimal Chroma SQLite fixture for testing."""
    chroma_dir.mkdir(parents=True, exist_ok=True)
    db = chroma_dir / "chroma.sqlite3"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE collections (id TEXT, name TEXT)")
    conn.execute(
        "CREATE TABLE segments (id TEXT, collection TEXT, scope TEXT)"
    )
    conn.execute(
        "CREATE TABLE embeddings "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, embedding_id TEXT, segment_id TEXT)"
    )
    conn.execute(
        "CREATE TABLE embedding_metadata "
        "(id INTEGER, key TEXT, string_value TEXT, bool_value INTEGER)"
    )
    conn.execute(
        "INSERT INTO collections VALUES (?, ?)",
        (collection_id, collection_name),
    )
    seg_id = "test-seg-uuid"
    conn.execute(
        "INSERT INTO segments VALUES (?, ?, ?)",
        (seg_id, collection_id, "METADATA"),
    )
    for rec in records:
        cur = conn.execute(
            "INSERT INTO embeddings (embedding_id, segment_id) VALUES (?, ?)",
            (rec["id"], seg_id),
        )
        row_id = cur.lastrowid
        if rec.get("document") is not None:
            conn.execute(
                "INSERT INTO embedding_metadata VALUES (?, ?, ?, ?)",
                (row_id, "chroma:document", rec["document"], None),
            )
        if rec.get("superseded"):
            conn.execute(
                "INSERT INTO embedding_metadata VALUES (?, ?, ?, ?)",
                (row_id, "superseded", None, 1),
            )
    conn.commit()
    conn.close()


def _setup_r2b_capture_env(
    root: Path,
    run_id: str = "test-r2b-run",
    chroma_records: list[dict] | None = None,
    export_lines: list[str] | None = None,
    include_processed: bool = True,
):
    """Full R2b capture environment with manifest, Chroma, sources."""
    if chroma_records is None:
        chroma_records = [
            {"id": "unit1", "document": "doc text 1"},
            {"id": "unit2", "document": "doc text 2"},
        ]
    if export_lines is None:
        export_lines = [
            json.dumps({"id": r["id"], "source": "test"}) for r in chroma_records
        ]

    eval_base = (
        root / ".local" / "share" / "convmem" / "eval" / run_id / "capture"
    )
    auth_dir = (
        root
        / ".local"
        / "share"
        / "convmem"
        / "authorizations"
        / "r2b"
        / run_id
    )
    source_dir = root / "source"

    for d in [eval_base.parent, auth_dir, source_dir]:
        d.mkdir(parents=True, exist_ok=True)

    export_path = source_dir / "knowledge_units.jsonl"
    export_path.write_text("\n".join(export_lines) + "\n", encoding="utf-8")

    processed_path = source_dir / "processed.json"
    if include_processed:
        processed_path.write_text("{}", encoding="utf-8")

    chroma_dir = source_dir / "chroma"
    _create_chroma_fixture(chroma_dir, chroma_records)

    identity = compute_chroma_capture_identity(chroma_dir)
    snap = {
        "export_sha256": sha256_file(export_path),
        "processed_state": "present" if include_processed else "absent",
        "processed_sha256": (
            sha256_file(processed_path) if include_processed else None
        ),
        "chroma_collection_name": identity["collection_name"],
        "chroma_collection_id": identity["collection_id"],
        "chroma_extracted_unit_count": identity["extracted_unit_count"],
        "chroma_sorted_id_hash": identity["sorted_id_hash"],
        "chroma_capture_slice_sha256": identity["capture_slice_sha256"],
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    paths = {
        "export": str(export_path),
        "processed": str(processed_path),
        "capture_dir": str(eval_base),
        "chroma_dir": str(chroma_dir),
    }
    body = make_r2b_run_manifest_for_tests(
        paths=paths, run_id=run_id, source_snapshot=snap
    )
    man = _write_json(auth_dir / "capture.json", body)
    write_approval_sidecar(man)

    def _pass_snapshot(**_kw):
        return snap

    cap = bind_r2b_capture(
        run_manifest_path=man,
        runtime={
            "export": paths["export"],
            "processed": paths["processed"],
            "capture_dir": paths["capture_dir"],
            "chroma_dir": paths["chroma_dir"],
        },
        snapshot_recompute_fn=_pass_snapshot,
        restic_gate_fn=lambda: None,
    )

    return cap, paths, body, snap, man


class R2bCaptureMarkerTests(unittest.TestCase):
    """Test that R2b capture writes the completion marker last."""

    def test_marker_written_and_present(self):
        with tempfile.TemporaryDirectory() as td:
            cap, paths, _body, _snap, _man = _setup_r2b_capture_env(Path(td))
            run_capture(
                export_src=Path(paths["export"]),
                processed_src=Path(paths["processed"]),
                capture_dir=Path(paths["capture_dir"]),
                chroma_dir=Path(paths["chroma_dir"]),
                r2b_capability=cap,
            )
            capture_dir = Path(paths["capture_dir"])
            marker_path = capture_dir / "corpus_package_manifest.json"
            self.assertTrue(marker_path.is_file())

            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            self.assertEqual(marker["marker_version"], 1)
            self.assertEqual(marker["status"], "CAPTURE_ARTIFACTS_COMPLETE")
            self.assertIn(
                marker["capture_outcome"],
                ("CAPTURE_COMPLETE", "UNRESOLVED"),
            )
            self.assertEqual(marker["run_id"], "test-r2b-run")
            self.assertEqual(marker["capture_id"], "test-r2b-run")

    def test_marker_has_correct_authorization_digests(self):
        with tempfile.TemporaryDirectory() as td:
            cap, paths, body, snap, _man = _setup_r2b_capture_env(Path(td))
            run_capture(
                export_src=Path(paths["export"]),
                processed_src=Path(paths["processed"]),
                capture_dir=Path(paths["capture_dir"]),
                chroma_dir=Path(paths["chroma_dir"]),
                r2b_capability=cap,
            )
            capture_dir = Path(paths["capture_dir"])
            marker = json.loads(
                (capture_dir / "corpus_package_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                marker["authorization_body_sha256"],
                canonical_manifest_body_sha256(body),
            )
            self.assertEqual(
                marker["source_snapshot_sha256"],
                canonical_source_snapshot_sha256(snap),
            )

    def test_marker_artifact_inventory_correct(self):
        with tempfile.TemporaryDirectory() as td:
            cap, paths, _body, _snap, _man = _setup_r2b_capture_env(Path(td))
            run_capture(
                export_src=Path(paths["export"]),
                processed_src=Path(paths["processed"]),
                capture_dir=Path(paths["capture_dir"]),
                chroma_dir=Path(paths["chroma_dir"]),
                r2b_capability=cap,
            )
            capture_dir = Path(paths["capture_dir"])
            marker = json.loads(
                (capture_dir / "corpus_package_manifest.json").read_text(
                    encoding="utf-8"
                )
            )

            expected_inv = sorted(
                [
                    "capture_report.json",
                    "chroma_documents.json",
                    "chroma_extract.json",
                    "corpus_package.jsonl",
                    "corpus_package_manifest.json",
                    "historical_spot_check.json",
                    "knowledge_units.jsonl",
                    "overlap_validation.json",
                    "processed.json",
                ]
            )
            self.assertEqual(marker["artifact_inventory"], expected_inv)

    def test_marker_artifact_sha256_correct(self):
        with tempfile.TemporaryDirectory() as td:
            cap, paths, _body, _snap, _man = _setup_r2b_capture_env(Path(td))
            run_capture(
                export_src=Path(paths["export"]),
                processed_src=Path(paths["processed"]),
                capture_dir=Path(paths["capture_dir"]),
                chroma_dir=Path(paths["chroma_dir"]),
                r2b_capability=cap,
            )
            capture_dir = Path(paths["capture_dir"])
            marker = json.loads(
                (capture_dir / "corpus_package_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            artifact_hashes = marker["artifact_sha256"]
            for name, expected_hash in artifact_hashes.items():
                actual = sha256_file(capture_dir / name)
                self.assertEqual(
                    actual, expected_hash,
                    msg=f"{name} hash mismatch",
                )
            self.assertNotIn(
                "corpus_package_manifest.json", artifact_hashes
            )

    def test_marker_absent_for_processed_absent(self):
        with tempfile.TemporaryDirectory() as td:
            cap, paths, _body, _snap, _man = _setup_r2b_capture_env(
                Path(td), include_processed=False
            )
            run_capture(
                export_src=Path(paths["export"]),
                processed_src=Path(paths["processed"]),
                capture_dir=Path(paths["capture_dir"]),
                chroma_dir=Path(paths["chroma_dir"]),
                r2b_capability=cap,
            )
            capture_dir = Path(paths["capture_dir"])
            marker = json.loads(
                (capture_dir / "corpus_package_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(marker["processed_state"], "absent")
            self.assertNotIn("processed.json", marker["artifact_inventory"])
            self.assertNotIn("processed.json", marker["artifact_sha256"])
            self.assertFalse((capture_dir / "processed.json").exists())

    def test_legacy_path_still_writes_mid_pipeline_manifest(self):
        """Fixture/temp path keeps legacy behavior: corpus_package_manifest.json mid-pipeline."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            export = root / "knowledge_units.jsonl"
            export.write_text(
                json.dumps({"id": "u1", "source": "test"}) + "\n",
                encoding="utf-8",
            )
            processed = root / "processed.json"
            processed.write_text("{}", encoding="utf-8")
            chroma_dir = root / "chroma"
            _create_chroma_fixture(
                chroma_dir, [{"id": "u1", "document": "doc"}]
            )
            capture_dir = root / "capture"
            run_capture(
                export_src=export,
                processed_src=processed,
                capture_dir=capture_dir,
                chroma_dir=chroma_dir,
                overlap_policy="fixture",
            )
            manifest_path = capture_dir / "corpus_package_manifest.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            self.assertNotIn("marker_version", manifest)
            self.assertIn("unit_count", manifest)

    def test_r2b_no_marker_on_eval_root_without_capability(self):
        """Eval-root path without capability must refuse."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            eval_path = (
                root
                / ".local"
                / "share"
                / "convmem"
                / "eval"
                / "test"
                / "capture"
            )
            eval_path.mkdir(parents=True, exist_ok=True)
            chroma_dir = root / "chroma"
            _create_chroma_fixture(
                chroma_dir, [{"id": "u1", "document": "doc"}]
            )
            export = root / "export.jsonl"
            export.write_text("{}\n", encoding="utf-8")
            processed = root / "processed.json"
            processed.write_text("{}", encoding="utf-8")
            with self.assertRaises(PermissionError) as ctx:
                run_capture(
                    export_src=export,
                    processed_src=processed,
                    capture_dir=eval_path,
                    chroma_dir=chroma_dir,
                )
            self.assertIn("capability", str(ctx.exception).lower())


class R2bChromaIdentityTests(unittest.TestCase):
    """Test compute_chroma_capture_identity canonicalization."""

    def test_basic_identity(self):
        with tempfile.TemporaryDirectory() as td:
            chroma_dir = Path(td)
            _create_chroma_fixture(
                chroma_dir,
                [
                    {"id": "b-unit", "document": "beta"},
                    {"id": "a-unit", "document": "alpha"},
                ],
            )
            identity = compute_chroma_capture_identity(chroma_dir)
            self.assertEqual(identity["collection_name"], "knowledge_units")
            self.assertEqual(identity["collection_id"], "test-coll-uuid")
            self.assertEqual(identity["extracted_unit_count"], 2)
            self.assertEqual(len(identity["sorted_id_hash"]), 64)
            self.assertEqual(len(identity["capture_slice_sha256"]), 64)

    def test_id_ordering_is_utf8_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            chroma_dir = Path(td)
            _create_chroma_fixture(
                chroma_dir,
                [
                    {"id": "z-unit", "document": "z"},
                    {"id": "a-unit", "document": "a"},
                ],
            )
            id1 = compute_chroma_capture_identity(chroma_dir)

            chroma_dir2 = Path(td) / "chroma2"
            _create_chroma_fixture(
                chroma_dir2,
                [
                    {"id": "a-unit", "document": "a"},
                    {"id": "z-unit", "document": "z"},
                ],
            )
            id2 = compute_chroma_capture_identity(chroma_dir2)

            self.assertEqual(
                id1["sorted_id_hash"], id2["sorted_id_hash"]
            )
            self.assertEqual(
                id1["capture_slice_sha256"], id2["capture_slice_sha256"]
            )

    def test_superseded_affects_slice_hash(self):
        with tempfile.TemporaryDirectory() as td:
            chroma_dir = Path(td)
            _create_chroma_fixture(
                chroma_dir,
                [{"id": "unit1", "document": "doc"}],
            )
            id_normal = compute_chroma_capture_identity(chroma_dir)

            chroma_dir2 = Path(td) / "chroma2"
            _create_chroma_fixture(
                chroma_dir2,
                [{"id": "unit1", "document": "doc", "superseded": True}],
            )
            id_super = compute_chroma_capture_identity(chroma_dir2)

            self.assertEqual(
                id_normal["sorted_id_hash"], id_super["sorted_id_hash"]
            )
            self.assertNotEqual(
                id_normal["capture_slice_sha256"],
                id_super["capture_slice_sha256"],
            )

    def test_cr_lf_in_id_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            chroma_dir = Path(td)
            _create_chroma_fixture(
                chroma_dir,
                [{"id": "unit\n1", "document": "doc"}],
            )
            with self.assertRaises(ValueError):
                compute_chroma_capture_identity(chroma_dir)


if __name__ == "__main__":
    unittest.main()
