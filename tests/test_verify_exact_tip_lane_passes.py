"""Unit tests for exact-tip lane PASS and closeout readiness helpers."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_exact_tip_lane_passes import (  # noqa: E402
    EvidenceItem,
    classify_lane,
    is_edited,
    latest_lane_verdict,
    verdict_of,
    verify_exact_tip_lane_passes,
    whole_token_sha_present,
)
from verify_pr_closeout_readiness import (  # noqa: E402
    PR52_CLOSEOUT_ALLOWLIST,
    check_body,
    verify_closeout_readiness,
)

SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
BASE = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
OTHER = "cccccccccccccccccccccccccccccccccccccccc"


def _item(
    *,
    body: str,
    author: str = "alanmz-crypto",
    kind: str = "issue_comment",
    item_id: int = 1,
    created_at: str = "2026-07-20T10:00:00Z",
    updated_at: str | None = None,
    url: str = "https://example.test/1",
) -> EvidenceItem:
    return EvidenceItem(
        kind=kind,
        item_id=item_id,
        author=author,
        body=body,
        created_at=created_at,
        updated_at=created_at if updated_at is None else updated_at,
        url=url,
    )


def _canonical(lane: str, verdict: str, sha: str) -> str:
    return (
        f"Lane: {lane}\n"
        f"Verdict: {verdict}\n"
        f"Reviewed head: {sha}\n"
    )


class ExactTipHelpersTests(unittest.TestCase):
    def test_whole_token_rejects_longer_hash_substring(self):
        longer = SHA + "dead"
        self.assertFalse(whole_token_sha_present(longer, SHA))
        self.assertTrue(whole_token_sha_present(f"head {SHA} ok", SHA))

    def test_classify_lane(self):
        self.assertEqual(
            classify_lane("Lane: GitHub Copilot audit lane\n"), "copilot"
        )
        self.assertEqual(classify_lane("Lane: Kiro\n"), "kiro")
        self.assertIsNone(
            classify_lane("Lane: GitHub Copilot audit lane\nLane: Kiro\n")
        )

    def test_verdict_rejects_mixed_pass_fail_lines(self):
        body = "Verdict: PASS\nVerdict: FAIL\n"
        self.assertIsNone(verdict_of(body))

    def test_edited_comment_rejected(self):
        item = _item(
            body=_canonical("Kiro", "PASS", SHA),
            updated_at="2026-07-20T11:00:00Z",
        )
        self.assertTrue(is_edited(item))
        ok, msgs = verify_exact_tip_lane_passes([item], sha=SHA)
        self.assertFalse(ok)
        self.assertTrue(any("no qualifying" in m for m in msgs))

    def test_latest_pass_wins_then_later_fail_blocks(self):
        items = [
            _item(
                body=_canonical("Kiro", "PASS", SHA),
                item_id=1,
                created_at="2026-07-20T10:00:00Z",
            ),
            _item(
                body=_canonical("Kiro", "FAIL", SHA),
                item_id=2,
                created_at="2026-07-20T11:00:00Z",
            ),
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS", SHA),
                item_id=3,
                created_at="2026-07-20T10:30:00Z",
            ),
        ]
        latest = latest_lane_verdict(items, sha=SHA, lane="kiro")
        assert latest is not None
        self.assertEqual(latest[1], "FAIL")
        ok, _ = verify_exact_tip_lane_passes(items, sha=SHA)
        self.assertFalse(ok)

    def test_both_lanes_pass(self):
        items = [
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS", SHA),
                item_id=10,
            ),
            _item(
                body=_canonical("Kiro", "PASS", SHA),
                item_id=11,
                created_at="2026-07-20T10:01:00Z",
            ),
        ]
        ok, msgs = verify_exact_tip_lane_passes(items, sha=SHA)
        self.assertTrue(ok, msgs)
        self.assertEqual(sum(1 for m in msgs if m.startswith("PASS ")), 2)

    def test_wrong_author_ignored(self):
        items = [
            _item(
                body=_canonical("Kiro", "PASS", SHA),
                author="someone-else",
            ),
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS", SHA),
            ),
        ]
        ok, _ = verify_exact_tip_lane_passes(items, sha=SHA)
        self.assertFalse(ok)

    def test_sha_mismatch_ignored(self):
        items = [
            _item(body=_canonical("Kiro", "PASS", OTHER)),
            _item(body=_canonical("GitHub Copilot audit lane", "PASS", SHA)),
        ]
        ok, _ = verify_exact_tip_lane_passes(items, sha=SHA)
        self.assertFalse(ok)


class CloseoutReadinessTests(unittest.TestCase):
    def _clean_view(self, **overrides) -> dict:
        view = {
            "state": "OPEN",
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "headRefOid": SHA,
            "baseRefOid": BASE,
            "body": (
                f"Reviewed head `{SHA}` on base `{BASE}`.\n"
                "- **Kiro:** sign-off\n"
                "- **Not authorized:** R2a execution\n"
            ),
            "files": [{"path": p} for p in sorted(PR52_CLOSEOUT_ALLOWLIST)],
        }
        view.update(overrides)
        return view

    def _pass_items(self) -> list[EvidenceItem]:
        return [
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS", SHA),
                item_id=1,
            ),
            _item(
                body=_canonical("Kiro", "PASS", SHA),
                item_id=2,
                created_at="2026-07-20T10:01:00Z",
            ),
        ]

    def test_check_body_flags_codex_and_missing_sha(self):
        bad = check_body(
            "- **Codex:** audit\nhead missing\n",
            sha=SHA,
            base=BASE,
        )
        self.assertTrue(any("Codex" in e for e in bad))
        self.assertTrue(any("head" in e for e in bad))

    def test_readiness_ok(self):
        ok, msgs = verify_closeout_readiness(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            fetch_pr_view=self._clean_view,
            count_threads=lambda: 0,
            fetch_evidence=lambda *_a: self._pass_items(),
            check_allowlist=True,
        )
        self.assertTrue(ok, msgs)

    def test_unresolved_threads_fail(self):
        ok, msgs = verify_closeout_readiness(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            fetch_pr_view=self._clean_view,
            count_threads=lambda: 2,
            fetch_evidence=lambda *_a: self._pass_items(),
        )
        self.assertFalse(ok)
        self.assertTrue(any("unresolved" in m for m in msgs))

    def test_stale_codex_body_fail(self):
        view = self._clean_view(
            body=f"- **Codex:** audit\n{SHA}\n{BASE}\n",
        )
        ok, msgs = verify_closeout_readiness(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            fetch_pr_view=lambda: view,
            count_threads=lambda: 0,
            fetch_evidence=lambda *_a: self._pass_items(),
        )
        self.assertFalse(ok)
        self.assertTrue(any("Codex" in m for m in msgs))

    def test_wrong_head_fail(self):
        view = self._clean_view(headRefOid=OTHER)
        ok, msgs = verify_closeout_readiness(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            fetch_pr_view=lambda: view,
            count_threads=lambda: 0,
            fetch_evidence=lambda *_a: self._pass_items(),
        )
        self.assertFalse(ok)
        self.assertTrue(any("headRefOid" in m for m in msgs))

    def test_non_clean_fail(self):
        view = self._clean_view(mergeStateStatus="DIRTY")
        ok, msgs = verify_closeout_readiness(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            fetch_pr_view=lambda: view,
            count_threads=lambda: 0,
            fetch_evidence=lambda *_a: self._pass_items(),
        )
        self.assertFalse(ok)
        self.assertTrue(any("mergeStateStatus" in m for m in msgs))

    def test_lane_verifier_failure_propagates(self):
        ok, msgs = verify_closeout_readiness(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            fetch_pr_view=self._clean_view,
            count_threads=lambda: 0,
            fetch_evidence=lambda *_a: [],
        )
        self.assertFalse(ok)
        self.assertTrue(any("lane PASS" in m for m in msgs))

    def test_mutex_required(self):
        items = self._pass_items() + [
            _item(
                body="MAIN-MERGE-MUTEX ACQUIRED for PR #52 closeout",
                item_id=99,
                created_at="2026-07-20T12:00:00Z",
            )
        ]
        ok, msgs = verify_closeout_readiness(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            require_mutex_acquired=True,
            fetch_pr_view=self._clean_view,
            count_threads=lambda: 0,
            fetch_evidence=lambda *_a: items,
        )
        self.assertTrue(ok, msgs)

        released = self._pass_items() + [
            _item(
                body="MAIN-MERGE-MUTEX ACQUIRED for PR #52 closeout",
                item_id=98,
                created_at="2026-07-20T11:00:00Z",
            ),
            _item(
                body="MAIN-MERGE-MUTEX RELEASED for PR #52 closeout",
                item_id=99,
                created_at="2026-07-20T12:00:00Z",
            ),
        ]
        ok2, msgs2 = verify_closeout_readiness(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            require_mutex_acquired=True,
            fetch_pr_view=self._clean_view,
            count_threads=lambda: 0,
            fetch_evidence=lambda *_a: released,
        )
        self.assertFalse(ok2)
        self.assertTrue(any("mutex" in m.lower() for m in msgs2))

    def test_allowlist_constant_has_twelve_paths(self):
        self.assertEqual(len(PR52_CLOSEOUT_ALLOWLIST), 12)
        # Scripts load as modules (import side effects must not crash).
        for name in (
            "verify_exact_tip_lane_passes",
            "verify_pr_closeout_readiness",
        ):
            path = SCRIPTS / f"{name}.py"
            spec = importlib.util.spec_from_file_location(name, path)
            assert spec and spec.loader
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)


if __name__ == "__main__":
    unittest.main()
