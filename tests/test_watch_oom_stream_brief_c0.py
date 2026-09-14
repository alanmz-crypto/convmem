"""C0: freeze current brief semantics on a deterministic Chroma fixture."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from brief import gather_brief_data, gather_brief_payload, render_brief_markdown
from tests.watch_oom_brief_hermetic import (
    EQUAL_TS_DECISION_ORDER,
    EXPECTED_DECISION_IDS,
    EXPECTED_MONITOR_TITLES,
    EXPECTED_UNRESOLVED_COUNT,
    freeze_brief_probes,
    normalize_brief_payload,
    write_c0_fixture,
)

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "watch-oom-stream-brief"
GOLDEN_PAYLOAD = GOLDEN_DIR / "c0-payload.json"
GOLDEN_RENDER = GOLDEN_DIR / "c0-render.md"


def _chroma_core(data: dict) -> dict:
    norm = normalize_brief_payload(data)
    return {
        "units": norm["units"],
        "summaries": norm["summaries"],
        "unresolved_count": norm["unresolved_count"],
        "recent_decisions_norm": norm["recent_decisions_norm"],
        "recent_monitor_norm": norm["recent_monitor_norm"],
        "projects_norm": norm["projects_norm"],
        "rerank": norm["rerank"],
        "generated_at": norm["generated_at"],
    }


def _normalize_render(text: str, tmp_root: Path) -> str:
    import brief as brief_mod

    repo = Path(brief_mod.__file__).resolve().parent
    text = (
        text.replace(str(tmp_root), "TMP")
        .replace(str(repo), "REPO")
        .replace(str(Path.home()), "HOME")
    )
    kept = []
    for line in text.splitlines(keepends=True):
        if line.startswith("  - repo:") or line.startswith("  - agents:"):
            continue
        kept.append(line)
    return "".join(kept)


class C0BriefOracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(self.id().replace(".", "_"))
        # Unique temp dir per test via TemporaryDirectory in each method.

    def _gather(self, tmp: Path) -> dict:
        fx = write_c0_fixture(tmp)
        with freeze_brief_probes():
            return gather_brief_data(fx["cfg"])

    def test_recent_decisions_are_five_newest_with_id_ascending_tiebreak(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            data = self._gather(Path(td))
        lids = [row.get("ledger_id") for row in data["recent_decisions"]]
        self.assertEqual(tuple(lids), EXPECTED_DECISION_IDS)
        equal = [
            row["ledger_id"]
            for row in data["recent_decisions"]
            if row.get("timestamp") == "2026-09-13T16:00:00Z"
        ]
        self.assertEqual(tuple(equal), EQUAL_TS_DECISION_ORDER)
        self.assertTrue(data["recent_decisions"][0].get("superseded") is True)

    def test_recent_monitor_is_three_newest_tool_rows(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            data = self._gather(Path(td))
        titles = [row.get("title") for row in data["recent_monitor"]]
        self.assertEqual(tuple(titles), EXPECTED_MONITOR_TITLES)

    def test_unresolved_count_uses_store_supersession_not_deleted(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            data = self._gather(Path(td))
        self.assertEqual(data["unresolved_count"], EXPECTED_UNRESOLVED_COUNT)

    def test_payload_and_render_match_golden_oracle(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fx = write_c0_fixture(tmp)
            with freeze_brief_probes():
                data = gather_brief_data(fx["cfg"])
                payload = gather_brief_payload(fx["cfg"])
                rendered = _normalize_render(render_brief_markdown(data), tmp)
        core = _chroma_core(data)
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        self.assertTrue(GOLDEN_PAYLOAD.is_file(), "missing C0 payload oracle")
        self.assertTrue(GOLDEN_RENDER.is_file(), "missing C0 render oracle")
        expected = json.loads(GOLDEN_PAYLOAD.read_text(encoding="utf-8"))
        self.assertEqual(core, expected)
        expected_render = GOLDEN_RENDER.read_text(encoding="utf-8")
        self.assertEqual(rendered, expected_render)
        self.assertIn("Equal-ts decision A", rendered)
        self.assertIn("tie-break A", rendered)
        self.assertNotIn("Dropped sixth decision", rendered)
        self.assertNotIn("Dropped monitor hit", rendered)
        self.assertIn("rationale", json.dumps(payload["recent_decisions"]))


if __name__ == "__main__":
    unittest.main()
