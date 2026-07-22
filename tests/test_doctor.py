"""Tests for convmem doctor."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from doctor import (
    DoctorCheck,
    _charter_register_consistency_probe,
    _check_dirty_main,
    _check_hooks_path,
    _check_standing_register,
    _check_unpushed_commits,
    _check_wip_on_main,
    _exposure_window_probe,
    _merge_order_probe,
    _standing_row_due,
    _unverified_resting_state_probe,
    doctor_exit_code,
    run_doctor,
    render_doctor_text,
    standing_register_status,
)


class DoctorTests(unittest.TestCase):
    @patch("doctor._check_index_drift")
    @patch("doctor._check_restic_password_backup")
    @patch("doctor._check_restic_external")
    @patch("doctor._check_restic")
    @patch("doctor._check_verify_script")
    @patch("doctor._check_copilot_mcp")
    @patch("doctor._check_continue_mcp")
    @patch("doctor._check_mcp_wiring")
    @patch("doctor._check_mcp_import")
    @patch("doctor._check_chroma")
    @patch("doctor._check_ollama")
    @patch("doctor._check_deepseek_key")
    @patch("doctor._check_config")
    @patch("doctor.load_config")
    def test_run_doctor_all_pass(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        mock_load,
        mock_cfg,
        mock_key,
        mock_ollama,
        mock_chroma,
        mock_mcp,
        mock_wire,
        mock_cont,
        mock_copilot,
        mock_verify,
        mock_restic,
        mock_restic_external,
        mock_restic_password_backup,
        mock_drift,
    ):
        mock_load.return_value = {"index": {"chroma_dir": "/tmp/c"}, "models": {}}
        ok = DoctorCheck("x", True, "ok")
        for mock in (
            mock_cfg,
            mock_key,
            mock_ollama,
            mock_chroma,
            mock_drift,
            mock_restic,
            mock_restic_external,
            mock_restic_password_backup,
            mock_mcp,
            mock_wire,
            mock_cont,
            mock_copilot,
        ):
            mock.return_value = ok
        mock_verify.return_value = DoctorCheck("verify_continue", True, "skipped")

        checks = run_doctor(run_verify=False)
        self.assertTrue(all(c.ok for c in checks))
        self.assertEqual(doctor_exit_code(checks), 0)

    def test_doctor_exit_code_fail(self):
        checks = [
            DoctorCheck("a", True, "ok"),
            DoctorCheck("b", False, "bad"),
        ]
        self.assertEqual(doctor_exit_code(checks), 1)

    def test_render_doctor_text_smoke(self):
        checks = [
            DoctorCheck("ollama", True, "running"),
            DoctorCheck("chroma", False, "empty collection"),
            DoctorCheck("config", True, "ok", status="warn"),
        ]
        text = render_doctor_text(checks)
        lines = text.splitlines()
        self.assertIn("[PASS] ollama: running", lines)
        self.assertIn("[FAIL] chroma: empty collection", lines)
        self.assertIn("[WARN] config: ok", lines)
        self.assertIn("doctor: 1 check(s) failed", text)
        self.assertIn("1 warning(s)", text)


class StandingRegisterTests(unittest.TestCase):
    CFG = {"index": {"chroma_dir": "/tmp/c"}, "models": {}}

    def _write(self, tmp: Path, rows: list) -> Path:
        path = tmp / "standing-checks-register.json"
        path.write_text(json.dumps({"checks": rows}), encoding="utf-8")
        return path

    def test_manual_row_due_warns_but_ok(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            path = self._write(
                tmp,
                [
                    {
                        "id": "stale",
                        "status": "open",
                        "last_verified": "2000-01-01",
                        "trigger": {"type": "manual", "max_age_days": 90},
                    }
                ],
            )
            c = _check_standing_register(self.CFG, register_path=path, root=tmp)
        self.assertEqual(c.effective_status(), "warn")
        self.assertTrue(c.ok)  # advisory — must not change exit code
        self.assertIn("stale", c.detail)

    def test_manual_row_fresh_passes(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            today = __import__("datetime").date.today().strftime("%Y-%m-%d")
            path = self._write(
                tmp,
                [
                    {
                        "id": "fresh",
                        "status": "open",
                        "last_verified": today,
                        "trigger": {"type": "manual", "max_age_days": 90},
                    }
                ],
            )
            c = _check_standing_register(self.CFG, register_path=path, root=tmp)
        self.assertEqual(c.effective_status(), "pass")
        self.assertIn("0 due", c.detail)

    def test_none_type_never_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            path = self._write(
                tmp,
                [
                    {
                        "id": "tracked",
                        "status": "open",
                        "last_verified": "2000-01-01",
                        "trigger": {"type": "none"},
                    }
                ],
            )
            c = _check_standing_register(self.CFG, register_path=path, root=tmp)
        self.assertEqual(c.effective_status(), "pass")
        self.assertIn("1 open checks, 0 due", c.detail)

    def test_probe_flags_unwired_eval(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            scripts = tmp / "scripts"
            scripts.mkdir()
            (scripts / "eval-bad.py").write_text("print('no wiring here')\n", encoding="utf-8")
            (scripts / "eval-good.py").write_text(
                "from eval_provenance import model_context\nmodel_context(cfg, m)\n",
                encoding="utf-8",
            )
            path = self._write(
                tmp,
                [
                    {
                        "id": "eval-provenance-wiring",
                        "status": "open",
                        "trigger": {"type": "probe", "probe": "eval_provenance_wiring"},
                    }
                ],
            )
            c = _check_standing_register(self.CFG, register_path=path, root=tmp)
        self.assertEqual(c.effective_status(), "warn")
        self.assertIn("eval-bad.py", c.detail)
        self.assertNotIn("eval-good.py", c.detail)

    def test_probe_honors_exemption(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            scripts = tmp / "scripts"
            scripts.mkdir()
            (scripts / "eval-retrieval.py").write_text("print('deterministic')\n", encoding="utf-8")
            path = self._write(
                tmp,
                [
                    {
                        "id": "eval-provenance-wiring",
                        "status": "open",
                        "trigger": {
                            "type": "probe",
                            "probe": "eval_provenance_wiring",
                            "exempt": [{"path": "scripts/eval-retrieval.py", "reason": "no LLM"}],
                        },
                    }
                ],
            )
            c = _check_standing_register(self.CFG, register_path=path, root=tmp)
        self.assertEqual(c.effective_status(), "pass")

    def test_malformed_register_skips(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            path = tmp / "standing-checks-register.json"
            path.write_text("{not valid json", encoding="utf-8")
            c = _check_standing_register(self.CFG, register_path=path, root=tmp)
        self.assertEqual(c.effective_status(), "skip")
        self.assertTrue(c.ok)

    def test_missing_register_skips(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            path = tmp / "nope.json"
            c = _check_standing_register(self.CFG, register_path=path, root=tmp)
        self.assertEqual(c.effective_status(), "skip")

    def test_shipped_register_is_valid(self):
        """The real register must parse and never fail the doctor exit code."""
        c = _check_standing_register(self.CFG)
        self.assertTrue(c.ok)
        self.assertIn(c.effective_status(), ("pass", "warn", "skip"))


class CadenceTriggerTests(unittest.TestCase):
    """Cadence trigger branch of _standing_row_due (via _check_standing_register)."""

    CFG = {"index": {"chroma_dir": "/tmp/c"}, "models": {}}

    def _check(self, row: dict) -> DoctorCheck:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            path = tmp / "standing-checks-register.json"
            path.write_text(json.dumps({"checks": [row]}), encoding="utf-8")
            return _check_standing_register(self.CFG, register_path=path, root=tmp)

    def test_stale_cadence_row_due(self):
        c = self._check(
            {
                "id": "parity",
                "status": "open",
                "last_verified": "2000-01-01",
                "trigger": {"type": "cadence", "interval_days": 60},
            }
        )
        self.assertEqual(c.effective_status(), "warn")
        self.assertTrue(c.ok)  # advisory — must not change exit code
        self.assertIn("parity", c.detail)
        self.assertIn("cadence", c.detail)

    def test_fresh_cadence_row_not_due(self):
        today = __import__("datetime").date.today().strftime("%Y-%m-%d")
        c = self._check(
            {
                "id": "parity",
                "status": "open",
                "last_verified": today,
                "trigger": {"type": "cadence", "interval_days": 60},
            }
        )
        self.assertEqual(c.effective_status(), "pass")
        self.assertIn("0 due", c.detail)

    def test_unparseable_last_verified_due(self):
        c = self._check(
            {
                "id": "parity",
                "status": "open",
                "last_verified": "not-a-date",
                "trigger": {"type": "cadence", "interval_days": 60},
            }
        )
        self.assertEqual(c.effective_status(), "warn")
        self.assertIn("unparseable", c.detail)


class CorpusSizeTriggerTests(unittest.TestCase):
    """Corpus-size trigger branch — collection_count patched, no real Chroma."""

    CFG = {"index": {"chroma_dir": "/tmp/c"}, "models": {}}

    def _check(self, row: dict, live_count: int) -> DoctorCheck:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            path = tmp / "standing-checks-register.json"
            path.write_text(json.dumps({"checks": [row]}), encoding="utf-8")
            with patch("doctor.collection_count", return_value=live_count):
                return _check_standing_register(self.CFG, register_path=path, root=tmp)

    def test_over_threshold_due(self):
        c = self._check(
            {
                "id": "retune",
                "status": "open",
                "trigger": {"type": "corpus_size", "baseline": 1000, "multiple": 2.0},
            },
            live_count=2001,
        )
        self.assertEqual(c.effective_status(), "warn")
        self.assertTrue(c.ok)
        self.assertIn("retune", c.detail)
        self.assertIn("2001", c.detail)

    def test_at_threshold_not_due(self):
        c = self._check(
            {
                "id": "retune",
                "status": "open",
                "trigger": {"type": "corpus_size", "baseline": 1000, "multiple": 2.0},
            },
            live_count=2000,
        )
        self.assertEqual(c.effective_status(), "pass")

    def test_zero_baseline_not_due(self):
        c = self._check(
            {
                "id": "retune",
                "status": "open",
                "trigger": {"type": "corpus_size", "baseline": 0, "multiple": 2.0},
            },
            live_count=999999,
        )
        self.assertEqual(c.effective_status(), "pass")
        self.assertIn("0 due", c.detail)


class ShippedTriggerPromotionTests(unittest.TestCase):
    """Guard the 2026-07-07 trigger triage against regression to type=none."""

    def _rows(self) -> dict:
        register = Path(__file__).resolve().parent.parent / "docs" / "standing-checks-register.json"
        data = json.loads(register.read_text(encoding="utf-8"))
        return {r["id"]: r for r in data["checks"]}

    def test_promoted_rows_keep_triggers(self):
        rows = self._rows()
        self.assertEqual(rows["adapter-parity-scan"]["trigger"]["type"], "cadence")
        self.assertEqual(rows["latency-budget"]["trigger"]["type"], "cadence")
        self.assertEqual(rows["recency-boost-retune"]["trigger"]["type"], "corpus_size")
        self.assertEqual(rows["escalation-threshold-retune"]["trigger"]["type"], "corpus_size")

    def test_recency_baseline_recorded(self):
        trig = self._rows()["recency-boost-retune"]["trigger"]
        self.assertGreater(int(trig.get("baseline") or 0), 0, "baseline lost — trigger is dead")

    def test_escalation_baseline_recorded(self):
        trig = self._rows()["escalation-threshold-retune"]["trigger"]
        self.assertGreater(int(trig.get("baseline") or 0), 0, "baseline lost — trigger is dead")

    def test_exposure_window_is_probe(self):
        trig = self._rows()["exposure-window-tracking"]["trigger"]
        self.assertEqual(trig["type"], "probe")

    def test_retro_rows_present_with_triggers(self):
        rows = self._rows()
        self.assertEqual(rows["mechanized-claims-audit"]["trigger"]["type"], "cadence")
        self.assertEqual(rows["unverified-resting-state"]["trigger"]["type"], "probe")
        self.assertEqual(rows["retro-loop-closure"]["trigger"]["type"], "manual")


class StandingRegisterStatusTests(unittest.TestCase):
    """The structured helper brief.py consumes: (open_count, due_rows)."""

    CFG = {"index": {"chroma_dir": "/tmp/unused"}, "models": {}}

    def _register(self, tmp: Path, checks: list) -> Path:
        p = tmp / "reg.json"
        p.write_text(json.dumps({"checks": checks}), encoding="utf-8")
        return p

    def test_open_count_and_empty_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            reg = self._register(tmp, [
                {"id": "a", "status": "open", "trigger": {"type": "none"}},
                {"id": "b", "status": "closed", "trigger": {"type": "none"}},
            ])
            open_n, due = standing_register_status(self.CFG, register_path=reg, root=tmp)
        self.assertEqual(open_n, 1)
        self.assertEqual(due, [])

    def test_due_row_is_structured(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            reg = self._register(tmp, [
                {"id": "stale", "status": "open",
                 "trigger": {"type": "manual", "max_age_days": 1},
                 "last_verified": "2000-01-01"},
            ])
            open_n, due = standing_register_status(self.CFG, register_path=reg, root=tmp)
        self.assertEqual(open_n, 1)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["id"], "stale")
        self.assertIn("manual", due[0]["detail"])

    def test_missing_register_quiet(self):
        with tempfile.TemporaryDirectory() as d:
            open_n, due = standing_register_status(
                self.CFG, register_path=Path(d) / "nope.json", root=Path(d)
            )
        self.assertEqual((open_n, due), (0, []))


class CharterStandingRowTests(unittest.TestCase):
    """`trigger: charter` + `status: standing` rows: excluded from the open
    count, never doctor-due, surfaced as a detail suffix."""

    CFG = {"index": {"chroma_dir": "/tmp/unused"}, "models": {}}

    def _register(self, tmp: Path, checks: list) -> Path:
        p = tmp / "reg.json"
        p.write_text(json.dumps({"checks": checks}), encoding="utf-8")
        return p

    def test_standing_row_excluded_from_open_count(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            reg = self._register(tmp, [
                {"id": "a", "status": "open", "trigger": {"type": "none"}},
                {"id": "s1", "status": "standing", "trigger": {"type": "charter"}},
                {"id": "s2", "status": "standing", "trigger": {"type": "charter"}},
            ])
            open_n, due = standing_register_status(self.CFG, register_path=reg, root=tmp)
        self.assertEqual(open_n, 1)  # only the open row is counted
        self.assertEqual(due, [])  # standing rows never surface as due

    def test_charter_row_never_due_when_called_directly(self):
        # A stale last_verified must not make a charter row due — the type,
        # not the age, governs. Guards against the row silently becoming due if
        # it is ever re-typed or reaches _standing_row_due via a status change.
        row = {"id": "s1", "status": "standing", "last_verified": "2000-01-01",
               "trigger": {"type": "charter"}}
        due, detail = _standing_row_due(row, self.CFG, Path("/tmp"), [row])
        self.assertFalse(due)
        self.assertIn("charter", detail)

    def test_detail_reports_charter_standing_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            reg = self._register(tmp, [
                {"id": "a", "status": "open", "trigger": {"type": "none"}},
                {"id": "s1", "status": "standing", "trigger": {"type": "charter"}},
                {"id": "s2", "status": "standing", "trigger": {"type": "charter"}},
            ])
            c = _check_standing_register(self.CFG, register_path=reg, root=tmp)
        self.assertEqual(c.effective_status(), "pass")
        self.assertIn("1 open checks, 0 due", c.detail)
        self.assertIn("(2 charter-standing)", c.detail)

    def test_no_suffix_when_no_standing_rows(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            reg = self._register(tmp, [
                {"id": "a", "status": "open", "trigger": {"type": "none"}},
            ])
            c = _check_standing_register(self.CFG, register_path=reg, root=tmp)
        self.assertIn("1 open checks, 0 due", c.detail)
        self.assertNotIn("charter-standing", c.detail)


class UnverifiedRestingStateProbeTests(unittest.TestCase):
    """Probe: no live uppercase UNVERIFIED marker in the mapping/charter docs."""

    LIVE = "UNVERIFIED"  # assembled below to avoid a literal in this out-of-scope file

    def _docs(self, tmp: Path, mapping: str = "", charter: str = "") -> None:
        docs = tmp / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "role-mapping.md").write_text(mapping, encoding="utf-8")
        (docs / "role-charters.md").write_text(charter, encoding="utf-8")

    def test_real_docs_clean(self):
        # Regression-lock: the shipped design docs carry no live marker today.
        root = Path(__file__).resolve().parent.parent
        due, detail = _unverified_resting_state_probe({}, root)
        self.assertFalse(due, detail)

    def test_live_marker_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._docs(tmp, mapping=f"- claim X is handled {self.LIVE}(ryan)\n")
            due, detail = _unverified_resting_state_probe({}, tmp)
        self.assertTrue(due, detail)
        self.assertIn("role-mapping.md:1", detail)

    def test_lowercase_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._docs(tmp, mapping="- was unverified last turn, now mechanized\n")
            due, detail = _unverified_resting_state_probe({}, tmp)
        self.assertFalse(due, detail)

    def test_out_of_scope_file_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._docs(tmp)  # both in-scope docs clean
            (tmp / "docs" / "engineering-team-retro-x.md").write_text(
                f"## {self.LIVE} sweep\n", encoding="utf-8"
            )
            due, detail = _unverified_resting_state_probe({}, tmp)
        self.assertFalse(due, detail)

    def test_missing_docs_not_due(self):
        with tempfile.TemporaryDirectory() as d:
            due, detail = _unverified_resting_state_probe({}, Path(d))
        self.assertFalse(due, detail)


class _FakeUnitStore:
    """Minimal ledger-index-compatible store. chroma_dir is falsy on purpose:
    build_ledger_index caches by store.chroma_dir for the process lifetime,
    and an empty key skips the cache, keeping each test isolated."""

    chroma_dir = ""

    def __init__(self, metas: list[dict]):
        self._metas = metas

    def units_metadata(self, **_kw) -> list[dict]:
        return [dict(m) for m in self._metas]


class ExposureWindowProbeTests(unittest.TestCase):
    """P0-close probe: due when a critical/high observation closed after last_verified."""

    CFG = {"index": {"chroma_dir": "/tmp/unused"}, "models": {}}
    ROW = {"id": "exposure-window-tracking", "status": "open", "last_verified": "2026-07-01"}

    def _probe(self, metas: list[dict]) -> tuple[bool, str]:
        with patch("doctor.open_readonly_unit_store", return_value=_FakeUnitStore(metas)):
            return _exposure_window_probe(dict(self.ROW), self.CFG)

    @staticmethod
    def _obs(lid: str, severity: str, ts: str, **extra) -> dict:
        return {"ledger_id": lid, "type": "observation", "severity": severity,
                "timestamp": ts, **extra}

    @staticmethod
    def _verif(lid: str, parent: str, result: str, ts: str) -> dict:
        return {"ledger_id": lid, "ledger_kind": "verification", "relates_to": parent,
                "result": result, "timestamp": ts}

    def test_no_critical_high_not_due(self):
        due, detail = self._probe([self._obs("obs_a", "medium", "2026-07-05T10:00:00")])
        self.assertFalse(due, detail)
        self.assertIn("no closed critical/high", detail)

    def test_critical_closed_after_last_verified_due(self):
        due, detail = self._probe([
            self._obs("obs_p0", "critical", "2026-06-20T10:00:00"),
            self._verif("obs_v1", "obs_p0", "pass", "2026-07-05T10:00:00"),
        ])
        self.assertTrue(due, detail)
        self.assertIn("obs_p0", detail)
        self.assertIn("2026-07-05", detail)

    def test_critical_closed_before_last_verified_not_due(self):
        due, detail = self._probe([
            self._obs("obs_p0", "critical", "2026-06-20T10:00:00"),
            self._verif("obs_v1", "obs_p0", "pass", "2026-06-25T10:00:00"),
        ])
        self.assertFalse(due, detail)
        self.assertIn("clean-scan recorded", detail)

    def test_critical_still_open_not_due(self):
        due, detail = self._probe([self._obs("obs_p0", "critical", "2026-07-05T10:00:00")])
        self.assertFalse(due, detail)
        self.assertIn("no closed critical/high", detail)

    def test_medium_closed_after_last_verified_not_due(self):
        due, detail = self._probe([
            self._obs("obs_m", "medium", "2026-06-20T10:00:00"),
            self._verif("obs_v1", "obs_m", "pass", "2026-07-05T10:00:00"),
        ])
        self.assertFalse(due, detail)
        self.assertIn("no closed critical/high", detail)

    def test_later_note_does_not_refire(self):
        # Close date is the pass-verification timestamp, not last_touched:
        # a non-verification child added after the clean scan must not re-fire.
        due, detail = self._probe([
            self._obs("obs_p0", "high", "2026-06-20T10:00:00"),
            self._verif("obs_v1", "obs_p0", "pass", "2026-06-25T10:00:00"),
            {"ledger_id": "obs_note", "ledger_kind": "note", "relates_to": "obs_p0",
             "timestamp": "2026-07-06T10:00:00"},
        ])
        self.assertFalse(due, detail)
        self.assertIn("clean-scan recorded", detail)


class CharterRegisterConsistencyTests(unittest.TestCase):
    """Probe that keeps docs/role-charters.md register_refs in sync with the register."""

    def _charter(self, tmp: Path, refs_by_role: list[list[str]]) -> None:
        docs = tmp / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        blocks = []
        for i, refs in enumerate(refs_by_role, 1):
            joined = ", ".join(refs)
            blocks.append(f"## Role {i}\n\n```yaml\nregister_refs: [{joined}]\n```\n")
        (docs / "role-charters.md").write_text("\n".join(blocks), encoding="utf-8")

    def _rows(self, *specs: tuple[str, str]) -> list:
        return [{"id": rid, "status": status, "trigger": {"type": "none"}} for rid, status in specs]

    def test_aligned_not_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._charter(tmp, [["a", "b"], ["c"]])
            rows = self._rows(("a", "open"), ("b", "open"), ("c", "open"))
            due, detail = _charter_register_consistency_probe(rows, tmp)
        self.assertFalse(due, detail)

    def test_dangling_ref_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._charter(tmp, [["a", "ghost"]])
            rows = self._rows(("a", "open"))
            due, detail = _charter_register_consistency_probe(rows, tmp)
        self.assertTrue(due)
        self.assertIn("ghost", detail)
        self.assertIn("dangling", detail)

    def test_orphan_open_row_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._charter(tmp, [["a"]])
            rows = self._rows(("a", "open"), ("lonely", "open"))
            due, detail = _charter_register_consistency_probe(rows, tmp)
        self.assertTrue(due)
        self.assertIn("lonely", detail)
        self.assertIn("orphan", detail)

    def test_closed_uncited_row_not_orphan(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._charter(tmp, [["a"]])
            rows = self._rows(("a", "open"), ("retired", "closed"))
            due, detail = _charter_register_consistency_probe(rows, tmp)
        self.assertFalse(due, detail)

    def test_orphan_standing_row_due(self):
        # standing rows exist for the charter<->register traceability link, so a
        # dropped citation must still be caught (unlike closed rows).
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._charter(tmp, [["a"]])
            rows = self._rows(("a", "open"), ("s1", "standing"))
            due, detail = _charter_register_consistency_probe(rows, tmp)
        self.assertTrue(due)
        self.assertIn("s1", detail)
        self.assertIn("orphan", detail)

    def test_cited_standing_row_not_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._charter(tmp, [["a", "s1"]])
            rows = self._rows(("a", "open"), ("s1", "standing"))
            due, detail = _charter_register_consistency_probe(rows, tmp)
        self.assertFalse(due, detail)

    def test_template_placeholder_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            docs = tmp / "docs"
            docs.mkdir(parents=True)
            (docs / "role-charters.md").write_text(
                "```yaml\nregister_refs: [<Layer 2 check IDs owned by this role>]\n```\n"
                "```yaml\nregister_refs: [a]\n```\n",
                encoding="utf-8",
            )
            rows = self._rows(("a", "open"))
            due, detail = _charter_register_consistency_probe(rows, tmp)
        self.assertFalse(due, detail)

    def test_missing_charter_graceful(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            due, detail = _charter_register_consistency_probe(self._rows(("a", "open")), tmp)
        self.assertFalse(due)
        self.assertIn("not found", detail)

    def test_probe_sees_injected_rows_via_check(self):
        """Guards the plumbing change: the probe compares against the loaded
        register (injected), not the repo's shipped one."""
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._charter(tmp, [["a"]])  # charter cites only 'a'
            reg = tmp / "standing-checks-register.json"
            reg.write_text(
                json.dumps(
                    {
                        "checks": [
                            {"id": "a", "status": "open", "trigger": {"type": "none"}},
                            {
                                "id": "charter-register-consistency",
                                "status": "open",
                                "trigger": {"type": "probe", "probe": "charter_register_consistency"},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            c = _check_standing_register(
                {"index": {"chroma_dir": "/tmp/c"}, "models": {}},
                register_path=reg,
                root=tmp,
            )
        # 'charter-register-consistency' is an open row cited by no charter -> orphan -> due (warn).
        self.assertEqual(c.effective_status(), "warn")
        self.assertTrue(c.ok)
        self.assertIn("charter-register-consistency", c.detail)

    def test_shipped_charters_and_register_consistent(self):
        """The real charters + register must be in sync (no dangling/orphan)."""
        import json as _json

        root = Path(__file__).resolve().parent.parent
        rows = _json.loads(
            (root / "docs" / "standing-checks-register.json").read_text(encoding="utf-8")
        )["checks"]
        due, detail = _charter_register_consistency_probe(rows, root)
        self.assertFalse(due, detail)


class MergeOrderProbeTests(unittest.TestCase):
    """Probe asserting CONVMEM-RITUAL.md is first in crush.json global_context_paths."""

    def _row(self, crush_config: Path) -> dict:
        return {
            "id": "merge-order-position",
            "status": "open",
            "trigger": {"type": "probe", "probe": "merge_order_position", "crush_config": str(crush_config)},
        }

    def _crush_json(self, tmp: Path, paths: list) -> Path:
        p = tmp / "crush.json"
        p.write_text(json.dumps({"options": {"global_context_paths": paths}}), encoding="utf-8")
        return p

    def test_ritual_first_not_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cfg = self._crush_json(
                tmp, ["~/.config/crush/CONVMEM-RITUAL.md", "~/.config/crush/CRUSH.md"]
            )
            due, detail = _merge_order_probe(self._row(cfg), tmp)
        self.assertFalse(due, detail)

    def test_ritual_not_first_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cfg = self._crush_json(
                tmp,
                [
                    "/x/rules/builder-reference-ddia.md",
                    "~/.config/crush/CONVMEM-RITUAL.md",
                ],
            )
            due, detail = _merge_order_probe(self._row(cfg), tmp)
        self.assertTrue(due)
        self.assertIn("not first", detail)
        self.assertIn("deploy-builder-reference.sh", detail)

    def test_missing_crush_json_not_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            due, detail = _merge_order_probe(self._row(tmp / "nope.json"), tmp)
        self.assertFalse(due)
        self.assertIn("not found", detail)

    def test_empty_paths_not_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cfg = self._crush_json(tmp, [])
            due, detail = _merge_order_probe(self._row(cfg), tmp)
        self.assertFalse(due, detail)

    def test_crush_md_not_last_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cfg = self._crush_json(
                tmp,
                [
                    "~/.config/crush/CONVMEM-RITUAL.md",
                    "~/.config/crush/CRUSH.md",
                    "/x/rules/builder-reference-ddia.md",
                ],
            )
            due, detail = _merge_order_probe(self._row(cfg), tmp)
        self.assertTrue(due)
        self.assertIn("CRUSH.md not last", detail)

    def test_crush_md_absent_not_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cfg = self._crush_json(
                tmp,
                ["~/.config/crush/CONVMEM-RITUAL.md", "/x/rules/builder-reference-ddia.md"],
            )
            due, detail = _merge_order_probe(self._row(cfg), tmp)
        self.assertFalse(due, detail)

    def test_unreadable_crush_json_due(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            p = tmp / "crush.json"
            p.write_text("{broken", encoding="utf-8")
            due, detail = _merge_order_probe(self._row(p), tmp)
        self.assertTrue(due)
        self.assertIn("unverifiable", detail)


class BranchingDoctorTests(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> None:
        import os
        import subprocess

        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=env
        )

    def test_hooks_path_warns_when_unset(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            self._git(repo, "init", "-b", "main")
            c = _check_hooks_path(root=repo)
        self.assertTrue(c.ok)
        self.assertEqual(c.effective_status(), "warn")
        self.assertIn("unset", c.detail.lower())
        self.assertIn("install-git-hooks", c.detail)

    def test_wip_on_main_warns(self):
        import os
        import subprocess

        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t",
            }
            self._git(repo, "init", "-b", "main")
            (repo / "a.txt").write_text("a\n", encoding="utf-8")
            self._git(repo, "add", "a.txt")
            self._git(repo, "commit", "-m", "chore: init")
            (repo / "b.txt").write_text("b\n", encoding="utf-8")
            self._git(repo, "add", "b.txt")
            subprocess.run(
                ["git", "commit", "-m", "WIP: should warn"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            c = _check_wip_on_main(root=repo)
        self.assertTrue(c.ok)
        self.assertEqual(c.effective_status(), "warn")
        self.assertIn("WIP", c.detail)

    def test_dirty_main_warns(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            self._git(repo, "init", "-b", "main")
            (repo / "a.txt").write_text("a\n", encoding="utf-8")
            self._git(repo, "add", "a.txt")
            self._git(repo, "commit", "-m", "chore: init")
            (repo / "a.txt").write_text("changed\n", encoding="utf-8")
            c = _check_dirty_main(root=repo)
        self.assertTrue(c.ok)
        self.assertEqual(c.effective_status(), "warn")
        self.assertIn("dirty", c.detail.lower())

    def test_unpushed_skips_without_upstream(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            self._git(repo, "init", "-b", "main")
            (repo / "a.txt").write_text("a\n", encoding="utf-8")
            self._git(repo, "add", "a.txt")
            self._git(repo, "commit", "-m", "chore: init")
            self._git(repo, "checkout", "-b", "feat/2026-07-12-z")
            c = _check_unpushed_commits(root=repo)
        self.assertTrue(c.ok)
        self.assertEqual(c.effective_status(), "warn")
        self.assertIn("upstream", c.detail.lower())


if __name__ == "__main__":
    unittest.main()
