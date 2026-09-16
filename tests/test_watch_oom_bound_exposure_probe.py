# pylint: disable=protected-access,too-many-public-methods
"""C2–C5: exposure-window probe parity, projection closure, cleanup, fail-soft."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import doctor as doctor_mod
import ledger as _ledger

from brief import gather_brief_data, write_brief
from doctor import (
    EXPOSURE_WINDOW_METADATA_KEYS,
    _exposure_window_probe,
    _iter_exposure_window_rows,
    standing_register_status,
)
from tests.watch_oom_brief_hermetic import freeze_brief_probes, write_c0_fixture
from tests.watch_oom_exposure_hermetic import (
    EXPOSURE_ROW,
    FORBIDDEN_EXPOSURE_KEYS,
    exposure_cfg,
    write_exposure_register,
    write_probe_chroma,
)

_LEDGER_INDEX_CACHE = _ledger.__dict__["_LEDGER_INDEX_CACHE"]
build_ledger_index_from_metadata = _ledger.__dict__["build_ledger_index_from_metadata"]


class ExposureProjectionClosureTests(unittest.TestCase):
    def test_iterator_requests_exact_projection(self) -> None:
        seen_keys: set[str] = set()
        include_doc: list[bool] = []

        def wrapped(chroma_dir, collection_name, *, metadata_keys=None, include_document=True):
            from chroma_readonly import iter_collection_metadata_rows as real

            if metadata_keys is not None:
                seen_keys.update(metadata_keys)
            include_doc.append(include_document)
            return real(
                chroma_dir,
                collection_name,
                metadata_keys=metadata_keys,
                include_document=include_document,
            )

        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            write_probe_chroma(
                chroma,
                [
                    {
                        "ledger_id": "obs_p0",
                        "type": "observation",
                        "severity": "critical",
                        "timestamp": "2026-06-20T10:00:00",
                    },
                    {
                        "ledger_id": "ver_p0",
                        "ledger_kind": "verification",
                        "relates_to": "obs_p0",
                        "result": "pass",
                        "timestamp": "2026-07-05T10:00:00",
                    },
                ],
            )
            with patch("doctor.iter_collection_metadata_rows", wrapped):
                _exposure_window_probe(EXPOSURE_ROW, exposure_cfg(chroma))
        self.assertEqual(
            tuple(sorted(seen_keys)),
            tuple(sorted(EXPOSURE_WINDOW_METADATA_KEYS)),
        )
        self.assertEqual(include_doc, [False])

    def test_probe_never_calls_full_row_helpers(self) -> None:
        def forbidden(*_a, **_k):
            raise AssertionError("exposure probe must not use full-row store APIs")

        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            write_probe_chroma(
                chroma,
                [
                    {
                        "ledger_id": "obs_p0",
                        "type": "observation",
                        "severity": "critical",
                        "timestamp": "2026-06-20T10:00:00",
                    },
                    {
                        "ledger_id": "ver_p0",
                        "ledger_kind": "verification",
                        "relates_to": "obs_p0",
                        "result": "pass",
                        "timestamp": "2026-07-05T10:00:00",
                    },
                ],
            )
            cache_before = dict(_LEDGER_INDEX_CACHE)
            with patch("chroma_readonly.open_readonly_unit_store", forbidden), patch(
                "chroma_readonly.collection_metadata_rows", forbidden
            ), patch("provenance_binding.provenance_identity", forbidden):
                due, detail = _exposure_window_probe(EXPOSURE_ROW, exposure_cfg(chroma))
            self.assertTrue(due, detail)
            self.assertEqual(_LEDGER_INDEX_CACHE, cache_before)

    def test_returned_rows_omit_forbidden_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            write_probe_chroma(
                chroma,
                [
                    {
                        "ledger_id": "obs_p0",
                        "type": "observation",
                        "severity": "critical",
                        "timestamp": "2026-06-20T10:00:00",
                    },
                ],
            )
            rows = list(_iter_exposure_window_rows(chroma))
        self.assertTrue(rows)
        for row in rows:
            for forbidden in FORBIDDEN_EXPOSURE_KEYS:
                self.assertNotIn(forbidden, row)


class ExposureFailSoftTests(unittest.TestCase):
    def test_standing_register_probe_error_is_advisory_due(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            reg = write_exposure_register(tmp)
            cfg = exposure_cfg(tmp / "chroma")
            with patch(
                "doctor._exposure_window_probe",
                side_effect=RuntimeError("scan failed"),
            ):
                open_n, due = standing_register_status(cfg, register_path=reg, root=tmp)
        self.assertEqual(open_n, 1)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["id"], "exposure-window-tracking")
        self.assertIn("probe error: RuntimeError", due[0]["detail"])

    def test_brief_chain_publishes_advisory_due_row(self) -> None:
        from contextlib import ExitStack

        from tests.watch_oom_brief_hermetic import FROZEN_NOW, FROZEN_NOW_ISO

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fx = write_c0_fixture(tmp)
            reg = write_exposure_register(tmp)
            out = tmp / "brief.md"
            real_datetime = __import__("datetime").datetime

            class _FrozenDateTime(real_datetime):
                @classmethod
                def now(cls, tz=None):
                    if tz is None:
                        return FROZEN_NOW.replace(tzinfo=None)
                    return FROZEN_NOW.astimezone(tz)

            with ExitStack() as stack:
                stack.enter_context(patch("brief._now_iso", return_value=FROZEN_NOW_ISO))
                stack.enter_context(patch("brief._systemd_state", return_value="enabled/active"))
                stack.enter_context(
                    patch(
                        "brief._mcp_registration",
                        return_value={
                            "cursor": "registered",
                            "crush": "registered",
                            "crush_live": "verified",
                            "stdio": "verified",
                        },
                    )
                )
                stack.enter_context(patch("brief._watch_process_memory", return_value=None))
                stack.enter_context(patch("brief._pending_decision_ingest", return_value=[]))
                stack.enter_context(patch("brief.datetime", _FrozenDateTime))
                stack.enter_context(patch("doctor._standing_register_path", return_value=reg))
                stack.enter_context(
                    patch(
                        "doctor._exposure_window_probe",
                        side_effect=ValueError("iterator broke"),
                    )
                )
                data = gather_brief_data(fx["cfg"])
                write_brief(fx["cfg"], out_path=out, quiet=True)
            self.assertTrue(out.is_file())
            text = out.read_text(encoding="utf-8")
            self.assertIn("exposure-window-tracking", text)
            self.assertIn("STANDING CHECKS DUE", text)
            standing = data.get("standing_due") or {}
            self.assertEqual(len(standing.get("due") or []), 1)
            self.assertIn("probe error: ValueError", standing["due"][0]["detail"])

    def test_brief_retains_prior_on_failure_beyond_fail_soft(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fx = write_c0_fixture(tmp)
            out = tmp / "brief.md"
            with freeze_brief_probes():
                write_brief(fx["cfg"], out_path=out, quiet=True)
                prior = out.read_text(encoding="utf-8")

                def boom(*_a, **_k):
                    raise RuntimeError("beyond fail-soft")

                with patch("brief._iter_brief_rows", boom):
                    from brief import refresh_brief_after_change

                    refresh_brief_after_change(fx["cfg"])
                self.assertEqual(out.read_text(encoding="utf-8"), prior)


class ExposureIteratorCleanupTests(unittest.TestCase):
    def test_connection_closed_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            write_probe_chroma(
                chroma,
                [
                    {
                        "ledger_id": "obs_p0",
                        "type": "observation",
                        "severity": "critical",
                        "timestamp": "2026-06-20T10:00:00",
                    },
                ],
            )
            db = chroma / "chroma.sqlite3"
            before = db.stat().st_mtime_ns
            _exposure_window_probe(EXPOSURE_ROW, exposure_cfg(chroma))
            self.assertEqual(db.stat().st_mtime_ns, before)
            self.assertFalse((chroma / "chroma.sqlite3-wal").exists())
            self.assertFalse((chroma / "chroma.sqlite3-shm").exists())

    def test_missing_db_surfaces_as_probe_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = exposure_cfg(Path(td) / "missing-chroma")
            with patch.object(doctor_mod, "_evaluate_standing_rows", wraps=doctor_mod._evaluate_standing_rows):
                open_n, due = standing_register_status(
                    cfg,
                    register_path=write_exposure_register(Path(td)),
                    root=Path(td),
                )
        self.assertEqual(open_n, 1)
        self.assertEqual(len(due), 1)
        self.assertIn("probe error:", due[0]["detail"])

    def test_iterator_failure_mid_scan_is_fail_soft(self) -> None:
        real_rows = [
            {
                "id": "emb-0000",
                "ledger_id": "obs_p0",
                "type": "observation",
                "severity": "critical",
                "timestamp": "2026-06-20T10:00:00",
            },
        ]

        def broken_iter(_chroma_dir):
            yield real_rows[0]
            raise sqlite3.OperationalError("mid-scan")

        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            write_probe_chroma(chroma, [{"ledger_id": "obs_p0", "type": "observation",
                                         "severity": "critical", "timestamp": "2026-06-20"}])
            with patch("doctor._iter_exposure_window_rows", broken_iter):
                open_n, due = standing_register_status(
                    exposure_cfg(chroma),
                    register_path=write_exposure_register(Path(td)),
                    root=Path(td),
                )
        self.assertEqual(open_n, 1)
        self.assertIn("probe error: OperationalError", due[0]["detail"])


class ExposureLedgerParityTests(unittest.TestCase):
    def test_from_metadata_matches_store_index_for_projection(self) -> None:
        from chroma_readonly import open_readonly_unit_store

        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            write_probe_chroma(
                chroma,
                [
                    {
                        "ledger_id": "obs_p0",
                        "type": "observation",
                        "severity": "critical",
                        "timestamp": "2026-06-20T10:00:00",
                    },
                    {
                        "ledger_id": "ver_p0",
                        "ledger_kind": "verification",
                        "relates_to": "obs_p0",
                        "result": "pass",
                        "timestamp": "2026-07-05T10:00:00",
                    },
                    {
                        "ledger_id": "obs_sup",
                        "type": "observation",
                        "severity": "critical",
                        "timestamp": "2026-06-20T10:00:00",
                        "superseded": True,
                    },
                ],
            )
            store = open_readonly_unit_store(chroma)
            from_store = build_ledger_index_from_metadata(store.units_metadata())
            from_iter = build_ledger_index_from_metadata(_iter_exposure_window_rows(chroma))
            self.assertEqual(set(from_store[0]), set(from_iter[0]))
            self.assertEqual(
                {k: [m.get("ledger_id") for m in v] for k, v in from_store[1].items()},
                {k: [m.get("ledger_id") for m in v] for k, v in from_iter[1].items()},
            )


if __name__ == "__main__":
    unittest.main()
