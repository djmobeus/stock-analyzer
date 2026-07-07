"""Tests for ML model and embeddings."""

import pytest

from intelligence.embeddings import cosine_similarity, embed_texts
from intelligence.ml_model import FEATURE_KEYS, _features_vector, predict_probability
from intelligence.patterns import find_similar_observations, format_similar_summary


def test_cosine_similarity_identical():
    a = {"support": 1.0, "bounce": 0.5}
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_embed_texts_tfidf_fallback():
    vecs = embed_texts(["support bounce", "breakout chart"])
    assert len(vecs) == 2
    assert isinstance(vecs[0], dict)


def test_features_vector_defaults():
    vec = _features_vector({})
    assert len(vec) == len(FEATURE_KEYS) + 1


def test_predict_insufficient_data():
    result = predict_probability({"support_score": 80, "confluence": 2})
    assert result.probability is None
    assert result.reason == "insufficient_data"


def test_find_similar_observations():
    obs = [
        {
            "id": 1,
            "ticker": "A.L",
            "chart_description": "bounce off support level",
            "outcome_8w_pct": 10.0,
            "outcome_8w_hit": True,
        }
    ]
    matches = find_similar_observations("support bounce near 200 sma", obs)
    assert len(matches) >= 1


def test_format_similar_summary():
    matches = [{"outcome_pct": 9.0, "target_hit": True}, {"outcome_pct": 5.0, "target_hit": False}]
    s = format_similar_summary(matches)
    assert s is not None
    assert "1/2" in s
