"""Adversarial tests for the R2b exact query-set lifecycle binding."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from eval_corpus.r2b_capture_auth import (
    bind_r2b_capture,
    materialize_r2b_capability,
    read_immutable_query_set,
)
from eval_corpus.run_manifest import (
    canonical_manifest_body_sha256,
    make_r2b_run_manifest_for_tests,
    write_approval_sidecar,
)
from tests.r2b_hermetic import (
    bind_r2b_pass_snapshot,
    capture_runtime,
    r2b_auth_dir,
    r2b_source_paths,
    trusted_snapshot_for_paths,
    write_json,
)


class R2bQueryLifecycleTests(unittest.TestCase):
    """Keep the approved query bytes stable across R2b authorization."""

    def _write_manifest(self, root: Path, paths: dict[str, str]):
        run_id = "query-lifecycle"
        snap = trusted_snapshot_for_paths(paths)
        body = make_r2b_run_manifest_for_tests(
            paths=paths,
            run_id=run_id,
            source_snapshot=snap,
        )
        manifest = write_json(
            r2b_auth_dir(root, run_id) / "capture.json",
            body,
        )
        write_approval_sidecar(manifest)
        return manifest, body, snap

    def test_valid_binding_hashes_and_parses_one_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = r2b_source_paths(root, "query-lifecycle")
            manifest, body, snap = self._write_manifest(root, paths)
            capability = bind_r2b_pass_snapshot(
                manifest_path=manifest,
                paths=paths,
                snap=snap,
            )
            bindings = materialize_r2b_capability(capability)
            snapshot = read_immutable_query_set(bindings.query_set)
            self.assertEqual(snapshot["sha256"], body["query_set_sha256"])
            self.assertEqual(bindings.query_set_sha256, body["query_set_sha256"])

    def test_digest_mismatch_is_rejected_before_capture_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = r2b_source_paths(root, "query-lifecycle")
            manifest, body, snap = self._write_manifest(root, paths)
            body["query_set_sha256"] = "0" * 64
            body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
            manifest.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
            write_approval_sidecar(manifest)
            with self.assertRaises(PermissionError) as ctx:
                bind_r2b_capture(
                    run_manifest_path=manifest,
                    runtime=capture_runtime(paths),
                    snapshot_recompute_fn=lambda **_kw: snap,
                    restic_gate_fn=lambda: None,
                )
            self.assertIn("query_set_sha256", str(ctx.exception))

    def test_invalid_jsonl_is_rejected_even_when_hash_matches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = r2b_source_paths(root, "query-lifecycle")
            query_path = Path(paths["query_set"])
            query_path.write_bytes(b"not-json\n")
            manifest, _body, snap = self._write_manifest(root, paths)
            with self.assertRaises(PermissionError) as ctx:
                bind_r2b_capture(
                    run_manifest_path=manifest,
                    runtime=capture_runtime(paths),
                    snapshot_recompute_fn=lambda **_kw: snap,
                    restic_gate_fn=lambda: None,
                )
            self.assertIn("JSONL", str(ctx.exception))

    def test_query_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = r2b_source_paths(root, "query-lifecycle")
            query_path = Path(paths["query_set"])
            target = query_path.with_name("queries-target.jsonl")
            query_path.rename(target)
            query_path.symlink_to(target)
            manifest, _body, snap = self._write_manifest(root, paths)
            with self.assertRaises(PermissionError) as ctx:
                bind_r2b_capture(
                    run_manifest_path=manifest,
                    runtime=capture_runtime(paths),
                    snapshot_recompute_fn=lambda **_kw: snap,
                    restic_gate_fn=lambda: None,
                )
            self.assertIn("symlink", str(ctx.exception).lower())

    def test_path_replacement_after_bind_is_rejected_at_materialization(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = r2b_source_paths(root, "query-lifecycle")
            manifest, _body, snap = self._write_manifest(root, paths)
            capability = bind_r2b_pass_snapshot(
                manifest_path=manifest,
                paths=paths,
                snap=snap,
            )
            query_path = Path(paths["query_set"])
            replacement = query_path.with_name("queries-replacement.jsonl")
            replacement.write_text('{"query_id":"changed"}\n', encoding="utf-8")
            query_path.unlink()
            replacement.rename(query_path)
            with self.assertRaises(PermissionError) as ctx:
                materialize_r2b_capability(capability)
            self.assertIn("query_set_sha256", str(ctx.exception))

    def test_snapshot_digest_is_over_raw_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            query_path = Path(td) / "queries.jsonl"
            raw = b'{"query_id":"q"}\r\n'
            query_path.write_bytes(raw)
            snapshot = read_immutable_query_set(query_path)
            self.assertEqual(snapshot["bytes"], raw)
            self.assertEqual(snapshot["sha256"], hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
