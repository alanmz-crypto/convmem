"""T0 baseline and evidence tests for JSONL production canary P1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from incremental_jsonl_canary import assemble_evidence


BASELINE_HASHES = {
    "watch.py": "b72fd6380d48bf4256371f4b3f4f8eda03f2ca7f1dd9c107f4d6db60c05da2e2",
    "ingest.py": "03246a6c104ad9bb6d9c4df9ab9d34bac165080c725ed1545b64aef8f76f6d23",
    "incremental_jsonl.py": "048a895394629f55fa2c2b0af2f00c9844a9038268899a85eadd97c7d4d88cfe",
    "incremental_jsonl_isolation.py": "818325221d46b1501795895b82d2465151b12ab76f0f11f21f42d8438c0a6df1",
}


def test_t0_baseline_hashes_unchanged() -> None:
    root = Path(".")
    for name, expected in BASELINE_HASHES.items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        assert actual == expected, name


def test_p1_a14_evidence_is_reproducible_structure() -> None:
    payload = assemble_evidence(t0={"baseline": BASELINE_HASHES}, hermetic=True)
    assert payload["hermetic"] is True
    assert payload["sections"]["t0"]["baseline"] == BASELINE_HASHES
