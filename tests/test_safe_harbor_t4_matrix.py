# pylint: disable=wrong-import-position
# Project imports follow the mandatory isolation check.
# pylint: disable=redefined-outer-name
"""T4 success matrix via isolated probe child (real CLI/admission/recovery)."""

from __future__ import annotations

import pytest

from tests._safe_harbor_bootstrap import require_t3_bootstrap

require_t3_bootstrap()
# Register only for this module; each child gets refusal before project imports.
from tests._safe_harbor_t4_pytest import isolated_t4_child_network  # pylint: disable=unused-import
from tests.test_safe_harbor_t2 import cli, isolated, scratch  # pylint: disable=unused-import

from tests._safe_harbor_t4_harness import expect_probe_ok  # noqa: E402
from tests.test_safe_harbor_t2 import NOW_ENV_KEY, _current, local_noon  # noqa: E402


def _matrix_env(cli):
    noon = local_noon()
    cli.s.snapshot(noon - __import__("datetime").timedelta(hours=1))
    return {**_current(cli), NOW_ENV_KEY: noon.isoformat()}


@pytest.mark.parametrize(
    "case",
    [
        "matrix.create_absence",
        "matrix.event_only",
        "matrix.marker_repair",
        "matrix.base_retry",
        "matrix.cli_recover",
        "matrix.cli_record",
        "matrix.unbound_helper",
        "matrix.warm_same_process",
        "matrix.fresh_process_retry",
    ],
)
def test_t4_matrix_success_paths(cli, case: str):
    payload = expect_probe_ok(cli, case, extra_env=_matrix_env(cli))
    assert payload.get("pid")
    if case == "matrix.create_absence":
        assert payload["chroma_id"] == payload["export_id"]
        assert payload["action"] == "retry_chroma"
    if case == "matrix.fresh_process_retry":
        pids = payload.get("child_probe_pids") or []
        assert len(pids) == 2 and pids[0] != pids[1]
    if case == "matrix.base_retry":
        assert payload["action"] == "retry_chroma", payload


def test_t4_classify_conflicting_marker_is_review():
    from propose_decision import classify_recovery_action

    assert (
        classify_recovery_action(
            proposal_id="p1",
            intent_present=True,
            proposed_hash="a" * 64,
            live_marker="other",
            live_hash="a" * 64,
            live_absent=False,
            live_read_failed=False,
            base_hash="",
        )
        == "review"
    )


def test_t4_live_absent_create_allows_retry_without_base():
    from propose_decision import classify_recovery_action

    assert (
        classify_recovery_action(
            proposal_id="p1",
            intent_present=True,
            proposed_hash="a" * 64,
            live_marker="",
            live_hash="",
            live_absent=True,
            live_read_failed=False,
            base_hash="",
        )
        == "retry_chroma"
    )
