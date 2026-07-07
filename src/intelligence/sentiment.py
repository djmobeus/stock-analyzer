"""News sentiment analysis."""

from __future__ import annotations

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score_headline(text: str) -> float:
    """
    Score headline/summary sentiment from -1 (negative) to +1 (positive).

    Uses VADER — fast, free, no GPU required.
    """
    if not text.strip():
        return 0.0
    scores = _analyzer.polarity_scores(text)
    return float(scores["compound"])
