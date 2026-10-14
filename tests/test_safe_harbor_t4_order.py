# pylint: disable=wrong-import-position
# Project imports follow the mandatory isolation check.
"""Real native maintenance happens before any recovery completion effects."""
from datetime import timedelta
import pytest
from tests._safe_harbor_bootstrap import require_t3_bootstrap
require_t3_bootstrap()
# Register only for this module; each child gets refusal before project imports.
from tests._safe_harbor_t4_pytest import isolated_t4_child_network  # pylint: disable=unused-import
pytest_plugins=('tests.test_safe_harbor_t2',)
from tests._safe_harbor_t4_harness import expect_probe_ok
from tests.test_safe_harbor_t2 import local_noon, _current, NOW_ENV_KEY

@pytest.mark.parametrize('mode',['order','after_failure'])
def test_native_validation_publication_order(cli,mode):
    noon=local_noon()
    cli.s.snapshot(noon-timedelta(hours=1))
    result=expect_probe_ok(cli,'guard.'+mode,extra_env={**_current(cli),NOW_ENV_KEY:noon.isoformat()})
    assert result['calls']
