"""Stdlib-only child entry; validate isolation before importing task/project modules."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    path = ROOT / 'tests' / '_safe_harbor_t4_common.py'
    spec = importlib.util.spec_from_file_location('t4_common_bootstrap', path)
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    helpers._require_child_isolation()  # pylint: disable=protected-access
    helpers._refuse_outside_fixture(Path(os.environ['CONVMEM_CONFIG']))  # pylint: disable=protected-access
    if not os.environ.get('SAFE_HARBOR_T2_NOW'):
        raise RuntimeError('missing isolated evaluation clock')
    sys.path.insert(0, str(ROOT))
    helpers._install_fakes()  # pylint: disable=protected-access
    try:
        cfg = helpers._load_cfg()  # pylint: disable=protected-access
        case = sys.argv[1]
        group, mode = case.split('.', 1)
        if group == 'matrix':
            payload = getattr(helpers, '_matrix_' + mode)(cfg)
        elif group == 'recover':
            payload = helpers._recover_only(cfg)  # pylint: disable=protected-access
        elif group == 'publication':
            from tests._safe_harbor_t4_publication import run_publication
            payload = run_publication(cfg, mode)
        elif group == 'refusal':
            from tests._safe_harbor_t4_refusal import run_refusal
            payload = run_refusal(cfg, mode)
        elif group == 'terminal':
            from tests._safe_harbor_t4_terminal import run_terminal_case
            payload = run_terminal_case(cfg, mode)
        elif group == 'guard':
            from tests._safe_harbor_t4_order import run_guard_case
            payload = run_guard_case(cfg, mode)
        elif case == 'retry.assume_rollback':
            from tests._safe_harbor_t4_publication import rollback_retry
            payload = rollback_retry(cfg, helpers._resolve_pid(cfg))  # pylint: disable=protected-access
        else:
            raise ValueError('unknown case ' + case)
        return helpers._emit(payload)  # pylint: disable=protected-access
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return helpers._emit({'verdict':'FAIL','error':str(exc),'case':sys.argv[1]},rc=1)  # pylint: disable=protected-access

if __name__ == '__main__':
    raise SystemExit(main())
