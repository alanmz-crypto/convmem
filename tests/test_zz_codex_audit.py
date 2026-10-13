"""Codex audit probes for issue #286 stage-2 corrective 6 (reference fixtures)."""

# pylint: disable=protected-access

from __future__ import annotations


def _route_fixture(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from incremental_jsonl_production import ProductionBoundary
    from tests.incremental_jsonl_helpers import install_fakes
    from tests.test_incremental_jsonl_codex_rollout_route import _write_user_config
    from tests.test_issue_286_stage2_wedge_probes import _codex_env, _route

    source, cfg = _codex_env(tmp_path, monkeypatch)
    cfg["models"]["deepseek_base_url"] = "http://127.0.0.1:9"
    config_path = tmp_path / "config.toml"
    _write_user_config(config_path, cfg)
    install_fakes(monkeypatch)

    class ScratchBoundary(ProductionBoundary):
        def __init__(self, cfg_arg, path):
            super().__init__(cfg_arg, path, config_path=config_path)

    monkeypatch.setattr(inc, "ProductionBoundary", ScratchBoundary)
    return source, cfg, lambda: _route(cfg, source)
