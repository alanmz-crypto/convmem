import os

# Must be set before transformers/sentence-transformers load models.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")

from contextlib import redirect_stderr
from io import StringIO

from sentence_transformers import CrossEncoder

_model = None


def get_model(model_name: str) -> CrossEncoder:
    global _model
    if _model is None:
        with redirect_stderr(StringIO()):
            _model = CrossEncoder(model_name, device="cuda")
    return _model


def rerank(query: str, candidates: list[dict], model_name: str, top_k: int) -> list[dict]:
    model = get_model(model_name)
    pairs = [(query, c["document"]) for c in candidates]
    scores = model.predict(pairs)
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [c for _, c in ranked[:top_k]]
