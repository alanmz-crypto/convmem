"""Bounded installed-interpreter checks; enter with python -I -S -B."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INTERPRETER_CASES = [
    'tests/test_safe_harbor_t3_backend_proof.py',
    'tests/test_safe_harbor_t3.py',
    'tests/test_safe_harbor_t3_matrix.py',
    'tests/test_safe_harbor_t4_publication.py',
    'tests/test_safe_harbor_t4_durability.py',
    'tests/test_governed_recovery_matrix_admitted.py',
    'tests/test_safe_harbor_t2.py::test_cli_add_succeeds_with_unchanged_chroma_alias',
    'tests/test_safe_harbor_t2.py::test_cli_chroma_alias_retarget_refused_after_preflight',
    'tests/test_safe_harbor_t2.py::test_control_unbound_target_lets_alias_retarget_mutate',
    'tests/test_safe_harbor_t2.py::test_cli_export_alias_retarget_refused_after_store_open',
    'tests/test_safe_harbor_t4_concurrency_real.py::test_t4_real_recovery_holds_lock_forget_cannot_acquire',
    'tests/test_safe_harbor_t4_concurrency_real.py::test_t4_real_recovery_holds_lock_refine_cannot_acquire',
    'tests/test_safe_harbor_t4_concurrency_real.py::test_t4_real_forget_before_recovery_refuses',
    'tests/test_safe_harbor_t4_concurrency_real.py::test_t4_real_refine_before_recovery_refuses',
    'tests/test_safe_harbor_t4_concurrency_real.py::test_t4_faulty_out_of_lock_recheck_negative_control',
    'tests/test_safe_harbor_t4_concurrency_real.py::test_t4_rechecks_config_after_native_lock_wait',
]
IDENTITY_CODE = '''
import hashlib, importlib.metadata as md, json, pathlib, sys
assert getattr(sys, '_safe_harbor_t4_network_refused', False)
from tests._safe_harbor_bootstrap import require_t3_bootstrap
require_t3_bootstrap()
packages = {name: md.version(name) for name in ('chromadb','hnswlib','numpy','pytest')}
binaries = {}
for name in ('chromadb','hnswlib'):
    dist = md.distribution(name)
    for item in dist.files or []:
        if str(item).endswith('.so') and ('bindings' in str(item) or 'hnswlib' in str(item)):
            p = pathlib.Path(dist.locate_file(item))
            binaries[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps({'python':sys.version,'executable':sys.executable,
                  'packages':packages,'binaries':binaries},sort_keys=True))
'''


def _source_hashes():
    listed = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT,
    )
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in sorted(set(listed.decode().split('\0'))) if name and (ROOT / name).is_file()}


def main():
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise RuntimeError('entry requires -I -S -B before imports')
    if len(sys.argv) != 2 or sys.argv[1] not in {'interpreter', 'legacy'}:
        raise RuntimeError('select interpreter or legacy')
    spec = importlib.util.spec_from_file_location('bootstrap', ROOT / 'tests/_safe_harbor_bootstrap.py')
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    uid = bootstrap.parent_launcher_uid()
    backend = bootstrap.load_stdlib_module(
        ROOT / 'tests/_safe_harbor_t3_backend_worker.py', 'backend',
    )
    # Uses the existing checksum/version verifier; no fetch or dependency install.
    os.environ['SAFE_HARBOR_CI_RESTIC_EXECUTABLE'] = '/tmp/safe-harbor-restic-tool/restic'
    evidence = Path(tempfile.mkdtemp(prefix='safe-harbor-rollout-', dir='/tmp'))
    fixture = evidence / 'fixture'
    fixture.mkdir()
    meta = {}
    env = backend.build_allowlisted_env(
        fixture, evidence, expected_uid=uid, profile='full_ci', fixture_meta=meta,
    )
    hook = fixture / 'network-hook'
    hook.mkdir()
    (hook / 'sitecustomize.py').write_bytes((ROOT / 'tests/_safe_harbor_t4_network.py').read_bytes())
    env['SAFE_HARBOR_T4_NETWORK_LOG'] = str(fixture / 'network-refusals.jsonl')
    env['PYTHONPATH'] = str(hook) + os.pathsep + str(ROOT)
    before = _source_hashes()
    identity = subprocess.run(
        [sys.executable, '-s', '-B', '-c', IDENTITY_CODE], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=30, check=True,
    )
    (evidence / 'identity.json').write_text(identity.stdout, encoding='utf-8')
    selected = INTERPRETER_CASES if sys.argv[1] == 'interpreter' else ['tests/test_safe_harbor_rollout_legacy.py']
    command = [sys.executable, '-s', '-B', '-m', 'pytest', *selected,
               '-v', '-ra', '--tb=short', '-p', 'no:cacheprovider',
               '--junitxml=' + str(evidence / 'junit.xml'),
               '--basetemp=' + str(fixture / 'pytest-tmp')]
    print(json.dumps({'evidence': str(evidence), 'mode': sys.argv[1], 'command': command}), flush=True)
    started = time.monotonic()
    with (evidence / 'run.log').open('w', encoding='utf-8') as log:
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=1200, check=False)
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            returncode = 124
    after = _source_hashes()
    network = []
    # T4 fixtures may install their own hook logs below this fixture.
    for path in fixture.rglob('*network*.jsonl'):
        network.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    unexpected = [row for row in network if row != {
        'event': 'socket.getaddrinfo', 'destination': 'safe-harbor-canary.invalid',
    }]
    counts = {}
    junit = evidence / 'junit.xml'
    if junit.is_file():
        suites = ET.parse(junit).getroot().iter('testsuite')
        for suite in suites:
            for key in ('tests', 'failures', 'errors', 'skipped'):
                counts[key] = counts.get(key, 0) + int(suite.get(key, '0'))
    passed = (returncode == 0 and before == after and not unexpected
              and counts.get('tests', 0) > 0
              and all(counts.get(k, 0) == 0 for k in ('failures', 'errors', 'skipped')))
    summary = {
        'mode': sys.argv[1], 'source_revision': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'runtime_candidate': 'c6f07241ccf1a71d9d874fee963a37b04091b3ce',
        'command': command, 'identity': json.loads(identity.stdout), 'fixture_meta': meta,
        'uid': uid, 'returncode': returncode, 'seconds': time.monotonic() - started,
        'junit': counts, 'source_hashes_before': before, 'source_hashes_after': after,
        'network_refusals': network, 'unexpected_network_refusals': unexpected,
        'passed': passed,
    }
    (evidence / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'evidence': str(evidence), 'passed': passed, 'junit': counts,
                      'returncode': returncode, 'source_unchanged': before == after}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

# ref: ../docs/plans/EXECUTION-safe-harbor.md — section 20 evidence-only grant
# src: ./_safe_harbor_bootstrap.py, ./_safe_harbor_t3_backend_worker.py, ./_safe_harbor_t4_network.py
