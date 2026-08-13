from datetime import date

from doctor import _check_arc_staleness


def _status(completion: str, update: str = "2026-08-01") -> str:
    return f"""# Arc

## 4. Completion State

| # | Milestone | Status | Blocking on |
|---|-----------|--------|-------------|
| T1 | Work | {completion} | — |

## Update Log

| Date | Who | Change |
|------|-----|--------|
| {update} | Ryan | checkpoint |
"""


def test_stale_incomplete_arc_warns(tmp_path):
    (tmp_path / "docs/plans").mkdir(parents=True)
    (tmp_path / "docs/plans/STATUS-forgotten.md").write_text(_status("**NOT STARTED**"))

    check = _check_arc_staleness(root=tmp_path, today=date(2026, 8, 20))

    assert check.ok is True
    assert check.status == "warn"
    assert "forgotten" in check.detail
    assert "1 incomplete" in check.detail


def test_completed_arc_is_not_stale(tmp_path):
    (tmp_path / "docs/plans").mkdir(parents=True)
    (tmp_path / "docs/plans/STATUS-done.md").write_text(_status("**DONE**"))

    check = _check_arc_staleness(root=tmp_path, today=date(2026, 8, 20))

    assert check.status == ""
    assert "0 stale" in check.detail


def test_fresh_arc_is_not_stale(tmp_path):
    (tmp_path / "docs/plans").mkdir(parents=True)
    (tmp_path / "docs/plans/STATUS-fresh.md").write_text(
        _status("**NOT READY**", update="2026-08-10")
    )

    check = _check_arc_staleness(root=tmp_path, today=date(2026, 8, 20))

    assert check.status == ""
    assert "0 stale" in check.detail


def test_missing_status_files_skip(tmp_path):
    (tmp_path / "docs/plans").mkdir(parents=True)

    check = _check_arc_staleness(root=tmp_path, today=date(2026, 8, 20))

    assert check.status == "skip"
    assert "no STATUS files" in check.detail


def test_missing_update_date_is_stale(tmp_path):
    (tmp_path / "docs/plans").mkdir(parents=True)
    text = _status("**BLOCKED**").replace("| 2026-08-01 | Ryan | checkpoint |", "| — | Ryan | checkpoint |")
    (tmp_path / "docs/plans/STATUS-malformed.md").write_text(text)

    check = _check_arc_staleness(root=tmp_path, today=date(2026, 8, 20))

    assert check.status == "warn"
    assert "last: unknown" in check.detail


def test_mixed_arcs_only_stale_arc_is_reported(tmp_path):
    (tmp_path / "docs/plans").mkdir(parents=True)
    (tmp_path / "docs/plans/STATUS-old.md").write_text(_status("NOT DONE"))
    (tmp_path / "docs/plans/STATUS-new.md").write_text(
        _status("NOT DONE", update="2026-08-10")
    )

    check = _check_arc_staleness(root=tmp_path, today=date(2026, 8, 20))

    assert check.status == "warn"
    assert "old" in check.detail
    assert "new" not in check.detail
