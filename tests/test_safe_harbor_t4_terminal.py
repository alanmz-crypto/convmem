# pylint: disable=wrong-import-position,redefined-outer-name
"""Terminal recovery lifecycle evidence (probe child, fixture-confined)."""

from __future__ import annotations

from datetime import timedelta
import pytest

from tests._safe_harbor_bootstrap import require_t3_bootstrap

require_t3_bootstrap()

pytest_plugins = ("tests.test_safe_harbor_t2",)

from tests._safe_harbor_t4_harness import expect_probe_ok  # noqa: E402
from tests.test_safe_harbor_t2 import NOW_ENV_KEY, _current, local_noon  # noqa: E402


def _terminal_env(cli):
    noon = local_noon()
    cli.s.snapshot(noon - timedelta(hours=1))
    return {**_current(cli), NOW_ENV_KEY: noon.isoformat()}


@pytest.mark.parametrize(
    "mode",
    [
        "missing_export",
        "terminal_tombstone",
        "terminal_absent",
        "cli_uncertain",
        "active_conflict",
    ],
)
def test_t4_terminal_lifecycle(cli, mode: str):
    payload = expect_probe_ok(cli, f"terminal.{mode}", extra_env=_terminal_env(cli))
    assert payload.get("pid")
    assert payload.get("mode") == mode
