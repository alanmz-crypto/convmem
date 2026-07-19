import os
import sys
import math

# Must be set before transformers/sentence-transformers load models.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")

from contextlib import redirect_stderr
from io import StringIO

from sentence_transformers import CrossEncoder  # pylint: disable=import-error

_model = None


def get_model(model_name: str) -> CrossEncoder:
    global _model
    if _model is None:
        with redirect_stderr(StringIO()):
            try:
                _model = CrossEncoder(model_name, device="cuda")
            except (RuntimeError, Exception) as e:
                print(f"[rerank] CUDA failed ({e}), falling back to CPU", file=sys.stderr)
                _model = CrossEncoder(model_name, device="cpu")
    return _model


def _normalize_scores(scores: list[float]) -> list[float]:
    """Map model logits to stable 0..1 values without changing their order."""
    return [1.0 / (1.0 + math.exp(-max(min(score, 60.0), -60.0))) for score in scores]


def rerank(query: str, candidates: list[dict], model_name: str, top_k: int) -> list[dict]:
    """Cross-encode candidates and preserve both semantic and reranker scores."""
    if not candidates:
        return []
    model = get_model(model_name)
    pairs = [(query, c["document"]) for c in candidates]
    raw_scores = [float(score) for score in model.predict(pairs)]
    normalized = _normalize_scores(raw_scores)
    ranked = sorted(
        zip(raw_scores, normalized, candidates),
        key=lambda item: item[0],
        reverse=True,
    )
    out: list[dict] = []
    for rank, (raw_score, norm_score, candidate) in enumerate(ranked[:top_k], 1):
        row = dict(candidate)
        row["rerank_score"] = round(raw_score, 6)
        row["rerank_score_norm"] = round(norm_score, 6)
        row["rerank_rank"] = rank
        row["rank_score"] = row["rerank_score_norm"]
        out.append(row)
    return out
