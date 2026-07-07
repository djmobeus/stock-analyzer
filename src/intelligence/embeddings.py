"""Text embedding and similarity search for chart descriptions."""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    if not texts:
        return []
    docs = [_tokenize(t) for t in texts]
    df: dict[str, int] = {}
    for tokens in docs:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    n = len(docs)
    vectors: list[dict[str, float]] = []
    for tokens in docs:
        tf: dict[str, int] = {}
        for term in tokens:
            tf[term] = tf.get(term, 0) + 1
        vec: dict[str, float] = {}
        denom = float(len(tokens) or 1)
        for term, count in tf.items():
            idf = math.log((1 + n) / (1 + df.get(term, 0))) + 1
            vec[term] = (count / denom) * idf
        vectors.append(vec)
    return vectors


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class SimilarMatch:
    observation_id: int
    ticker: str
    description: str
    similarity: float
    outcome_pct: float | None
    target_hit: bool | None


def embed_texts(texts: list[str]) -> list[dict[str, float]]:
    """
    Embed texts for similarity search.

    Uses sentence-transformers when installed; otherwise TF-IDF (no extra deps).
    """
    if not texts:
        return []
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [{str(i): float(v) for i, v in enumerate(vec)} for vec in embeddings]
    except Exception as exc:
        logger.debug("sentence-transformers unavailable (%s); using TF-IDF", exc)
        return _tfidf_vectors(texts)
