"""How Ollama names a model, so two spellings of one model compare equal and nothing else does.

A name is ``[host/][namespace/]model[:tag]`` with the defaults ``registry.ollama.ai``,
``library`` and ``latest``, compared case-insensitively. Two names are the same model when
those four components are equal after defaults. Components are parsed, never stripped by
prefix: ``library/acme/model`` has host ``library`` and namespace ``acme``, which is not
``acme/model`` (default host, namespace ``acme``).

A name that does not fit the grammar (an empty component, a stray colon, too many parts) equals
only an identical string, so a malformed configuration still matches its own stamp but is
never mistaken for a well-formed model.
"""

from __future__ import annotations

import re

DEFAULT_HOST = "registry.ollama.ai"
DEFAULT_NAMESPACE = "library"
_HOST = re.compile(r"[a-z0-9][a-z0-9.-]*(:[0-9]{1,5})?")
_PART = re.compile(r"[a-z0-9][a-z0-9._-]*")


def _normalized(value: object) -> str | None:
    """The name stripped of surrounding blanks; None unless it is a non-blank string."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def parse_embed_model(value: object) -> tuple[str, str, str, str] | None:
    """(host, namespace, model, tag), or None for anything outside the grammar."""
    name = _normalized(value)
    if name is None:
        return None
    parts = name.lower().split("/")
    if len(parts) > 3:
        return None
    model, colon, tag = parts[-1].partition(":")
    if colon and not tag:
        return None  # "x:" is not "x:latest"
    host, namespace = DEFAULT_HOST, DEFAULT_NAMESPACE
    if len(parts) == 3:
        host, namespace = parts[0], parts[1]
    elif len(parts) == 2:
        namespace = parts[0]
    ok = (
        _HOST.fullmatch(host)
        and _PART.fullmatch(namespace)
        and _PART.fullmatch(model)
        and _PART.fullmatch(tag or "latest")
    )
    return (host, namespace, model, tag or "latest") if ok else None


def same_embed_model(first: object, second: object) -> bool:
    """True when two names denote one Ollama model."""
    left, right = parse_embed_model(first), parse_embed_model(second)
    if left is None or right is None:
        # Outside the grammar: equal only to an identical string, never to a valid name.
        return left is None and right is None and _normalized(first) is not None and (
            _normalized(first) == _normalized(second)
        )
    return left == right
