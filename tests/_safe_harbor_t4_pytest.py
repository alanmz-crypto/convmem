"""T4-only child network refusal; does not alter unrelated full-suite tests."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import pytest


@pytest.fixture(autouse=True)
def isolated_t4_child_network(tmp_path, monkeypatch):
    """Use the outer T4 hook or install one before any fixture child starts."""
    from tests._safe_harbor_bootstrap import require_t3_bootstrap
    require_t3_bootstrap()
    if getattr(sys, "_safe_harbor_t4_network_refused", False):
        # The dedicated launcher already installs and checks this hook globally.
        yield
        return
    fixture = Path(os.environ["SAFE_HARBOR_T3_FIXTURE_ROOT"]).resolve(strict=True)
    assert fixture in tmp_path.resolve(strict=True).parents
    hook = tmp_path / "t4-network-hook"
    hook.mkdir()
    root = Path(__file__).resolve().parents[1]
    (hook / "sitecustomize.py").write_bytes((root / "tests/_safe_harbor_t4_network.py").read_bytes())
    log = tmp_path / "network-refusals.jsonl"
    monkeypatch.setenv("SAFE_HARBOR_T4_NETWORK_LOG", str(log))
    monkeypatch.setenv("PYTHONPATH", str(hook) + os.pathsep + str(root))
    yield
    attempts = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    expected = {"event": "socket.getaddrinfo", "destination": "safe-harbor-canary.invalid"}
    assert all(row == expected for row in attempts), f"unexpected T4 child network attempts: {attempts}"
