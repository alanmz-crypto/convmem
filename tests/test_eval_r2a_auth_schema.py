"""Hermetic tests for R2a phase-scoped auth schema (no real eval-root writes)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eval_corpus import run_manifest as run_manifest_mod
from eval_corpus.run_manifest import (
    AuthContext,
    assert_operation_allowed,
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


def _approved_r2a(root: Path, *, embed_model: str = "fake-embed", host: str = "http://127.0.0.1:9"):
    out_dir, chroma = _eval_like(root)
    live = root / "live.toml"
    live.write_text(
        "[index]\nchroma_dir = \"/tmp/x\"\n"
        "processed_log = \"/tmp/APPROVED_LIVE_MARKER.json\"\n"
        f"[models]\nembed_model = \"approved-live-model\"\nollama_host = \"{host}\"\n",
        encoding="utf-8",
    )
    body = make_r2a_run_manifest_for_tests(
        paths={
            "live_config": str(live.resolve()),
            "out_dir": str(out_dir.resolve()),
            "chroma_dir": str(chroma.resolve()),
            "embed_host": host,
        },
        embed_model=embed_model,
    )
    man = _write_json(root / "r2a.json", body)
    write_approval_sidecar(man)
    runtime = {
        "live_config": live,
        "out_dir": out_dir,
        "chroma_dir": chroma,
        "embed_model": embed_model,
        "embed_host": host,
    }
    grant = bind_r2a_config_generation(run_manifest_path=man, runtime=runtime)
    return grant, runtime, man, live, out_dir, chroma


class R2aAuthSchemaTests(unittest.TestCase):
    def test_t1_global_real_fields_still_required(self):
        body = make_real_run_manifest_for_tests(
            paths={"export": "/tmp/e"},
            operations=["baseline_build"],
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

    def test_t3b_r2a_rejects_duplicate_operations(self):
        body = make_r2a_run_manifest_for_tests(
            paths={"live_config": "/tmp/l", "out_dir": "/tmp/o", "chroma_dir": "/tmp/c"}
        )
        body["operations"] = ["config_generation", "config_generation"]
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("exactly" in e for e in errs))

    def test_t4_r2a_wrong_harness_sha(self):
        body = make_r2a_run_manifest_for_tests(
            paths={"live_config": "/tmp/l", "out_dir": "/tmp/o", "chroma_dir": "/tmp/c"},
            merged_harness_sha256="0" * 64,
        )
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("Gate 1" in e or "merged_harness" in e for e in errs))

    def test_t4b_r2a_empty_embed_host_fails_schema(self):
        """Empty/whitespace host must fail schema (not only later bind)."""
        for host in ("", "   "):
            with self.subTest(host=repr(host)):
                body = make_r2a_run_manifest_for_tests(
                    paths={
                        "live_config": "/tmp/l",
                        "out_dir": "/tmp/o",
                        "chroma_dir": "/tmp/c",
                        "embed_host": host,
                    }
                )
                errs = validate_run_manifest_schema(body)
                self.assertTrue(
                    any("embed_host" in e for e in errs),
                    msg=errs,
                )
        body_top = make_r2a_run_manifest_for_tests(
            paths={
                "live_config": "/tmp/l",
                "out_dir": "/tmp/o",
                "chroma_dir": "/tmp/c",
            }
        )
        body_top.pop("embed_host", None)
        body_top["paths"].pop("embed_host", None)
        body_top["embed_host"] = ""
        body_top["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(
            body_top
        )
        errs_top = validate_run_manifest_schema(body_top)
        self.assertTrue(any("embed_host" in e for e in errs_top), msg=errs_top)

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
                    live_cfg=None,
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model="fake-embed",
                    ollama_host="http://127.0.0.1:9",
                )

    def test_t7_capability_immutable_and_unforgeable(self):
        with tempfile.TemporaryDirectory() as td:
            grant, runtime, _man, _live, out_dir, chroma = _approved_r2a(Path(td))
            self.assertTrue(is_r2a_eval_root_grant(grant))
            with self.assertRaises(AttributeError):
                grant._manifest_path = Path("/tmp/forged")  # pylint: disable=protected-access
            with self.assertRaises(TypeError):
                type(grant)()  # public constructor refused
            # Subclass / random object cannot authenticate
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=None,
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model=runtime["embed_model"],
                    ollama_host=runtime["embed_host"],
                    r2a_grant=object(),
                )
            fake_ctx = AuthContext(
                execution_mode="real",
                require_corpus_acceptance=False,
                manifest={"authorization_phase": "r2a"},
                operation="config_generation",
            )
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=None,
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model=runtime["embed_model"],
                    ollama_host=runtime["embed_host"],
                    r2a_grant=fake_ctx,
                )

    def test_t8_valid_capability_loads_approved_live_config(self):
        with tempfile.TemporaryDirectory() as td:
            grant, runtime, _man, live, out_dir, chroma = _approved_r2a(Path(td))
            path, violations = generate_shadow_config(
                live_cfg=None,
                out_dir=out_dir,
                chroma_dir=chroma,
                embed_model=runtime["embed_model"],
                ollama_host=runtime["embed_host"],
                r2a_grant=grant,
            )
            self.assertEqual(violations, [])
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            # Must come from approved live.toml, not a caller-supplied dict
            self.assertIn("APPROVED_LIVE_MARKER", text)
            self.assertIn(runtime["embed_model"], text)
            self.assertTrue(live.is_file())

    def test_t8b_caller_live_cfg_refused_under_r2a(self):
        with tempfile.TemporaryDirectory() as td:
            grant, runtime, _man, _live, out_dir, chroma = _approved_r2a(Path(td))
            with self.assertRaises(PermissionError) as ctx:
                generate_shadow_config(
                    live_cfg=_live_cfg(),
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model=runtime["embed_model"],
                    ollama_host=runtime["embed_host"],
                    r2a_grant=grant,
                )
            self.assertIn("refuses caller live_cfg", str(ctx.exception))

    def test_t9_grant_path_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            grant, runtime, _man, _live, _out, _chroma = _approved_r2a(root)
            other, other_c = _eval_like(root, "other")
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=None,
                    out_dir=other,
                    chroma_dir=other_c,
                    embed_model=runtime["embed_model"],
                    ollama_host=runtime["embed_host"],
                    r2a_grant=grant,
                )

    def test_t10_corrupt_sidecar_after_bind_refused(self):
        with tempfile.TemporaryDirectory() as td:
            grant, runtime, man, _live, out_dir, chroma = _approved_r2a(Path(td))
            side = man.with_suffix(man.suffix + ".approved.sha256")
            side.write_text("00" * 32 + "\n", encoding="utf-8")
            with self.assertRaises(PermissionError):
                generate_shadow_config(
                    live_cfg=None,
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model=runtime["embed_model"],
                    ollama_host=runtime["embed_host"],
                    r2a_grant=grant,
                )

    def test_t10b_write_time_prohibits_config_generation(self):
        """Capability issued under allow must fail if re-approved with prohibit."""
        with tempfile.TemporaryDirectory() as td:
            grant, runtime, man, _live, out_dir, chroma = _approved_r2a(Path(td))
            body = json.loads(man.read_text(encoding="utf-8"))
            body["prohibited_actions"] = ["config_generation"]
            body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
            man.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
            write_approval_sidecar(man)
            with self.assertRaises(PermissionError) as ctx:
                generate_shadow_config(
                    live_cfg=None,
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model=runtime["embed_model"],
                    ollama_host=runtime["embed_host"],
                    r2a_grant=grant,
                )
            msg = str(ctx.exception).lower()
            # Sealed approval digest blocks retarget; prohibit check is defense-in-depth.
            self.assertTrue(
                "prohibited" in msg or "digest" in msg or "retarget" in msg,
                msg=msg,
            )

    def test_t10c_string_prohibited_actions_fail_closed(self):
        """String prohibited_actions must not fail open via set(characters)."""
        body = make_r2a_run_manifest_for_tests(
            paths={
                "live_config": "/tmp/l",
                "out_dir": "/tmp/o",
                "chroma_dir": "/tmp/c",
            }
        )
        body["prohibited_actions"] = "config_generation"
        body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
        errs = validate_run_manifest_schema(body)
        self.assertTrue(any("prohibited_actions" in e for e in errs), msg=errs)
        with self.assertRaises(PermissionError) as ctx:
            assert_operation_allowed(body, "config_generation")
        self.assertIn("must be a list", str(ctx.exception))

    def test_t10d_no_raw_issuer_or_arm_controls(self):
        """Raw mint/arm/disarm must not be reachable at module or binder scope."""
        for name in (
            "_issue_r2a_capability",
            "_mint",
            "issue",
            "arm_issue",
            "disarm_issue",
        ):
            self.assertFalse(
                hasattr(run_manifest_mod, name),
                msg=f"module must not export {name}",
            )
        binder = run_manifest_mod.bind_r2a_config_generation
        self.assertTrue(callable(binder))
        self.assertFalse(hasattr(binder, "arm"))
        self.assertFalse(hasattr(binder, "disarm"))
        self.assertFalse(hasattr(binder, "issue"))
        # No nested callable named issue/arm/disarm/mint in the binder closure.
        for cell in binder.__closure__ or ():
            cell_obj = cell.cell_contents
            if not callable(cell_obj):
                continue
            name = getattr(cell_obj, "__name__", "")
            self.assertNotIn(
                name,
                {
                    "arm_issue",
                    "disarm_issue",
                    "issue",
                    "_mint",
                    "mint",
                    "_bind_impl",
                },
            )
            self.assertFalse(hasattr(cell_obj, "arm"))
            self.assertFalse(hasattr(cell_obj, "disarm"))

    def test_t10e_path_preserving_retarget_refused(self):
        """Same path + new approved live_config must not reuse old grant."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            grant, runtime, man, live, out_dir, chroma = _approved_r2a(root)
            # Replace approved live_config content and re-seal sidecar at same path.
            live.write_text(
                "[index]\nchroma_dir = \"/tmp/x\"\n"
                "processed_log = \"/tmp/RETARGETED_LIVE.json\"\n"
                "[models]\nembed_model = \"approved-live-model\"\n"
                f"ollama_host = \"{runtime['embed_host']}\"\n",
                encoding="utf-8",
            )
            body = json.loads(man.read_text(encoding="utf-8"))
            body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
            man.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
            write_approval_sidecar(man)
            # Body unchanged except digest field — force a real body change via model.
            body["embed_model"] = "retargeted-embed"
            body["ryan_approved_manifest_sha256"] = canonical_manifest_body_sha256(body)
            man.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
            write_approval_sidecar(man)
            with self.assertRaises(PermissionError) as ctx:
                generate_shadow_config(
                    live_cfg=None,
                    out_dir=out_dir,
                    chroma_dir=chroma,
                    embed_model="retargeted-embed",
                    ollama_host=runtime["embed_host"],
                    r2a_grant=grant,
                )
            self.assertIn("digest", str(ctx.exception).lower())

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
                    live_cfg=None,
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
