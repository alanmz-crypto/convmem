# pylint: disable=wrong-import-position
# Project imports follow the mandatory isolation check.
"""Uncertain/contradictory recovery states never authorize a write."""
from datetime import timedelta
import pytest
from tests._safe_harbor_bootstrap import require_t3_bootstrap
require_t3_bootstrap()
# Register only for this module; each child gets refusal before project imports.
from tests._safe_harbor_t4_pytest import isolated_t4_child_network  # pylint: disable=unused-import
pytest_plugins = ('tests.test_safe_harbor_t2',)
from tests._safe_harbor_t4_harness import expect_probe_ok
from tests.test_safe_harbor_t2 import local_noon, _current, NOW_ENV_KEY

@pytest.mark.parametrize('mode', [
    'tombstone', 'missing_hash', 'invalid_hash', 'false_hash', 'wrong_marker', 'stale_base',
    'duplicate', 'active_and_tombstone', 'wrong_document', 'missing_collection', 'read_error',
    'queue_malformed', 'queue_missing', 'queue_duplicate', 'queue_conflict', 'queue_unsigned',
    'queue_target', 'queue_base', 'queue_hashschema',
    'approved_malformed', 'approved_missing', 'approved_duplicate', 'approved_conflict',
    'events_malformed', 'events_conflict', 'export_conflict', 'export_malformed',
    'cfg_chroma', 'cfg_export', 'cfg_missing', 'unknown_control',
])
def test_recovery_refusals(cli, mode):
    noon = local_noon()
    cli.s.snapshot(noon - timedelta(hours=1))
    result = expect_probe_ok(cli, 'refusal.' + mode, extra_env={**_current(cli), NOW_ENV_KEY: noon.isoformat()})
    assert result['pid']
    if mode != 'unknown_control':
        assert result['refusal']
