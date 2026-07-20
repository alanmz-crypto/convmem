"""Acceptance contract tests for exclude --purge (N1–N21 + audit hardening)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from chroma_store import ChromaStore
from ingest import (
    _commit_chunk_to_stores,
    exclude_processed_path,
    load_processed,
    sha256_file,
    watch_skip_reason,
)
from purge_locks import (
    export_flock,
    export_lock_depth,
    source_lock_depth,
    source_lock_path,
)
from source_purge import (
    assert_lock_ordering_ok,
    execute_purge,
    preview_purge,
    undo_exclude_source,
)
from tests.purge_test_util import patch_export_flock, patch_source_flock, purge_cfg as _cfg


def _seed(root: Path, src: Path, *, n_units: int = 2, n_sum: int = 1) -> str:
    (root / "chroma").mkdir(exist_ok=True)
    (root / "processed.json").write_text("{}", encoding="utf-8")
    src.write_text("payload-seed\n", encoding="utf-8")
    canon = str(src.resolve())
    store = ChromaStore(str(root / "chroma"))
    for i in range(n_units):
        store.add_unit(
            f"u{i}",
            f"doc-{i}",
            [1.0, 0.0],
            {"id": f"u{i}", "title": f"T{i}", "source_path": canon},
        )
    for i in range(n_sum):
        store.add_summary(
            f"s{i}",
            f"sum-{i}",
            [1.0, 0.0],
            {"id": f"s{i}", "source_path": canon},
        )
    store.close()
    lines = [
        json.dumps({"id": f"u{i}", "source_path": canon}) for i in range(n_units)
    ]
    (root / "knowledge_units.jsonl").write_text(
        "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
    )
    return canon


def _active_markers(processed: dict, path_key: str) -> list[str]:
    out = []
    for key, entry in processed.items():
        if not isinstance(entry, dict) or not entry.get("excluded"):
            continue
        ep = entry.get("path")
        if ep and str(Path(ep).expanduser().resolve()) == path_key:
            out.append(key)
    return out


def _chroma_jsonl_counts(cfg: dict, canon: str) -> tuple[int, int, int]:
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        units = int(store.count_for_source_path("knowledge_units", canon))
        summaries = int(
            store.count_for_source_path("conversation_summaries", canon)
        )
    finally:
        store.close()
    export = Path(cfg["index"]["units_export"])
    jsonl = 0
    if export.is_file():
        for line in export.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("source_path") == canon:
                jsonl += 1
    return units, summaries, jsonl


class ExcludeSourcePurgeContractTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    def test_n8_all_sinks_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n8.jsonl"
            canon = _seed(root, src)
            res = execute_purge(cfg, canon, reason="n8")
            self.assertEqual(res.exit_code, 0, res.message)
            self.assertEqual(_chroma_jsonl_counts(cfg, canon), (0, 0, 0))

    def test_n4_exact_path_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            a = root / "note.jsonl"
            b = root / "note.jsonl.bak"
            _seed(root, a)
            # seed B separately
            b.write_text("b\n", encoding="utf-8")
            bcanon = str(b.resolve())
            store = ChromaStore(str(root / "chroma"))
            store.add_unit(
                "ub", "db", [1.0, 0.0], {"id": "ub", "source_path": bcanon}
            )
            store.close()
            with open(cfg["index"]["units_export"], "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"id": "ub", "source_path": bcanon}) + "\n")
            res = execute_purge(cfg, str(a.resolve()), reason="n4")
            self.assertEqual(res.exit_code, 0, res.message)
            self.assertEqual(_chroma_jsonl_counts(cfg, bcanon)[0], 1)

    def test_n13_legacy_expanduser_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td) / "home"
            fake_home.mkdir()
            with mock.patch.dict(os.environ, {"HOME": str(fake_home)}):
                root = Path(td) / "data"
                root.mkdir()
                cfg = _cfg(root)
                rel = Path("~/legacy.jsonl")
                real = fake_home / "legacy.jsonl"
                real.write_text("x\n", encoding="utf-8")
                home_raw = str(rel.expanduser())
                self.assertTrue(home_raw.startswith(str(fake_home)))
                (root / "chroma").mkdir()
                (root / "processed.json").write_text("{}", encoding="utf-8")
                store = ChromaStore(str(root / "chroma"))
                store.add_unit(
                    "leg",
                    "d",
                    [1.0, 0.0],
                    {"id": "leg", "source_path": home_raw},
                )
                store.close()
                (root / "knowledge_units.jsonl").write_text(
                    json.dumps({"id": "leg", "source_path": home_raw}) + "\n",
                    encoding="utf-8",
                )
                # Never wrote under the real HOME
                self.assertFalse(
                    (Path.home() / "legacy.jsonl").exists()
                    if Path.home() != fake_home
                    else False
                )
                res = execute_purge(cfg, str(rel), reason="n13")
                self.assertEqual(res.exit_code, 0, res.message)
                store = ChromaStore(str(root / "chroma"))
                ids = {m["id"] for m in store.units_metadata(include_superseded=True)}
                store.close()
                self.assertNotIn("leg", ids)

    def test_n3_unrelated_export_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            a = root / "a.jsonl"
            canon_a = _seed(root, a)
            other = root / "b.jsonl"
            other.write_text("b\n", encoding="utf-8")
            other_path = str(other.resolve())
            with open(cfg["index"]["units_export"], "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"id": "kept", "source_path": other_path}) + "\n")

            barrier = threading.Event()
            errors: list = []

            def purge():
                try:
                    def hold():
                        barrier.set()
                        time.sleep(0.2)

                    res = execute_purge(
                        cfg,
                        canon_a,
                        reason="n3",
                        _hooks={"after_jsonl_rewrite": hold},
                    )
                    self.assertEqual(res.exit_code, 0, res.message)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    errors.append(exc)

            def appender():
                try:
                    self.assertTrue(barrier.wait(5))
                    with export_flock(cfg):
                        with open(
                            cfg["index"]["units_export"], "a", encoding="utf-8"
                        ) as fh:
                            fh.write(
                                json.dumps(
                                    {"id": "late", "source_path": other_path}
                                )
                                + "\n"
                            )
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    errors.append(exc)

            t1 = threading.Thread(target=purge)
            t2 = threading.Thread(target=appender)
            t1.start()
            t2.start()
            t1.join(15)
            t2.join(15)
            self.assertEqual(errors, [])
            text = Path(cfg["index"]["units_export"]).read_text(encoding="utf-8")
            self.assertIn(other_path, text)
            self.assertIn("kept", text)
            self.assertIn("late", text)

    def test_n1_purge_then_ingest_batch_aborts(self):
        """Production _commit_chunk_to_stores aborts after overlapping purge."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n1.jsonl"
            canon = _seed(root, src)
            file_hash = sha256_file(canon)
            start_commit = threading.Event()
            purge_done = threading.Event()
            result: dict = {}

            def ingester():
                self.assertTrue(start_commit.wait(5))
                self.assertTrue(purge_done.wait(5))
                ok, _, n, _, _ = _commit_chunk_to_stores(
                    cfg=cfg,
                    idx=cfg["index"],
                    path_key=canon,
                    path=canon,
                    file_hash=file_hash,
                    chroma_dir=cfg["index"]["chroma_dir"],
                    units_export=Path(cfg["index"]["units_export"]),
                    doc_id="d1",
                    summary="s",
                    summary_embedding=[1.0, 0.0],
                    metadata={"id": "d1", "source_path": canon},
                    units_to_add=[
                        (
                            {"id": "orphan", "source_path": canon},
                            "doc",
                            [1.0, 0.0],
                            {"id": "orphan", "source_path": canon},
                        )
                    ],
                    verbose=False,
                )
                result["ok"] = ok
                result["n"] = n

            def purger():
                start_commit.set()
                res = execute_purge(cfg, canon, reason="n1")
                result["purge"] = res.exit_code
                purge_done.set()

            t1 = threading.Thread(target=ingester)
            t2 = threading.Thread(target=purger)
            t1.start()
            # Give ingester time to wait on purge_done before purge... order:
            # Start both: ingester waits purge_done; purger runs purge then signals.
            # Better barrier: ingest reaches pre-commit unlocked, then purge, then commit.
            t2.start()
            t1.join(15)
            t2.join(15)
            self.assertEqual(result.get("purge"), 0)
            self.assertIs(result.get("ok"), False)
            self.assertEqual(result.get("n"), 0)
            units, summaries, jsonl = _chroma_jsonl_counts(cfg, canon)
            self.assertEqual((units, summaries, jsonl), (0, 0, 0))
            store = ChromaStore(cfg["index"]["chroma_dir"])
            ids = {m["id"] for m in store.units_metadata(include_superseded=True)}
            store.close()
            self.assertNotIn("orphan", ids)

    def test_n2_ingest_then_purge_clears(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            src = root / "n2.jsonl"
            src.write_text("n2\n", encoding="utf-8")
            canon = str(src.resolve())
            file_hash = sha256_file(canon)
            ok, _, n, _, _ = _commit_chunk_to_stores(
                cfg=cfg,
                idx=cfg["index"],
                path_key=canon,
                path=canon,
                file_hash=file_hash,
                chroma_dir=cfg["index"]["chroma_dir"],
                units_export=Path(cfg["index"]["units_export"]),
                doc_id="d2",
                summary="summary",
                summary_embedding=[1.0, 0.0],
                metadata={"id": "d2", "source_path": canon},
                units_to_add=[
                    (
                        {"id": "u2", "source_path": canon},
                        "doc2",
                        [1.0, 0.0],
                        {"id": "u2", "source_path": canon},
                    )
                ],
                verbose=False,
            )
            self.assertTrue(ok)
            self.assertEqual(n, 1)
            self.assertEqual(_chroma_jsonl_counts(cfg, canon)[0], 1)
            res = execute_purge(cfg, canon, reason="n2")
            self.assertEqual(res.exit_code, 0, res.message)
            self.assertEqual(_chroma_jsonl_counts(cfg, canon), (0, 0, 0))

    def test_n5_partial_retry_converges(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n5.jsonl"
            canon = _seed(root, src)

            def boom():
                raise RuntimeError("crash-after-units")

            with self.assertRaises(RuntimeError):
                execute_purge(
                    cfg, canon, reason="n5", _hooks={"after_units": boom}
                )
            res = execute_purge(cfg, canon, reason="n5-retry")
            self.assertEqual(res.exit_code, 0, res.message)
            self.assertEqual(_chroma_jsonl_counts(cfg, canon), (0, 0, 0))

    def test_n6_preview_no_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n6.jsonl"
            canon = _seed(root, src)
            before = Path(cfg["index"]["units_export"]).read_text(encoding="utf-8")
            preview = preview_purge(cfg, canon)
            self.assertGreater(preview.units, 0)
            after = Path(cfg["index"]["units_export"]).read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertEqual(load_processed(cfg["index"]["processed_log"]), {})

    def test_n10_malformed_jsonl_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n10.jsonl"
            canon = _seed(root, src)
            export = Path(cfg["index"]["units_export"])
            original = export.read_text(encoding="utf-8") + "{not-json\n"
            export.write_text(original, encoding="utf-8")
            res = execute_purge(cfg, canon, reason="n10")
            self.assertEqual(res.exit_code, 1)
            self.assertEqual(export.read_text(encoding="utf-8"), original)

    def test_n9_lock_ordering(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            with export_flock(cfg):
                with self.assertRaises(RuntimeError):
                    assert_lock_ordering_ok(acquiring="source")

    def test_n11_yes_and_decline_cli(self):
        import convmem as convmem_mod
        from typer.testing import CliRunner

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n11.jsonl"
            canon = _seed(root, src)
            runner = CliRunner()
            with mock.patch.object(convmem_mod, "_guard_write", lambda: None):
                with mock.patch("config.load_config", return_value=cfg):
                    declined = runner.invoke(
                        convmem_mod.app,
                        ["exclude", canon, "--purge"],
                        input="n\n",
                    )
                    self.assertEqual(declined.exit_code, 0, declined.output)
                    self.assertIn("Aborted", declined.output)
                    self.assertEqual(
                        _chroma_jsonl_counts(cfg, canon)[0] > 0, True
                    )
                    yes = runner.invoke(
                        convmem_mod.app,
                        ["exclude", canon, "--purge", "--yes"],
                    )
                    self.assertEqual(yes.exit_code, 0, yes.output)
                    self.assertEqual(_chroma_jsonl_counts(cfg, canon), (0, 0, 0))

    def test_n12_undo_after_purge(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n12.jsonl"
            canon = _seed(root, src)
            self.assertEqual(execute_purge(cfg, canon, reason="n12").exit_code, 0)
            self.assertTrue(undo_exclude_source(cfg, canon))
            proc = load_processed(cfg["index"]["processed_log"])
            self.assertEqual(_active_markers(proc, canon), [])
            self.assertEqual(_chroma_jsonl_counts(cfg, canon), (0, 0, 0))

    def test_undo_blocked_until_purge_releases_fence(self):
        """Overlapping undo waits on production source_flock; fence intact at purge return."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "undo-race.jsonl"
            canon = _seed(root, src)
            release_purge = threading.Event()
            fence_held = threading.Event()
            state: dict = {}
            undo_ok = {"ok": False}
            patch_ready = threading.Event()

            def after_exclusion():
                fence_held.set()
                release_purge.wait(10)

            def purge_thread():
                with patch_source_flock() as ev:
                    state["ev"] = ev
                    patch_ready.set()
                    res = execute_purge(
                        cfg,
                        canon,
                        reason="undo-race",
                        _hooks={"after_exclusion": after_exclusion},
                    )
                    state["purge_exit"] = res.exit_code
                    state["markers_at_purge_return"] = _active_markers(
                        load_processed(cfg["index"]["processed_log"]), canon
                    )

            def undo_thread():
                undo_ok["ok"] = undo_exclude_source(cfg, canon)

            t_purge = threading.Thread(target=purge_thread, name="purge")
            t_purge.start()
            self.assertTrue(patch_ready.wait(5))
            self.assertTrue(fence_held.wait(5))
            self.assertTrue(
                _active_markers(load_processed(cfg["index"]["processed_log"]), canon)
            )
            t_undo = threading.Thread(target=undo_thread, name="undo")
            t_undo.start()
            self.assertTrue(state["ev"]["wait_undo"].wait(5))
            self.assertFalse(state["ev"]["acq_undo"].is_set())
            release_purge.set()
            t_purge.join(10)
            t_undo.join(10)
            self.assertEqual(state.get("purge_exit"), 0)
            self.assertTrue(state.get("markers_at_purge_return"))
            self.assertTrue(state["ev"]["acq_undo"].is_set())
            self.assertTrue(undo_ok["ok"])
            self.assertEqual(
                _active_markers(load_processed(cfg["index"]["processed_log"]), canon),
                [],
            )


    def test_n14_concurrent_same_source_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n14.jsonl"
            canon = _seed(root, src)
            results: list = []
            errors: list = []

            def run():
                try:
                    results.append(execute_purge(cfg, canon, reason="n14"))
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    errors.append(exc)

            t1 = threading.Thread(target=run)
            t2 = threading.Thread(target=run)
            t1.start()
            t2.start()
            t1.join(15)
            t2.join(15)
            self.assertEqual(errors, [])
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.exit_code == 0 for r in results))

    def test_n15_alternate_root_inter_model_lock_contention(self):
        """Non-sibling paths: purge blocks on production inter-model source_flock."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            processed = root / "proc" / "processed.json"
            chroma = root / "vec" / "chroma"
            export = root / "exp" / "units.jsonl"
            processed.parent.mkdir(parents=True)
            chroma.mkdir(parents=True)
            export.parent.mkdir(parents=True)
            processed.write_text("{}", encoding="utf-8")
            export.write_text("", encoding="utf-8")
            cfg = {
                "index": {
                    "processed_log": str(processed),
                    "chroma_dir": str(chroma),
                    "units_export": str(export),
                }
            }
            self.assertNotEqual(processed.parent.resolve(), chroma.parent.resolve())
            self.assertNotEqual(processed.parent.resolve(), export.parent.resolve())
            doc = root / "docs" / "inter-model" / "PLAN-n15.md"
            doc.parent.mkdir(parents=True)
            doc.write_text("## Sec\n\nBody for n15.\n", encoding="utf-8")
            path_key = str(doc.resolve())
            expected_lock = source_lock_path(cfg, path_key)
            self.assertTrue(str(expected_lock).startswith(str(processed.parent.resolve())))
            self.assertNotIn("/.local/share/convmem/locks", str(expected_lock))
            from adapters.inter_model_doc import parse
            from inter_model_index import index_inter_model_messages
            messages = parse(str(doc))
            release_ingest = threading.Event()
            state: dict = {}
            patch_ready = threading.Event()

            def hold():
                release_ingest.wait(10)

            def ingest_thread():
                with patch_source_flock(after_acquire={"ingest": hold}) as ev:
                    state["ev"] = ev
                    patch_ready.set()
                    with mock.patch(
                        "inter_model_index.ollama_embed", return_value=[0.1, 0.2]
                    ):
                        state["n"] = index_inter_model_messages(
                            str(doc),
                            messages,
                            path_key=path_key,
                            chroma_dir=str(chroma),
                            embed_model="nomic-embed-text",
                            ollama_host="http://localhost:11434",
                            cfg=cfg,
                            verbose=False,
                            units_export=export,
                        )

            def purge_thread():
                state["purge"] = execute_purge(cfg, path_key, reason="n15")

            t_ing = threading.Thread(target=ingest_thread, name="ingest")
            t_ing.start()
            self.assertTrue(patch_ready.wait(5))
            self.assertTrue(state["ev"]["acq_ingest"].wait(5))
            t_purge = threading.Thread(target=purge_thread, name="purge")
            t_purge.start()
            self.assertTrue(state["ev"]["wait_purge"].wait(5))
            self.assertFalse(state["ev"]["acq_purge"].is_set())
            release_ingest.set()
            t_ing.join(10)
            t_purge.join(10)
            self.assertEqual(state.get("n"), 1)
            self.assertTrue(state["ev"]["acq_purge"].is_set())
            self.assertEqual(state["purge"].exit_code, 0, state["purge"].message)
            self.assertEqual(_chroma_jsonl_counts(cfg, path_key), (0, 0, 0))


    def test_n16_missing_file_exclusion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            gone = root / "deleted.jsonl"
            path = str(gone)  # absolute, never created
            store = ChromaStore(str(root / "chroma"))
            store.add_unit(
                "g1", "d", [1.0, 0.0], {"id": "g1", "source_path": path}
            )
            store.close()
            (root / "knowledge_units.jsonl").write_text(
                json.dumps({"id": "g1", "source_path": path}) + "\n",
                encoding="utf-8",
            )
            res = execute_purge(cfg, path, reason="n16")
            self.assertEqual(res.exit_code, 0, res.message)
            self.assertTrue(res.exclusion_key.startswith("purged:"))
            proc = load_processed(cfg["index"]["processed_log"])
            self.assertEqual(_active_markers(proc, path), [res.exclusion_key])
            self.assertEqual(watch_skip_reason(path, processed=proc), "excluded")
            self.assertTrue(undo_exclude_source(cfg, path))

    def test_missing_file_clears_prior_same_path_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            src = root / "gone.jsonl"
            src.write_text("old\n", encoding="utf-8")
            path = str(src.resolve())
            old_hash = sha256_file(path)
            exclude_processed_path(
                cfg["index"]["processed_log"],
                path,
                old_hash,
                reason="old-soft",
            )
            src.unlink()
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            res = execute_purge(cfg, path, reason="clear-old")
            self.assertEqual(res.exit_code, 0, res.message)
            proc = load_processed(cfg["index"]["processed_log"])
            active = _active_markers(proc, path)
            self.assertEqual(len(active), 1)
            self.assertTrue(active[0].startswith("purged:"))
            self.assertFalse(proc.get(old_hash, {}).get("excluded"))

    def test_ledger_target_no_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "keep.jsonl"
            canon = _seed(root, src)
            before_proc = Path(cfg["index"]["processed_log"]).read_text(
                encoding="utf-8"
            )
            before_export = Path(cfg["index"]["units_export"]).read_text(
                encoding="utf-8"
            )
            before_counts = _chroma_jsonl_counts(cfg, canon)
            res = execute_purge(cfg, "ledger:obs_123", reason="ledger")
            self.assertEqual(res.exit_code, 1)
            self.assertEqual(res.candidates, [])
            self.assertEqual(
                Path(cfg["index"]["processed_log"]).read_text(encoding="utf-8"),
                before_proc,
            )
            self.assertEqual(
                Path(cfg["index"]["units_export"]).read_text(encoding="utf-8"),
                before_export,
            )
            self.assertEqual(_chroma_jsonl_counts(cfg, canon), before_counts)
            locks = root / "locks"
            self.assertFalse(locks.exists())

    def test_n17_no_lock_during_llm_embed(self):
        """Normal ingest: summarize/distill/embed run with lock depths zero."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
            Path(cfg["index"]["units_export"]).write_text("", encoding="utf-8")
            src = root / "agent-transcripts" / "sess" / "chat.jsonl"
            src.parent.mkdir(parents=True)
            src.write_text(
                json.dumps(
                    {
                        "role": "user",
                        "message": {
                            "content": [
                                {"type": "text", "text": "Hello n17 contract path."}
                            ]
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            depths = {"summarize": [], "distill": [], "embed": []}

            def summarize_probe(*_a, **_k):
                depths["summarize"].append((source_lock_depth(), export_lock_depth()))
                return "summary for n17"

            def distill_probe(*_a, **_k):
                depths["distill"].append((source_lock_depth(), export_lock_depth()))
                return [
                    {
                        "type": "explanation",
                        "title": "N17",
                        "summary": "unit summary",
                        "keywords": ["n17"],
                        "confidence": 0.9,
                        "domain": "coding.tooling",
                    }
                ]

            def embed_probe(*_a, **_k):
                depths["embed"].append((source_lock_depth(), export_lock_depth()))
                return [0.1, 0.2]

            full_cfg = {
                "index": {**cfg["index"], "chunk_size": 60, "chunk_overlap": 10},
                "models": {
                    "summarize_model": "dummy",
                    "distill_model": "dummy",
                    "embed_model": "dummy",
                    "ollama_host": "http://localhost:11434",
                },
                "distill": {"min_confidence": 0.1},
                "sources": {"inventory": str(root / "inventory.json")},
            }
            (root / "inventory.json").write_text("[]", encoding="utf-8")
            with mock.patch("ingest.load_config", return_value=full_cfg), mock.patch(
                "ingest.summarize", side_effect=summarize_probe
            ), mock.patch("ingest.distill", side_effect=distill_probe), mock.patch(
                "ingest.ollama_embed", side_effect=embed_probe
            ), mock.patch("brief.refresh_brief_after_change", lambda *_a, **_k: None):
                from ingest import index as ingest_index
                stats = ingest_index(force_file=str(src), verbose=False)
            self.assertEqual(stats["files_processed"], 1)
            self.assertTrue(depths["summarize"])
            self.assertTrue(depths["distill"])
            self.assertTrue(depths["embed"])
            for phase, samples in depths.items():
                self.assertTrue(all(d == (0, 0) for d in samples), phase)


    def test_n18_failure_injection_matrix(self):
        stages = [
            ("before_exclusion", False),
            ("after_exclusion", True),
            ("after_units", True),
            ("after_summaries", True),
            ("before_export_lock", True),
            ("after_export_lock", True),
            ("after_jsonl_tmp_write", True),  # F6
            ("after_jsonl_rename", True),  # F7
        ]
        for stage, expect_excl in stages:
            with self.subTest(stage=stage):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    cfg = _cfg(root)
                    src = root / f"{stage}.jsonl"
                    _seed(root, src)

                    def boom(stage_name=stage):
                        raise RuntimeError(f"crash-{stage_name}")

                    with self.assertRaises(RuntimeError):
                        execute_purge(
                            cfg, str(src.resolve()), reason=stage, _hooks={stage: boom}
                        )
                    proc = load_processed(cfg["index"]["processed_log"])
                    excluded = any(
                        isinstance(e, dict) and e.get("excluded")
                        for e in proc.values()
                    )
                    self.assertEqual(excluded, expect_excl, stage)
                    res = execute_purge(cfg, str(src.resolve()), reason=f"{stage}-retry")
                    self.assertEqual(res.exit_code, 0, f"{stage}: {res.message}")

        # F8 residual
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "f8.jsonl"
            _seed(root, src)
            res = execute_purge(
                cfg, str(src.resolve()), reason="f8", _hooks={"inject_residual": True}
            )
            self.assertEqual(res.exit_code, 1)
            self.assertIn("postcondition", res.message)

        # F9 chroma locked
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "f9.jsonl"
            _seed(root, src)
            res = execute_purge(
                cfg,
                str(src.resolve()),
                reason="f9",
                _hooks={"force_chroma_locked": True},
            )
            self.assertEqual(res.exit_code, 1)
            self.assertIn("Chroma locked", res.message)
            proc = load_processed(cfg["index"]["processed_log"])
            self.assertTrue(
                any(isinstance(e, dict) and e.get("excluded") for e in proc.values())
            )

        # F10 malformed
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "f10.jsonl"
            canon = _seed(root, src)
            export = Path(cfg["index"]["units_export"])
            export.write_text(
                export.read_text(encoding="utf-8") + "NOT_JSON\n", encoding="utf-8"
            )
            res = execute_purge(cfg, canon, reason="f10")
            self.assertEqual(res.exit_code, 1)

    def test_n19_superseded_cache_exact_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n19.jsonl"
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            src.write_text("x", encoding="utf-8")
            canon = str(src.resolve())
            other = root / "other.jsonl"
            other.write_text("o", encoding="utf-8")
            other_path = str(other.resolve())
            store = ChromaStore(str(root / "chroma"))
            store.add_unit(
                "live",
                "d",
                [1.0, 0.0],
                {"id": "live", "title": "L", "source_path": canon},
            )
            store.add_unit(
                "dead",
                "d",
                [1.0, 0.0],
                {
                    "id": "dead",
                    "title": "D",
                    "source_path": canon,
                    "superseded": True,
                    "superseded_by": "live",
                },
            )
            store.add_unit(
                "keep",
                "d",
                [1.0, 0.0],
                {"id": "keep", "title": "K", "source_path": other_path},
            )
            before = store.count_units(include_superseded=False)
            self.assertEqual(before, 2)  # live + keep
            store.close()
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            self.assertEqual(execute_purge(cfg, canon, reason="n19").exit_code, 0)
            store = ChromaStore(str(root / "chroma"))
            ids = {m["id"] for m in store.units_metadata(include_superseded=True)}
            self.assertNotIn("live", ids)
            self.assertNotIn("dead", ids)
            self.assertIn("keep", ids)
            self.assertEqual(store.count_units(include_superseded=False), 1)
            store.close()

    def test_n20_postcondition_export_lock_barrier(self):
        """JSONL postcondition under export lock; append waits then succeeds."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n20.jsonl"
            canon = _seed(root, src)
            other = root / "other.jsonl"
            other.write_text("o", encoding="utf-8")
            other_path = str(other.resolve())
            release_purge = threading.Event()
            in_post = threading.Event()
            state: dict = {}
            patch_ready = threading.Event()

            def after_rewrite():
                in_post.set()
                release_purge.wait(10)

            def purge_thread():
                with patch_export_flock(extra_modules=[sys.modules[__name__]]) as ev:
                    state["ev"] = ev
                    patch_ready.set()
                    res = execute_purge(
                        cfg,
                        canon,
                        reason="n20",
                        _hooks={"after_jsonl_rewrite": after_rewrite},
                    )
                    state["purge_exit"] = res.exit_code
                    state["residual"] = _chroma_jsonl_counts(cfg, canon)

            def append_thread():
                with export_flock(cfg):
                    with open(cfg["index"]["units_export"], "a", encoding="utf-8") as fh:
                        fh.write(
                            json.dumps({"id": "o1", "source_path": other_path}) + "\n"
                        )
                    state["appended"] = True

            t_purge = threading.Thread(target=purge_thread, name="purge")
            t_purge.start()
            self.assertTrue(patch_ready.wait(5))
            self.assertTrue(in_post.wait(5))
            self.assertTrue(state["ev"]["acq_purge"].is_set())
            t_app = threading.Thread(target=append_thread, name="append")
            t_app.start()
            self.assertTrue(state["ev"]["wait_append"].wait(5))
            self.assertFalse(state["ev"]["acq_append"].is_set())
            release_purge.set()
            t_purge.join(10)
            t_app.join(10)
            self.assertEqual(state.get("purge_exit"), 0)
            self.assertEqual(state.get("residual"), (0, 0, 0))
            self.assertTrue(state["ev"]["acq_append"].is_set())
            self.assertTrue(state.get("appended"))
            text = Path(cfg["index"]["units_export"]).read_text(encoding="utf-8")
            self.assertIn(other_path, text)


    def test_n21_preview_filesystem_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n21.jsonl"
            _seed(root, src)

            def snap(base: Path) -> dict[str, float]:
                out = {}
                for p in base.rglob("*"):
                    if p.is_file():
                        out[str(p.relative_to(base))] = p.stat().st_mtime_ns
                return out

            before_files = snap(root)
            before_dirs = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir()
            )
            preview_purge(cfg, str(src.resolve()))
            with self.assertRaises(ValueError):
                preview_purge(cfg, "ledger:obs_x")
            after_files = snap(root)
            after_dirs = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir()
            )
            self.assertEqual(before_dirs, after_dirs)
            self.assertEqual(before_files, after_files)

    def test_n7_inter_model_source_type(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
            Path(cfg["index"]["units_export"]).write_text("", encoding="utf-8")
            doc = root / "docs" / "inter-model" / "PLAN-n7.md"
            doc.parent.mkdir(parents=True)
            doc.write_text("## One\n\nAlpha.\n", encoding="utf-8")
            path_key = str(doc.resolve())
            from adapters.inter_model_doc import parse
            from inter_model_index import index_inter_model_messages

            with mock.patch(
                "inter_model_index.ollama_embed", return_value=[0.1, 0.2]
            ):
                n = index_inter_model_messages(
                    str(doc),
                    parse(str(doc)),
                    path_key=path_key,
                    chroma_dir=cfg["index"]["chroma_dir"],
                    embed_model="nomic-embed-text",
                    ollama_host="http://localhost:11434",
                    cfg=cfg,
                    verbose=False,
                    units_export=Path(cfg["index"]["units_export"]),
                )
            self.assertEqual(n, 1)
            self.assertEqual(execute_purge(cfg, path_key, reason="n7").exit_code, 0)
            self.assertEqual(_chroma_jsonl_counts(cfg, path_key), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
