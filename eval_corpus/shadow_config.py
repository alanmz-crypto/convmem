"""Generate allowlisted shadow configs under caller-supplied out_dir only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eval_corpus.config_audit import SHADOW_CONFIG_ALLOWLIST, config_diff_violations
from eval_corpus.io_atomic import atomic_write_text
from eval_corpus.run_manifest import (
    materialize_r2a_write_authorization,
    path_is_eval_root,
    path_is_live_config_root,
)


def _toml_escape(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def render_toml(cfg: dict[str, Any]) -> str:
    lines: list[str] = []
    for section, body in cfg.items():
        if not isinstance(body, dict):
            continue
        lines.append(f"[{section}]")
        for k, v in body.items():
            lines.append(f"{k} = {_toml_escape(v)}")
        lines.append("")
    return "\n".join(lines)


def generate_shadow_config(
    *,
    live_cfg: dict[str, Any] | None = None,
    out_dir: Path,
    chroma_dir: Path,
    embed_model: str,
    processed_log: Path | None = None,
    units_export: Path | None = None,
    ollama_host: str | None = None,
    r2a_grant: Any | None = None,
) -> tuple[Path, list[str]]:
    """Write shadow.toml under out_dir.

    Eval-root paths require a binder-issued R2a capability. When that capability
    is present, the approved ``live_config`` path is loaded from the manifest
    after sidecar re-verification — caller-supplied ``live_cfg`` is refused.
    Live ``~/.config/convmem`` writes are always refused.
    """
    out_dir = Path(out_dir)
    chroma_dir = Path(chroma_dir)
    embed_host = ollama_host if ollama_host is not None else ""

    for p in (out_dir, chroma_dir):
        if path_is_live_config_root(p):
            raise PermissionError(f"refusing live config path {p}")

    needs_eval = path_is_eval_root(out_dir) or path_is_eval_root(chroma_dir)
    if needs_eval:
        if live_cfg is not None:
            raise PermissionError(
                "R2a eval-root generation refuses caller live_cfg; "
                "approved live_config is loaded from the run-manifest"
            )
        bindings = materialize_r2a_write_authorization(
            r2a_grant,
            out_dir=out_dir,
            chroma_dir=chroma_dir,
            embed_model=embed_model,
            embed_host=str(embed_host),
        )
        # Import here to avoid import cycles at module load.
        from config import load_config  # pylint: disable=import-outside-toplevel

        live_cfg = load_config(bindings.live_config)
        embed_model = bindings.embed_model
        embed_host = bindings.embed_host
        ollama_host = bindings.embed_host
    elif live_cfg is None:
        raise ValueError("live_cfg is required unless an R2a capability is provided")

    out_dir.mkdir(parents=True, exist_ok=True)

    shadow = {
        section: dict(body) if isinstance(body, dict) else body
        for section, body in live_cfg.items()
    }
    shadow.setdefault("index", {})
    shadow.setdefault("models", {})
    shadow["index"]["chroma_dir"] = str(chroma_dir)
    if processed_log is not None:
        shadow["index"]["processed_log"] = str(processed_log)
    if units_export is not None:
        shadow["index"]["units_export"] = str(units_export)
    shadow["models"]["embed_model"] = embed_model
    if ollama_host is not None:
        shadow["models"]["ollama_host"] = ollama_host
    shadow.setdefault("eval", {})
    shadow["eval"]["rerank_mode"] = "identity"
    shadow["eval"]["retrieval_view"] = "embedding_influenced"

    violations = config_diff_violations(live_cfg, shadow)
    path = out_dir / "shadow.toml"
    atomic_write_text(path, render_toml(shadow))
    return path, violations


__all__ = ["SHADOW_CONFIG_ALLOWLIST", "generate_shadow_config", "render_toml"]
