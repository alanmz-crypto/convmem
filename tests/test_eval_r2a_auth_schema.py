"""Hermetic tests for R2a phase-scoped auth schema (no real eval-root writes)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eval_corpus.run_manifest import (
    GATE_1_HARNESS_SHA256,
    AuthContext,
    bind_config_generation,
    bind_r2a_config_generation,
    canonical_manifest_body_sha256,
    is_r2a_eval_root_grant,
    make_r2a_run_manifest_for_tests,
    make_real_run_manifest_for_tests,
    validate_run_manifest_schema,
    write_approval_sidecar,
)
from eval_corpus.shadow_config import generate_shadow_config


def _write_json(path: Path, body: dict) -> Path:
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def _live_cfg() -> dict:
    return {
        "index": {"chroma_dir": "/tmp/live-chroma", "processed_log": "/tmp/p.json"},
        "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://127.0.0.1:11434"},
    }


def _eval_like(root: Path, arm: str = "baseline") -> tuple[Path, Path]:
    """Temp paths containing /.local/share/convmem/eval for hermetic policy tests."""
    base = root / ".local" / "share" / "convmem" / "eval" / "run-test" / arm
    out_dir = base
    chroma = base / "chroma"
    out_dir.mkdir(parents=True, exist_ok=True)
    chroma.mkdir(parents=True, exist_ok=True)
    return out_dir, chroma


class R2aAuthSchemaTests(unittest.TestCase):
    def test_t1_global_real_fields_still_required(self):
        body = make_real_run_manifest_for_tests(
            paths={"export": "/tmp/e"},
            operations=["capture"],
        )
        del body["corpus_package_sha256"]
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("corpus_package_sha256" in e for e in errs))

    def test_t2_r2a_ok_without_corpus_query_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, chroma = _eval_like(root)
            live = root / "live.toml"
            live.write_text("[index]\nchroma_dir = \"x\"\n", encoding="utf-8")
            body = make_r2a_run_manifest_for_tests(
                paths={
                    "live_config": str(live),
                    "out_dir": str(out_dir),
                    "chroma_dir": str(chroma),
                    "embed_host": "http://127.0.0.1:9",
                }
            )
            self.assertNotIn("corpus_package_sha256", body)
            errs = validate_run_manifest_schema(body)
            self.assertEqual(errs, [])

    def test_t3_r2a_rejects_extra_operations(self):
        body = make_r2a_run_manifest_for_tests(
            paths={"live_config": "/tmp/l", "out_dir": "/tmp/o", "chroma_dir": "/tmp/c"}
        )
        body["operations"] = ["config_generation", "capture"]
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("exactly" in e or "forbids" in e for e in errs))

    def test_t4_r2a_wrong_harness_sha(self):
        body = make_r2a_run_manifest_for_tests(
            paths={"live_config": "/tmp/l", "out_dir": "/tmp/o", "chroma_dir": "/tmp/c"},
            merged_harness_sha256="0" * 64,
        )
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("Gate 1" in e or "merged_harness" in e for e in errs))

    def test_t5_r2a_missing_or_mismatched_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, chroma = _eval_like(root)
            live = root / "live.toml"
            live.write_text("[models]\nembed_model = \"x\"\n", encoding="utf-8")
            body = make_r2a_run_manifest_for_tests(
                paths={
                    "live_config": str(live),
                    "out_dir": str(out_dir),
                    "chroma_dir": str(chroma),
                    "embed_host": "http://127.0.0.1:9",
                }
            )
            man = _write_json(root / "r2a.json", body)
            runtime = {
                "live_config": live,
                "out_dir": out_dir,
                "chroma_dir": chroma,
                "embed_model": "fake-embed",
                "embed_host": "http://127.0.0.1:9",
            }
            with self.assertRaises(PermissionError):
                bind_r2a_config_generation(run_manifest_path=man, runtime=runtime)
            write_approval_sidecar(man)
            side = man.with_suffix(man.suffix + ".approved.sha256")
            side.write_text("deadbeef\n", encoding="utf-8")
            with self.assertRaises(PermissionError):
                bind_r2a_config_generation(run_manifest_path=man, runtime=runtime)

    def test_t6_eval_root_without_grant_refused(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir, chroma = _eval_like(Path(td))
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=_live_cfg(),
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model="fake-embed",
                    ollama_host="http://127.0.0.1:9",
                )

    def test_t7_forged_grant_and_authcontext_refused(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir, chroma = _eval_like(Path(td))
            fake_ctx = AuthContext(
                execution_mode="real",
                require_corpus_acceptance=False,
                manifest={"authorization_phase": "r2a"},
                operation="config_generation",
            )
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=_live_cfg(),
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model="fake-embed",
                    ollama_host="http://127.0.0.1:9",
                    r2a_grant=fake_ctx,
                )
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=_live_cfg(),
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model="fake-embed",
                    ollama_host="http://127.0.0.1:9",
                    r2a_grant=object(),
                )
            # Caller cannot construct a valid grant
            from eval_corpus import run_manifest as rm

            with self.assertRaises(PermissionError):
                rm._R2aEvalRootGrant(  # pylint: disable=protected-access
                    object(),
                    out_dir=str(out_dir),
                    chroma_dir=str(chroma),
                    embed_model="fake-embed",
                    embed_host="http://127.0.0.1:9",
                    merged_harness_sha256=GATE_1_HARNESS_SHA256,
                    manifest_path=Path(td) / "x.json",
                    body_sha256="0" * 64,
                    phase="r2a",
                )

    def test_t8_valid_grant_writes_shadow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, chroma = _eval_like(root)
            live = root / "live.toml"
            live.write_text(
                "[index]\nchroma_dir = \"/tmp/x\"\n"
                "[models]\nembed_model = \"nomic\"\nollama_host = \"http://127.0.0.1:9\"\n",
                encoding="utf-8",
            )
            host = "http://127.0.0.1:9"
            body = make_r2a_run_manifest_for_tests(
                paths={
                    "live_config": str(live.resolve()),
                    "out_dir": str(out_dir.resolve()),
                    "chroma_dir": str(chroma.resolve()),
                    "embed_host": host,
                },
                embed_model="fake-embed",
            )
            man = _write_json(root / "r2a.json", body)
            write_approval_sidecar(man)
            runtime = {
                "live_config": live,
                "out_dir": out_dir,
                "chroma_dir": chroma,
                "embed_model": "fake-embed",
                "embed_host": host,
            }
            grant = bind_r2a_config_generation(run_manifest_path=man, runtime=runtime)
            self.assertTrue(is_r2a_eval_root_grant(grant))
            path, violations = generate_shadow_config(
                live_cfg=_live_cfg(),
                out_dir=out_dir,
                chroma_dir=chroma,
                embed_model="fake-embed",
                ollama_host=host,
                r2a_grant=grant,
            )
            self.assertEqual(violations, [])
            self.assertTrue(path.is_file())
            self.assertIn("fake-embed", path.read_text(encoding="utf-8"))

    def test_t9_grant_path_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, chroma = _eval_like(root, "baseline")
            other, other_c = _eval_like(root, "other")
            live = root / "live.toml"
            live.write_text("[models]\nembed_model = \"x\"\n", encoding="utf-8")
            host = "http://127.0.0.1:9"
            body = make_r2a_run_manifest_for_tests(
                paths={
                    "live_config": str(live.resolve()),
                    "out_dir": str(out_dir.resolve()),
                    "chroma_dir": str(chroma.resolve()),
                    "embed_host": host,
                },
                embed_model="fake-embed",
            )
            man = _write_json(root / "r2a.json", body)
            write_approval_sidecar(man)
            grant = bind_r2a_config_generation(
                run_manifest_path=man,
                runtime={
                    "live_config": live,
                    "out_dir": out_dir,
                    "chroma_dir": chroma,
                    "embed_model": "fake-embed",
                    "embed_host": host,
                },
            )
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=_live_cfg(),
                    out_dir=other,
                    chroma_dir=other_c,
                    embed_model="fake-embed",
                    ollama_host=host,
                    r2a_grant=grant,
                )

    def test_t10_corrupt_sidecar_after_bind_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir, chroma = _eval_like(root)
            live = root / "live.toml"
            live.write_text("[models]\nembed_model = \"x\"\n", encoding="utf-8")
            host = "http://127.0.0.1:9"
            body = make_r2a_run_manifest_for_tests(
                paths={
                    "live_config": str(live.resolve()),
                    "out_dir": str(out_dir.resolve()),
                    "chroma_dir": str(chroma.resolve()),
                    "embed_host": host,
                },
                embed_model="fake-embed",
            )
            man = _write_json(root / "r2a.json", body)
            write_approval_sidecar(man)
            grant = bind_r2a_config_generation(
                run_manifest_path=man,
                runtime={
                    "live_config": live,
                    "out_dir": out_dir,
                    "chroma_dir": chroma,
                    "embed_model": "fake-embed",
                    "embed_host": host,
                },
            )
            side = man.with_suffix(man.suffix + ".approved.sha256")
            side.write_text("00" * 32 + "\n", encoding="utf-8")
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=_live_cfg(),
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model="fake-embed",
                    ollama_host=host,
                    r2a_grant=grant,
                )

    def test_t11_fixture_cannot_grant_or_write_eval_like(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir, chroma = _eval_like(Path(td))
            live = Path(td) / "live.toml"
            live.write_text("[models]\nembed_model = \"x\"\n", encoding="utf-8")
            with self.assertRaises(PermissionError):
                bind_config_generation(
                    authorize_fixture=True,
                    run_manifest_path=None,
                    runtime={
                        "live_config": live,
                        "out_dir": out_dir,
                        "chroma_dir": chroma,
                        "embed_model": "fake-embed",
                        "embed_host": "http://127.0.0.1:9",
                    },
                )
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=_live_cfg(),
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model="fake-embed",
                    ollama_host="http://127.0.0.1:9",
                )

    def test_t12_live_config_root_always_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg_like = root / ".config" / "convmem" / "shadow"
            cfg_like.mkdir(parents=True)
            chroma = cfg_like / "chroma"
            chroma.mkdir()
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=_live_cfg(),
                    out_dir=cfg_like,
                    chroma_dir=chroma,
                    embed_model="fake-embed",
                    ollama_host="http://127.0.0.1:9",
                )


if __name__ == "__main__":
    unittest.main()
