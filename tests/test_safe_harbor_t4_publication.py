# pylint: disable=wrong-import-position
# Project imports follow the mandatory isolation check.
"""Real recovery append/export failures and fresh-process reconciliation."""
from datetime import timedelta
import pytest
from tests._safe_harbor_bootstrap import require_t3_bootstrap
require_t3_bootstrap()
pytest_plugins = ('tests.test_safe_harbor_t2',)
from tests._safe_harbor_t4_harness import expect_probe_ok
from tests.test_safe_harbor_t2 import local_noon, _current, NOW_ENV_KEY

@pytest.mark.parametrize('mode', [
    'before', 'partial', 'file_fsync', 'dir_fsync', 'lost_return', 'export', 'rollback_control',
])
def test_publication_restarts(cli, mode):
    noon = local_noon()
    cli.s.snapshot(noon - timedelta(hours=1))
    env = {**_current(cli), NOW_ENV_KEY: noon.isoformat()}
    payload = expect_probe_ok(cli, 'publication.' + mode, extra_env=env)
    assert payload['fault_hits']
    assert 'unknown' in payload['first_outcome']
