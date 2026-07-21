"""Hermetic tests for R2b phase-scoped capture auth schema (no real eval-root writes)."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from eval_corpus.run_manifest import (
    AuthContext,
    GATE_1_HARNESS_SHA256,
    R2B_REQUIRED_PROHIBITED,
    canonical_manifest_body_sha256,
    make_r2b_run_manifest_for_tests,
    validate_r2b_manifest_schema,
    validate_run_manifest_schema,
    write_approval_sidecar,
)


def _write_json(path: Path, body: dict) -> Path:
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def _r2b_paths(root: Path, run_id: str = "test-r2b-run") -> dict[str, str]:
    """Create hermetic paths containing eval-root and auth-root markers."""
    eval_base = (
        root / ".local" / "share" / "convmem" / "eval" / run_id / "capture"
    )
    auth_base = (
        root
        / ".local"
        / "share"
        / "convmem"
        / "authorizations"
        / "r2b"
        / run_id
    )
    export = root / "source" / "knowledge_units.jsonl"
    processed = root / "source" / "processed.json"
    chroma_dir = root / "source" / "chroma"

    for d in [eval_base.parent, auth_base, export.parent, chroma_dir]:
        d.mkdir(parents=True, exist_ok=True)

    export.write_text('{"id":"unit1"}\n', encoding="utf-8")
    processed.write_text("{}", encoding="utf-8")

    return {
        "export": str(export),
        "processed": str(processed),
        "capture_dir": str(eval_base),
        "chroma_dir": str(chroma_dir),
    }


def _fresh_snapshot() -> dict:
    return {
        "export_sha256": "a" * 64,
        "processed_state": "present",
        "processed_sha256": "b" * 64,
        "chroma_collection_name": "knowledge_units",
        "chroma_collection_id": "test-coll-uuid",
        "chroma_extracted_unit_count": 5,
        "chroma_sorted_id_hash": "c" * 64,
        "chroma_capture_slice_sha256": "d" * 64,
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
    }


class R2bSchemaValidationTests(unittest.TestCase):
    """Validate the R2b manifest schema independently of binder/capability."""

    def test_valid_r2b_schema(self):
        with tempfile.TemporaryDirectory() as td:
            paths = _r2b_paths(Path(td))
            body = make_r2b_run_manifest_for_tests(paths=paths)
            errs = validate_r2b_manifest_schema(body)
            self.assertEqual(errs, [], msg=errs)

    def test_wrong_authorization_phase(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            authorization_phase="r2a",
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("r2b" in e.lower() for e in errs))

    def test_wrong_execution_mode(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            execution_mode="fixture",
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("real" in e.lower() for e in errs))

    def test_wrong_status(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            status="draft",
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("approved" in e for e in errs))

    def test_wrong_operations(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        body["operations"] = ["capture", "adjudicate"]
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("exactly" in e for e in errs))

    def test_wrong_harness_sha(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            merged_harness_sha256="0" * 64,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("Gate 1" in e or "harness" in e for e in errs))

    def test_wrong_service_policy(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            service_policy="allow_service_changes",
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("no_service_changes" in e for e in errs))

    def test_missing_prohibited_actions(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        body["prohibited_actions"] = ["promote"]
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("missing required" in e for e in errs))

    def test_string_prohibited_actions_rejected(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        body["prohibited_actions"] = "config_generation"
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("must be a list" in e for e in errs))

    def test_bad_run_id_rejected(self):
        for bad_id in ["", "../escape", ".hidden", "a" * 200, "a/b", "a b"]:
            with self.subTest(run_id=bad_id):
                body = make_r2b_run_manifest_for_tests(
                    paths={"export": "/e", "processed": "/p",
                           "capture_dir": "/c", "chroma_dir": "/d"},
                    run_id=bad_id if bad_id else "ok",
                )
                if bad_id == "":
                    body["run_id"] = ""
                else:
                    body["run_id"] = bad_id
                body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
                errs = validate_r2b_manifest_schema(body)
                self.assertTrue(
                    any("run_id" in e for e in errs),
                    msg=f"run_id={bad_id!r} should fail: {errs}",
                )

    def test_valid_run_id_accepted(self):
        for good_id in ["run-2026", "A.B_C-1", "x"]:
            with self.subTest(run_id=good_id):
                body = make_r2b_run_manifest_for_tests(
                    paths={"export": "/e", "processed": "/p",
                           "capture_dir": "/c", "chroma_dir": "/d"},
                    run_id=good_id,
                )
                errs = validate_r2b_manifest_schema(body)
                self.assertFalse(
                    any("run_id" in e for e in errs),
                    msg=f"run_id={good_id!r} should pass: {errs}",
                )

    def test_paths_wrong_keys(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        body["paths"]["extra_key"] = "/x"
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("extra" in e.lower() for e in errs))

    def test_paths_missing_keys(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        del body["paths"]["chroma_dir"]
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("missing" in e.lower() for e in errs))


class R2bSourceSnapshotSchemaTests(unittest.TestCase):
    """Validate source_snapshot sub-object schema."""

    def test_valid_snapshot(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=_fresh_snapshot(),
        )
        errs = validate_r2b_manifest_schema(body)
        snap_errs = [e for e in errs if "source_snapshot" in e]
        self.assertEqual(snap_errs, [], msg=snap_errs)

    def test_bad_export_sha(self):
        snap = _fresh_snapshot()
        snap["export_sha256"] = "short"
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=snap,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("export_sha256" in e for e in errs))

    def test_processed_sha_present_requires_hex(self):
        snap = _fresh_snapshot()
        snap["processed_state"] = "present"
        snap["processed_sha256"] = None
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=snap,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("processed_sha256" in e for e in errs))

    def test_processed_sha_absent_must_be_null(self):
        snap = _fresh_snapshot()
        snap["processed_state"] = "absent"
        snap["processed_sha256"] = "b" * 64
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=snap,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("processed_sha256" in e for e in errs))

    def test_empty_collection_name(self):
        snap = _fresh_snapshot()
        snap["chroma_collection_name"] = ""
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=snap,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("chroma_collection_name" in e for e in errs))

    def test_null_collection_id(self):
        snap = _fresh_snapshot()
        snap["chroma_collection_id"] = None
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=snap,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("chroma_collection_id" in e for e in errs))

    def test_negative_unit_count(self):
        snap = _fresh_snapshot()
        snap["chroma_extracted_unit_count"] = -1
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=snap,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("chroma_extracted_unit_count" in e for e in errs))

    def test_bool_unit_count_rejected(self):
        snap = _fresh_snapshot()
        snap["chroma_extracted_unit_count"] = True
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=snap,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("chroma_extracted_unit_count" in e for e in errs))

    def test_naive_timestamp_rejected(self):
        snap = _fresh_snapshot()
        snap["snapshot_timestamp"] = "2026-07-20T12:00:00"
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
            source_snapshot=snap,
        )
        errs = validate_r2b_manifest_schema(body)
        self.assertTrue(any("timezone" in e for e in errs))


class R2bValidationPrecedenceTests(unittest.TestCase):
    """Test updated validate_run_manifest_schema precedence."""

    def test_real_capture_requires_r2b(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        body["authorization_phase"] = "r2a"
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("r2b" in e.lower() for e in errs))

    def test_r2b_without_capture_rejected(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        body["operations"] = ["config_generation"]
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("without capture" in e.lower() for e in errs))

    def test_mixed_capture_operations_rejected(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        body["operations"] = ["capture", "adjudicate"]
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("only operation" in e for e in errs))

    def test_malformed_operations_rejected(self):
        body = make_r2b_run_manifest_for_tests(
            paths={"export": "/e", "processed": "/p",
                   "capture_dir": "/c", "chroma_dir": "/d"},
        )
        body["operations"] = "capture"
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("must be a list" in e for e in errs))


class R2bCapabilityTests(unittest.TestCase):
    """Test R2b capability immutability, forgery, and bind_capture refusal."""

    def _setup_r2b_env(self, root: Path, run_id: str = "test-r2b-run"):
        """Create an R2b environment with manifest, sidecar, and source files."""
        import sqlite3

        paths = _r2b_paths(root, run_id)
        chroma_dir = Path(paths["chroma_dir"])
        db = chroma_dir / "chroma.sqlite3"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE collections (id TEXT, name TEXT)")
        conn.execute("CREATE TABLE segments (id TEXT, collection TEXT, scope TEXT)")
        conn.execute(
            "CREATE TABLE embeddings "
            "(id INTEGER PRIMARY KEY, embedding_id TEXT, segment_id TEXT)"
        )
        conn.execute(
            "CREATE TABLE embedding_metadata "
            "(id INTEGER, key TEXT, string_value TEXT, bool_value INTEGER)"
        )
        conn.execute(
            "INSERT INTO collections VALUES (?, ?)",
            ("test-coll-uuid", "knowledge_units"),
        )
        conn.execute(
            "INSERT INTO segments VALUES (?, ?, ?)",
            ("seg1", "test-coll-uuid", "METADATA"),
        )
        conn.execute(
            "INSERT INTO embeddings VALUES (?, ?, ?)", (1, "unit1", "seg1")
        )
        conn.execute(
            "INSERT INTO embedding_metadata VALUES (?, ?, ?, ?)",
            (1, "chroma:document", "doc text", None),
        )
        conn.commit()
        conn.close()

        from eval_corpus.capture import compute_chroma_capture_identity
        from eval_corpus.io_atomic import sha256_file

        identity = compute_chroma_capture_identity(chroma_dir)
        snap = {
            "export_sha256": sha256_file(paths["export"]),
            "processed_state": "present",
            "processed_sha256": sha256_file(paths["processed"]),
            "chroma_collection_name": identity["collection_name"],
            "chroma_collection_id": identity["collection_id"],
            "chroma_extracted_unit_count": identity["extracted_unit_count"],
            "chroma_sorted_id_hash": identity["sorted_id_hash"],
            "chroma_capture_slice_sha256": identity["capture_slice_sha256"],
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        body = make_r2b_run_manifest_for_tests(
            paths=paths, run_id=run_id, source_snapshot=snap
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
        man = _write_json(auth_dir / "capture.json", body)
        write_approval_sidecar(man)
        return man, paths, body, snap

    def test_bind_capture_refuses_r2b(self):
        from eval_corpus.run_manifest import bind_capture

        with tempfile.TemporaryDirectory() as td:
            man, paths, body, snap = self._setup_r2b_env(Path(td))
            with self.assertRaises(PermissionError) as ctx:
                bind_capture(
                    authorize_fixture=False,
                    run_manifest_path=man,
                    runtime={
                        "export": paths["export"],
                        "processed": paths["processed"],
                        "capture_dir": paths["capture_dir"],
                        "chroma_dir": paths["chroma_dir"],
                    },
                )
            self.assertIn("bind_r2b_capture", str(ctx.exception))

    def test_r2b_capability_immutable(self):
        from eval_corpus.r2b_capture_auth import bind_r2b_capture

        with tempfile.TemporaryDirectory() as td:
            man, paths, body, snap = self._setup_r2b_env(Path(td))

            def _pass_snapshot(**kw):
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
            )

            with self.assertRaises(AttributeError):
                cap._manifest_path = Path("/forged")  # pylint: disable=protected-access
            with self.assertRaises(TypeError):
                type(cap)()

    def test_r2b_capability_unforgeable(self):
        from eval_corpus.r2b_capture_auth import is_r2b_eval_root_grant

        self.assertFalse(is_r2b_eval_root_grant(object()))
        self.assertFalse(
            is_r2b_eval_root_grant(
                AuthContext(
                    execution_mode="real",
                    require_corpus_acceptance=False,
                    manifest={},
                    operation="capture",
                )
            )
        )

    def test_r2b_bind_rejects_stale_snapshot(self):
        from eval_corpus.r2b_capture_auth import bind_r2b_capture

        with tempfile.TemporaryDirectory() as td:
            man, paths, body, snap = self._setup_r2b_env(Path(td))
            stale_ts = (
                datetime.now(timezone.utc) - timedelta(hours=2)
            ).isoformat()
            stale_body = dict(body)
            stale_body["source_snapshot"] = dict(snap, snapshot_timestamp=stale_ts)
            stale_body["ryan_approved_manifest_sha256"] = (
                canonical_manifest_body_sha256(stale_body)
            )
            man.write_text(
                json.dumps(stale_body, indent=2) + "\n", encoding="utf-8"
            )
            write_approval_sidecar(man)

            with self.assertRaises(PermissionError) as ctx:
                bind_r2b_capture(
                    run_manifest_path=man,
                    runtime={
                        "export": paths["export"],
                        "processed": paths["processed"],
                        "capture_dir": paths["capture_dir"],
                        "chroma_dir": paths["chroma_dir"],
                    },
                )
            self.assertIn("old", str(ctx.exception).lower())

    def test_r2b_bind_rejects_snapshot_mismatch(self):
        from eval_corpus.r2b_capture_auth import bind_r2b_capture

        with tempfile.TemporaryDirectory() as td:
            man, paths, body, snap = self._setup_r2b_env(Path(td))

            def _wrong_snapshot(**kw):
                wrong = dict(snap)
                wrong["export_sha256"] = "f" * 64
                return wrong

            with self.assertRaises(PermissionError) as ctx:
                bind_r2b_capture(
                    run_manifest_path=man,
                    runtime={
                        "export": paths["export"],
                        "processed": paths["processed"],
                        "capture_dir": paths["capture_dir"],
                        "chroma_dir": paths["chroma_dir"],
                    },
                    snapshot_recompute_fn=_wrong_snapshot,
                )
            self.assertIn("mismatch", str(ctx.exception).lower())

    def test_r2b_corrupt_sidecar_refused(self):
        from eval_corpus.r2b_capture_auth import bind_r2b_capture

        with tempfile.TemporaryDirectory() as td:
            man, paths, body, snap = self._setup_r2b_env(Path(td))

            def _pass_snapshot(**kw):
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
            )

            side = man.with_suffix(man.suffix + ".approved.sha256")
            side.write_text("00" * 32 + "\n", encoding="utf-8")

            from eval_corpus.r2b_capture_auth import (
                materialize_r2b_write_authorization,
            )

            with self.assertRaises(PermissionError):
                materialize_r2b_write_authorization(cap)


if __name__ == "__main__":
    unittest.main()
