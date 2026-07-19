"""Generate allowlisted shadow configs under caller-supplied out_dir only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eval_corpus.config_audit import SHADOW_CONFIG_ALLOWLIST, config_diff_violations
from eval_corpus.io_atomic import atomic_write_text


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
    live_cfg: dict[str, Any],
    out_dir: Path,
    chroma_dir: Path,
    embed_model: str,
    processed_log: Path | None = None,
    units_export: Path | None = None,
) -> tuple[Path, list[str]]:
    """Write shadow.toml under out_dir. Never touches ~/.config or ~/.local/share/convmem/eval."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    forbidden = ("/.config/convmem", "/.local/share/convmem/eval")
    for p in (out_dir, chroma_dir):
        s = str(Path(p).resolve())
        if any(f in s for f in forbidden):
            raise PermissionError(f"refusing external path {s}")

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
    shadow.setdefault("eval", {})
    shadow["eval"]["retrieval_view"] = "embedding_influenced"

    violations = config_diff_violations(live_cfg, shadow)
    # Filter allowlisted diffs only — violations should be empty
    path = out_dir / "shadow.toml"
    atomic_write_text(path, render_toml(shadow))
    return path, violations


__all__ = ["SHADOW_CONFIG_ALLOWLIST", "generate_shadow_config", "render_toml"]
