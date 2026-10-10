"""Pure fail-closed checks for the gated cgroup service boundary."""

from pathlib import Path

import pytest

from tests.watch_oom_cgroup_runner import MEMORY_LIMIT_BYTES, worker_limit_claim


def _fake_membership(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "cgroup"
    parent = root / "user.slice"
    group = parent / "measurement.service"
    group.mkdir(parents=True)
    for location in (root, parent):
        (location / "memory.max").write_text("max\n", encoding="ascii")
        (location / "memory.swap.max").write_text("max\n", encoding="ascii")
    (group / "memory.max").write_text(f"{MEMORY_LIMIT_BYTES}\n", encoding="ascii")
    (group / "memory.swap.max").write_text("0\n", encoding="ascii")
    membership = tmp_path / "self.cgroup"
    membership.write_text("0::/user.slice/measurement.service\n", encoding="ascii")
    return root, parent, membership


def test_worker_claim_requires_own_effective_cap(tmp_path: Path) -> None:
    root, parent, membership = _fake_membership(tmp_path)
    claim = worker_limit_claim(
        MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root
    )
    assert claim["memory_max_bytes"] == MEMORY_LIMIT_BYTES
    assert claim["memory_swap_max_bytes"] == 0

    (parent / "memory.max").write_text(f"{MEMORY_LIMIT_BYTES // 2}\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="differs from the reviewed cap"):
        worker_limit_claim(MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root)


def test_worker_claim_rejects_unbounded_or_swapping_service(tmp_path: Path) -> None:
    root, _parent, membership = _fake_membership(tmp_path)
    group = root / "user.slice" / "measurement.service"
    (group / "memory.max").write_text("max\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="differs from the reviewed cap"):
        worker_limit_claim(MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root)

    (group / "memory.max").write_text(f"{MEMORY_LIMIT_BYTES}\n", encoding="ascii")
    (group / "memory.swap.max").write_text("max\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="differs from the reviewed cap"):
        worker_limit_claim(MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root)


def test_worker_claim_rejects_ambiguous_membership(tmp_path: Path) -> None:
    root, _parent, membership = _fake_membership(tmp_path)
    membership.write_text("0::/user.slice/measurement.service\n0::/other\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="unambiguous"):
        worker_limit_claim(MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root)
