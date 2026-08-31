"""Hermetic G5 tests for the synthetic naturalistic evaluation dry-run."""

# pylint: disable=wrong-import-position

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.analysis_fixtures import G4_SYNTHETIC_FIXTURE_SEED
from eval_naturalistic.dry_run import (
    G5_CLASSIFICATION,
    G5_REQUIRED_FAIL_CLOSED_SCENARIOS,
    run_g4_safe_synthetic_example,
    run_g5_dry_run,
    run_g5_end_to_end,
)
from eval_naturalistic.dry_run_mechanics import (
    SYNTHETIC_ORDINARY_TOOLS,
    make_symmetric_condition_packages,
    qualify_c0_c1_environment,
)
from eval_naturalistic.enums import StudyTerminalDisposition
from eval_naturalistic.fixtures import make_synthetic_evidence, make_synthetic_episode, make_synthetic_frame


REQUIRED_FAIL_CLOSED = G5_REQUIRED_FAIL_CLOSED_SCENARIOS

REQUIRED_PRESERVE = {
    "g4_safe_synthetic_example",
    "g5_end_to_end_happy_path",
    "capture_dependent_target_exclusion",
    "all_zero_window",
}

PRODUCT_DISPOSITIONS = {
    StudyTerminalDisposition.COMPLETE_POSITIVE.value,
    StudyTerminalDisposition.COMPLETE_NEGATIVE.value,
    StudyTerminalDisposition.COMPLETE_NULL_EQUIVALENT.value,
}


class G4SafeExampleTests(unittest.TestCase):
    def test_existing_g4_fixture_semantics(self):
        result = run_g4_safe_synthetic_example()
        self.assertTrue(result["aggregation_ok"])
        self.assertEqual(result["conditional_effect"], 0.3)
        self.assertEqual(result["paired_episodes"], 2)
        self.assertEqual(result["disposition"], "blocked_non_estimable")
        self.assertFalse(result["all_slots_frozen"])
        self.assertTrue(result["not_evidence_that_convmem_helps"])
        self.assertEqual(result["classification"], G5_CLASSIFICATION)


class G5EndToEndTests(unittest.TestCase):
    def test_favorable_synthetic_effect_is_not_product_evidence(self):
        result = run_g5_end_to_end()
        self.assertTrue(result["aggregation_ok"], result["errors"])
        self.assertEqual(result["conditional_effect"], 0.3)
        self.assertEqual(result["paired_episodes"], 2)
        self.assertEqual(result["zero_target_episode_count"], 1)
        self.assertEqual(result["opportunity_episode_count"], 3)
        self.assertEqual(result["disposition"], "blocked_non_estimable")
        self.assertFalse(result["all_slots_frozen"])
        self.assertIsNone(result["scorer_reliability_passes"])
        self.assertTrue(result["synthetic_only"])
        self.assertTrue(result["not_evidence_that_convmem_helps"])
        self.assertNotIn(result["disposition"], PRODUCT_DISPOSITIONS)

    def test_stage_gates_all_pass_mechanically(self):
        result = run_g5_end_to_end()
        self.assertEqual(
            result["stage_ok"],
            {"T0_T2": True, "T3_T5": True, "T6_T7": True, "T8_T10": True},
        )


class G5AdversarialSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_g5_dry_run()
        cls.by_id = {scenario.scenario_id: scenario for scenario in cls.report.scenarios}

    def test_every_required_scenario_is_demonstrated(self):
        missing = (REQUIRED_FAIL_CLOSED | REQUIRED_PRESERVE) - set(self.by_id)
        self.assertFalse(missing, missing)
        for scenario_id in REQUIRED_FAIL_CLOSED | REQUIRED_PRESERVE:
            self.assertTrue(self.by_id[scenario_id].demonstrated, scenario_id)

    def test_required_fail_closed_cases_reject(self):
        for scenario_id in REQUIRED_FAIL_CLOSED:
            scenario = self.by_id[scenario_id]
            self.assertTrue(scenario.fail_closed, scenario_id)
            self.assertTrue(scenario.demonstrated, scenario_id)

    def test_zero_targets_remain_in_opportunity_denominator(self):
        happy = self.report.happy_path
        self.assertEqual(happy["zero_target_episode_count"], 1)
        self.assertEqual(happy["opportunity_episode_count"], 3)
        self.assertTrue(self.by_id["missing_zero_target_episode"].demonstrated)
        self.assertTrue(self.by_id["all_zero_window"].demonstrated)

    def test_no_product_disposition_or_g6_authority(self):
        self.assertFalse(self.report.product_disposition_emitted)
        self.assertFalse(self.report.g6_authority_assumed)
        self.assertFalse(self.report.naturalistic_evidence_created)
        self.assertTrue(self.report.synthetic_only)
        self.assertEqual(self.report.fixture_seed, G4_SYNTHETIC_FIXTURE_SEED)
        self.assertEqual(self.report.classification, G5_CLASSIFICATION)
        self.assertTrue(self.report.all_required_fail_closed_demonstrated)
        for scenario in self.report.scenarios:
            disposition = scenario.details.get("disposition")
            if disposition:
                self.assertNotIn(disposition, PRODUCT_DISPOSITIONS, scenario.scenario_id)

    def test_report_is_json_serializable(self):
        payload = json.dumps(self.report.to_dict())
        self.assertIn(G5_CLASSIFICATION, payload)
        self.assertIn("blocked_non_estimable", payload)


class G5MechanicsAndIsolationTests(unittest.TestCase):
    def test_symmetric_packages_qualify(self):
        c0, c1 = make_symmetric_condition_packages()
        self.assertEqual(c0.tools, SYNTHETIC_ORDINARY_TOOLS)
        self.assertTrue(qualify_c0_c1_environment(c0, c1).ok)

    def test_fixtures_remain_synthetic_only(self):
        evidence = make_synthetic_evidence(episode=make_synthetic_episode(frame=make_synthetic_frame()))
        for source in evidence.sources:
            self.assertTrue(source.locator.startswith("synthetic://"))

    def test_no_live_study_modules_imported_by_g5(self):
        import eval_naturalistic.dry_run as dry_run_mod

        source = Path(dry_run_mod.__file__).read_text(encoding="utf-8")
        forbidden = (
            "run_agent_a",
            "run_agent_b",
            "execute_trial",
            "chromadb",
            "eval_corpus",
            "mcp_server",
            "~/.local/share/convmem/",
        )
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
