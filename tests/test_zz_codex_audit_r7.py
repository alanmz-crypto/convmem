"""Recovery must reach a fake HTTP transport through the real embedding gate."""
import json
import sys
from pathlib import Path
import pytest
from tests._safe_harbor_t4_pytest import isolated_t4_child_network  # pylint: disable=unused-import,duplicate-code
from tests.test_safe_harbor_t2 import cli, isolated, scratch  # pylint: disable=unused-import
from tests.test_safe_harbor_t4_matrix import _matrix_env
from tests._safe_harbor_t4_harness import probe_env, run_fixture_child

@pytest.mark.parametrize('case', ['create_absence', 'base_retry', 'event_only', 'marker_repair'])
def test_recovery_with_real_embed_gate(cli, case):  # pylint: disable=redefined-outer-name
    env = probe_env(cli, case=case, extra=_matrix_env(cli))
    probe = Path(__file__).with_name('_r7_recovery_probe.py')
    proc = run_fixture_child([sys.executable,'-s','-B',str(probe),case],env=env,timeout=300)
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    print('REAL_EMBED_RECOVERY:',json.dumps(payload,sort_keys=True))
    assert proc.returncode == 0, payload
    assert payload['verdict'] == 'PASS', payload

# src: ./_r7_recovery_probe.py — real embedding gate with fake HTTP transport
