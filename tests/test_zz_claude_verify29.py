"""Claude verify probes, round 29 (corrective 22): recovery embeds outside C1 and survives a provider outage."""
import json
import sys
from pathlib import Path

import pytest

from tests._safe_harbor_t4_pytest import isolated_t4_child_network  # noqa: F401  (fixture)
from tests.test_safe_harbor_t2 import cli, isolated, scratch  # noqa: F401  (fixtures)
from tests.test_safe_harbor_t4_matrix import _matrix_env
from tests._safe_harbor_t4_harness import probe_env, run_fixture_child


@pytest.mark.parametrize('case', ['create_absence_down_then_up', 'event_only_down', 'marker_repair_down'])
def test_recovery_provider_outage(cli, case):  # noqa: F811
    env = probe_env(cli, case=case, extra=_matrix_env(cli))
    probe = Path(__file__).with_name('_c22_recovery_outage_probe.py')
    proc = run_fixture_child([sys.executable, '-s', '-B', str(probe), case], env=env, timeout=300)
    assert proc.stdout.strip(), (proc.returncode, proc.stderr[-3000:])
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    print('OUTAGE_RECOVERY:', json.dumps(payload, sort_keys=True))
    assert proc.returncode == 0, payload
    assert payload['verdict'] == 'PASS', payload
