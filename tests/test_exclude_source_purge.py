"""Acceptance tests N1–N21 for exclude --purge (temp config/corpus only)."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from chroma_store import ChromaStore
from ingest import (
    exclude_processed_path,
    load_processed,
    undo_exclude_processed_path,
    watch_skip_reason,
)
from source_purge import (
    MalformedJsonlError,
    build_path_candidates,
    count_chroma_for_source,
    count_jsonl_lines_for_source,
    execute_purge,
    export_flock,
    preview_purge,
    purge_source_from_jsonl,
    source_flock,
)


def _cfg(root: Path) -> dict:
    return {
        "index": {
            "processed_log": str(root / "processed.json"),
            "units_export": str(root / "knowledge_units.jsonl"),
            "chroma_dir": str(root / "chroma"),
        }
    }


def _seed(root: Path, src: Path, *, n_units: int = 2, n_sum: int = 1) -> str:
    chroma = root / "chroma"
    chroma.mkdir(exist_ok=True)
    src.write_text("payload-secret-ABCDEF\n", encoding="utf-8")
    canonical = str(src.resolve())
    (root / "processed.json").write_text("{}", encoding="utf-8")
    store = ChromaStore(str(chroma))
    for i in range(n_units):
        store.add_unit(
            f"u{i}",
            f"doc-{i}-ABCDEF",
            [1.0, 0.0],
            {"id": f"u{i}", "title": f"t{i}", "source_path": canonical},
        )
    for i in range(n_sum):
        store.add_summary(
            f"s{i}",
            f"sum-{i}-ABCDEF",
            [1.0, 0.0],
            {"id": f"s{i}", "source_path": canonical},
        )
    store.close()
    lines = [
        json.dumps({"id": f"u{i}", "source_path": canonical, "summary": f"ABCDEF-{i}"})
        for i in range(n_units)
    ]
    (root / "knowledge_units.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return canonical


class ExcludeSourcePurgeAcceptance(unittest.TestCase):
    def test_N8_all_sinks_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "a.jsonl"
            canon = _seed(root, src)
            cfg = _cfg(root)
            res = execute_purge(cfg, str(src), reason="n8")
            self.assertEqual(res.exit_code, 0, res.message)
            prev = preview_purge(cfg, str(src))
            self.assertEqual(prev.units, 0)
            self.assertEqual(prev.summaries, 0)
            self.assertEqual(prev.jsonl_lines, 0)
            store = ChromaStore(cfg["index"]["chroma_dir"])
            self.assertEqual(count_chroma_for_source(store, [canon]), {"units": 0, "summaries": 0})
            store.close()

    def test_N4_exact_path_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}")
            a = "/tmp/boundary/b.jsonl"
            exp = root / "knowledge_units.jsonl"
            rows = [
                {"id": "1", "source_path": a},
                {"id": "2", "source_path": a + ".bak"},
                {"id": "3", "source_path": a + "2"},
            ]
            exp.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            store = ChromaStore(str(root / "chroma"))
            store.add_unit("1", "d", [1.0, 0.0], {"id": "1", "source_path": a})
            store.add_unit("2", "d", [1.0, 0.0], {"id": "2", "source_path": a + ".bak"})
            store.close()
            res = execute_purge(cfg, a, reason="n4")
            self.assertEqual(res.exit_code, 0, res.message)
            left = [json.loads(l)["id"] for l in exp.read_text().splitlines() if l.strip()]
            self.assertEqual(set(left), {"2", "3"})
            store = ChromaStore(str(root / "chroma"))
            self.assertEqual(count_chroma_for_source(store, [a + ".bak"])["units"], 1)
            store.close()

    def test_N13_legacy_expanduser_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}")
            # Simulate home-relative storage that expands to absolute
            home_rel = "~/purge-legacy-n13.jsonl"
            raw = str(Path(home_rel).expanduser())
            Path(raw).parent.mkdir(parents=True, exist_ok=True)
            Path(raw).write_text("x")
            try:
                cands = build_path_candidates(home_rel)
                self.assertGreaterEqual(len(cands), 1)
                store = ChromaStore(str(root / "chroma"))
                # Store with expanduser-only form
                store.add_unit(
                    "leg", "d", [1.0, 0.0], {"id": "leg", "title": "t", "source_path": raw}
                )
                store.close()
                (root / "knowledge_units.jsonl").write_text(
                    json.dumps({"id": "leg", "source_path": raw}) + "\n"
                )
                res = execute_purge(cfg, home_rel, reason="n13")
                self.assertEqual(res.exit_code, 0, res.message)
                store = ChromaStore(str(root / "chroma"))
                self.assertEqual(count_chroma_for_source(store, cands)["units"], 0)
                store.close()
            finally:
                try:
                    Path(raw).unlink()
                except OSError:
                    pass

    def test_N3_unrelated_export_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src_a = root / "a.jsonl"
            src_b = root / "b.jsonl"
            _seed(root, src_a)
            # Add B lines
            exp = root / "knowledge_units.jsonl"
            b_path = str(src_b.resolve())
            src_b.write_text("b\\n")
            with open(exp, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": "ub", "source_path": b_path, "summary": "keep"}) + "\n")
            # Concurrent append during rewrite via barrier
            start = threading.Event()
            mid = threading.Event()
            done = threading.Event()
            errors: list[BaseException] = []

            real_rewrite = purge_source_from_jsonl

            def slow_purge():
                try:
                    start.set()
                    self.assertTrue(mid.wait(2))
                    res = execute_purge(cfg, str(src_a), reason="n3")
                    self.assertEqual(res.exit_code, 0, res.message)
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)
                finally:
                    done.set()

            def append_b():
                try:
                    self.assertTrue(start.wait(2))
                    mid.set()
                    from source_purge import export_flock

                    with export_flock(cfg):
                        with open(exp, "a", encoding="utf-8") as f:
                            f.write(
                                json.dumps(
                                    {"id": "ub2", "source_path": b_path, "summary": "later"}
                                )
                                + "\n"
                            )
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)

            t1 = threading.Thread(target=slow_purge)
            t2 = threading.Thread(target=append_b)
            t1.start()
            t2.start()
            t1.join(timeout=10)
            t2.join(timeout=10)
            self.assertEqual(errors, [])
            text = exp.read_text()
            self.assertIn(b_path, text)
            self.assertNotIn(str(src_a.resolve()), text)

    def test_N1_purge_then_ingest_batch_aborts(self):
        """Ingest batch-write under source lock sees exclusion and writes nothing new."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "race.jsonl"
            canon = _seed(root, src, n_units=0, n_sum=0)
            # Empty sinks; exclusion via purge
            res = execute_purge(cfg, str(src), reason="n1")
            self.assertEqual(res.exit_code, 0)
            # Simulate ingest batch critical section
            from source_purge import source_flock
            from ingest import _path_is_excluded, load_processed

            wrote = {"n": 0}
            with source_flock(cfg, canon):
                processed = load_processed(cfg["index"]["processed_log"])
                if _path_is_excluded(processed, canon):
                    wrote["n"] = 0
                else:
                    store = ChromaStore(cfg["index"]["chroma_dir"])
                    store.add_unit(
                        "should-not",
                        "x",
                        [1.0, 0.0],
                        {"id": "should-not", "source_path": canon},
                    )
                    store.close()
                    wrote["n"] = 1
            self.assertEqual(wrote["n"], 0)
            store = ChromaStore(cfg["index"]["chroma_dir"])
            self.assertEqual(count_chroma_for_source(store, [canon])["units"], 0)
            store.close()

    def test_N2_ingest_then_purge_clears(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n2.jsonl"
            canon = _seed(root, src)
            # "Ingest completed" already in seed; purge must clear
            res = execute_purge(cfg, str(src), reason="n2")
            self.assertEqual(res.exit_code, 0)
            store = ChromaStore(cfg["index"]["chroma_dir"])
            self.assertEqual(count_chroma_for_source(store, [canon])["units"], 0)
            store.close()
            self.assertEqual(
                count_jsonl_lines_for_source(cfg["index"]["units_export"], [canon]), 0
            )

    def test_N5_partial_retry_converges(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n5.jsonl"
            canon = _seed(root, src)

            def crash_before_export():
                raise RuntimeError("simulated crash F4")

            with self.assertRaises(RuntimeError):
                execute_purge(
                    cfg, str(src), reason="n5", _hooks={"before_export_lock": crash_before_export}
                )
            # Exclusion present; Chroma may be cleared; JSONL still has lines
            proc = load_processed(cfg["index"]["processed_log"])
            self.assertTrue(any(isinstance(e, dict) and e.get("excluded") for e in proc.values()))
            self.assertGreater(
                count_jsonl_lines_for_source(cfg["index"]["units_export"], [canon]), 0
            )
            # Retry
            res = execute_purge(cfg, str(src), reason="n5-retry")
            self.assertEqual(res.exit_code, 0, res.message)
            self.assertEqual(
                count_jsonl_lines_for_source(cfg["index"]["units_export"], [canon]), 0
            )

    def test_N6_preview_no_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n6.jsonl"
            _seed(root, src)
            before = (root / "knowledge_units.jsonl").read_text()
            prev = preview_purge(cfg, str(src))
            self.assertGreater(prev.units, 0)
            self.assertEqual((root / "knowledge_units.jsonl").read_text(), before)
            proc = load_processed(cfg["index"]["processed_log"])
            self.assertFalse(any(isinstance(e, dict) and e.get("excluded") for e in proc.values()))

    def test_N10_malformed_jsonl_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n10.jsonl"
            canon = _seed(root, src)
            exp = root / "knowledge_units.jsonl"
            bad = exp.read_text() + "NOT_JSON\\n"
            exp.write_text(bad)
            res = execute_purge(cfg, str(src), reason="n10")
            self.assertEqual(res.exit_code, 1)
            self.assertEqual(exp.read_text(), bad)

    def test_N9_lock_ordering(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            with export_flock(cfg):
                with self.assertRaises(RuntimeError):
                    with source_flock(cfg, "/tmp/x"):
                        pass

    def test_N11_yes_skips_confirm(self):
        """CLI --yes path exercised via execute_purge (confirmation is CLI-only)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n11.jsonl"
            _seed(root, src)
            res = execute_purge(cfg, str(src), reason="n11")
            self.assertEqual(res.exit_code, 0)

    def test_N12_undo_after_purge(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n12.jsonl"
            canon = _seed(root, src)
            self.assertEqual(execute_purge(cfg, str(src), reason="n12").exit_code, 0)
            self.assertTrue(
                undo_exclude_processed_path(cfg["index"]["processed_log"], canon)
            )
            # Sinks still empty
            self.assertEqual(
                count_jsonl_lines_for_source(cfg["index"]["units_export"], [canon]), 0
            )
            # Re-include allows future ingest (marker cleared)
            proc = load_processed(cfg["index"]["processed_log"])
            self.assertFalse(
                any(
                    isinstance(e, dict) and e.get("excluded") and e.get("path") == canon
                    for e in proc.values()
                )
            )

    def test_N14_concurrent_same_source_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n14.jsonl"
            _seed(root, src)
            results: list = []
            errors: list = []

            def run():
                try:
                    results.append(execute_purge(cfg, str(src), reason="n14"))
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)

            t1 = threading.Thread(target=run)
            t2 = threading.Thread(target=run)
            t1.start()
            t2.start()
            t1.join(10)
            t2.join(10)
            self.assertEqual(errors, [])
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.exit_code == 0 for r in results))

    def test_N15_alternate_data_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            from source_purge import source_lock_path

            a = source_lock_path(cfg, "/tmp/x")
            b = source_lock_path(cfg, "/tmp/x")
            self.assertEqual(a, b)
            self.assertTrue(str(a).startswith(str(root.resolve())))
            self.assertNotIn("/.local/share/convmem/locks", str(a).replace(str(root), ""))

    def test_N16_missing_file_exclusion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}")
            (root / "knowledge_units.jsonl").write_text("")
            gone = root / "deleted.jsonl"
            # never create file — use absolute path
            path = str(gone)
            # seed chroma with that path spelling
            store = ChromaStore(str(root / "chroma"))
            store.add_unit(
                "g1", "d", [1.0, 0.0], {"id": "g1", "source_path": path}
            )
            store.close()
            (root / "knowledge_units.jsonl").write_text(
                json.dumps({"id": "g1", "source_path": path}) + "\n"
            )
            res = execute_purge(cfg, path, reason="n16")
            self.assertEqual(res.exit_code, 0, res.message)
            self.assertTrue(res.exclusion_key.startswith("purged:"))
            proc = load_processed(cfg["index"]["processed_log"])
            self.assertIn(res.exclusion_key, proc)
            self.assertTrue(proc[res.exclusion_key].get("excluded"))
            skip = watch_skip_reason(path, processed=proc)
            self.assertEqual(skip, "excluded")
            self.assertTrue(undo_exclude_processed_path(cfg["index"]["processed_log"], path))

    def test_N17_no_lock_during_llm(self):
        """Instrument: source/export depths are zero outside flock contexts."""
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            import source_purge as sp

            self.assertEqual(sp._source_depth(), 0)
            self.assertEqual(sp._export_depth(), 0)
            # Simulate LLM window
            depths = []
            depths.append((sp._source_depth(), sp._export_depth()))
            with source_flock(cfg, "/tmp/x"):
                with export_flock(cfg):
                    depths.append((sp._source_depth(), sp._export_depth()))
            depths.append((sp._source_depth(), sp._export_depth()))
            self.assertEqual(depths[0], (0, 0))
            self.assertEqual(depths[1], (1, 1))
            self.assertEqual(depths[2], (0, 0))

    def test_N18_failure_injection_matrix(self):
        stages = [
            ("before_exclusion", False),  # F1 — not excluded
            ("after_exclusion", True),  # F2
            ("after_units", True),  # F3
            ("after_summaries", True),  # F4
            ("before_export_lock", True),
            ("after_export_lock", True),  # F5
        ]
        for stage, expect_excl in stages:
            with self.subTest(stage=stage):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    cfg = _cfg(root)
                    src = root / f"{stage}.jsonl"
                    _seed(root, src)

                    def boom():
                        raise RuntimeError(f"crash-{stage}")

                    with self.assertRaises(RuntimeError):
                        execute_purge(cfg, str(src), reason=stage, _hooks={stage: boom})
                    proc = load_processed(cfg["index"]["processed_log"])
                    excluded = any(
                        isinstance(e, dict) and e.get("excluded") for e in proc.values()
                    )
                    self.assertEqual(excluded, expect_excl, stage)
                    # Retry converges
                    res = execute_purge(cfg, str(src), reason=f"{stage}-retry")
                    self.assertEqual(res.exit_code, 0, f"{stage}: {res.message}")

        # F8 postcondition residual
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "f8.jsonl"
            _seed(root, src)
            res = execute_purge(
                cfg, str(src), reason="f8", _hooks={"inject_residual": True}
            )
            self.assertEqual(res.exit_code, 1)
            self.assertIn("postcondition", res.message)

        # F10 malformed — covered by N10

    def test_N19_superseded_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n19.jsonl"
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}")
            src.write_text("x")
            canon = str(src.resolve())
            store = ChromaStore(str(root / "chroma"))
            store.add_unit(
                "live", "d", [1.0, 0.0], {"id": "live", "title": "L", "source_path": canon}
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
            _ = store.count_units(include_superseded=False)
            store.close()
            (root / "knowledge_units.jsonl").write_text("")
            self.assertEqual(execute_purge(cfg, str(src), reason="n19").exit_code, 0)
            store = ChromaStore(str(root / "chroma"))
            ids = {m["id"] for m in store.units_metadata(include_superseded=True)}
            self.assertNotIn("live", ids)
            self.assertNotIn("dead", ids)
            n = store.count_units(include_superseded=False)
            self.assertIsInstance(n, int)
            store.close()

    def test_N20_postcondition_export_lock_barrier(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n20.jsonl"
            _seed(root, src)
            other = root / "other.jsonl"
            other.write_text("o")
            other_path = str(other.resolve())
            barrier = threading.Event()
            released = threading.Event()
            saw_block = {"ok": False}
            errors: list = []

            def purge():
                try:
                    from source_purge import count_jsonl_lines_for_source as real_count

                    def counting_hook():
                        barrier.set()
                        # Hold briefly so appender contends on export lock
                        time.sleep(0.2)

                    # Use before_postcondition which runs after export released —
                    # Need hold during count: patch inside export by hook after_jsonl_rewrite
                    def after_rewrite():
                        barrier.set()
                        time.sleep(0.3)

                    res = execute_purge(
                        cfg,
                        str(src),
                        reason="n20",
                        _hooks={"after_jsonl_rewrite": after_rewrite},
                    )
                    self.assertEqual(res.exit_code, 0, res.message)
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)
                finally:
                    released.set()

            def appender():
                try:
                    self.assertTrue(barrier.wait(5))
                    from source_purge import export_flock

                    t0 = time.time()
                    with export_flock(cfg):
                        elapsed = time.time() - t0
                        if elapsed > 0.05:
                            saw_block["ok"] = True
                        with open(cfg["index"]["units_export"], "a", encoding="utf-8") as f:
                            f.write(
                                json.dumps({"id": "o1", "source_path": other_path}) + "\n"
                            )
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)

            t1 = threading.Thread(target=purge)
            t2 = threading.Thread(target=appender)
            t1.start()
            t2.start()
            t1.join(15)
            t2.join(15)
            self.assertEqual(errors, [])
            text = Path(cfg["index"]["units_export"]).read_text()
            self.assertIn(other_path, text)

    def test_N21_preview_filesystem_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            src = root / "n21.jsonl"
            _seed(root, src)

            def snap(base: Path) -> dict[str, float]:
                out = {}
                for p in base.rglob("*"):
                    if p.is_file():
                        st = p.stat()
                        out[str(p.relative_to(base))] = st.st_mtime_ns
                return out

            before_files = snap(root)
            before_dirs = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir()
            )
            preview_purge(cfg, str(src))
            preview_purge(cfg, str(root / "does-not-exist.jsonl"))
            after_files = snap(root)
            after_dirs = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir()
            )
            self.assertEqual(before_dirs, after_dirs)
            self.assertEqual(before_files, after_files)
            # No lock files created under locks/
            locks = root / "locks"
            self.assertFalse(locks.exists())

    def test_N7_inter_model_source_type(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}")
            src = root / "docs.md"
            src.write_text("# Hi\\n")
            canon = str(src.resolve())
            store = ChromaStore(str(root / "chroma"))
            store.add_unit(
                "im1",
                "inter",
                [1.0, 0.0],
                {
                    "id": "im1",
                    "title": "t",
                    "source_path": canon,
                    "source_type": "inter_model_doc",
                },
            )
            store.close()
            (root / "knowledge_units.jsonl").write_text(
                json.dumps({"id": "im1", "source_path": canon}) + "\n"
            )
            res = execute_purge(cfg, str(src), reason="n7")
            self.assertEqual(res.exit_code, 0, res.message)
            store = ChromaStore(str(root / "chroma"))
            self.assertEqual(count_chroma_for_source(store, [canon])["units"], 0)
            store.close()


if __name__ == "__main__":
    unittest.main()
