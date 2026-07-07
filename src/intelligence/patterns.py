"""Chart description pattern parsing and rolling statistics."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Keyword map: pattern_type -> regex (case-insensitive)
PATTERN_KEYWORDS: list[tuple[str, re.Pattern]] = [
    ("support_bounce", re.compile(r"support|bounce|near support|holding support", re.I)),
    ("breakout", re.compile(r"breakout|breaking out|break above", re.I)),
    ("pullback", re.compile(r"pullback|pull back|retrace|dip", re.I)),
    ("golden_cross", re.compile(r"golden cross|sma cross|ma cross", re.I)),
    ("oversold", re.compile(r"oversold|rsi low|beaten down", re.I)),
    ("catalyst", re.compile(r"catalyst|results|earnings|dividend|agm", re.I)),
    ("double_bottom", re.compile(r"double bottom|w bottom", re.I)),
    ("flag", re.compile(r"flag|consolidation|coiling", re.I)),
    ("resistance_break", re.compile(r"resistance break|above resistance", re.I)),
    ("volume_surge", re.compile(r"volume surge|high volume|volume spike", re.I)),
]


def parse_chart_patterns(description: str | None) -> list[str]:
    """Extract structured pattern tags from free-text chart description."""
    if not description or not description.strip():
        return ["unspecified"]
    found = [name for name, pattern in PATTERN_KEYWORDS if pattern.search(description)]
    return found or ["unspecified"]


def pattern_key(patterns: list[str]) -> str:
    """Stable key for grouping stats (sorted, deduplicated)."""
    unique = sorted(set(patterns))
    return "+".join(unique)


def find_similar_observations(
    description: str,
    observations: list[dict],
    top_n: int = 5,
    min_similarity: float = 0.15,
) -> list[dict]:
    """
    Find historically similar chart descriptions with outcomes.

    Returns dicts with keys: observation_id, ticker, similarity, outcome_pct, wins, total.
    """
    from intelligence.embeddings import cosine_similarity, embed_texts

    if not description or not observations:
        return []

    corpus = [description]
    valid_obs = []
    for obs in observations:
        desc = (obs.get("chart_description") or "").strip()
        if desc:
            corpus.append(desc)
            valid_obs.append(obs)

    if len(corpus) < 2:
        return []

    vectors = embed_texts(corpus)
    query = vectors[0]
    matches = []
    for vec, obs in zip(vectors[1:], valid_obs):
        sim = cosine_similarity(query, vec)
        if sim < min_similarity:
            continue
        outcome_pct = obs.get("outcome_8w_pct")
        matches.append(
            {
                "observation_id": obs["id"],
                "ticker": obs["ticker"],
                "description": obs.get("chart_description", ""),
                "similarity": round(sim, 3),
                "outcome_pct": outcome_pct,
                "target_hit": obs.get("outcome_8w_hit"),
            }
        )

    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches[:top_n]


def format_similar_summary(matches: list[dict]) -> str | None:
    """Template: Similar pattern: 10/14 wins, avg +9.1%"""
    if not matches:
        return None
    with_outcome = [m for m in matches if m.get("outcome_pct") is not None]
    if not with_outcome:
        return f"Similar descriptions: {len(matches)} match(es), outcomes pending"
    hits = sum(1 for m in with_outcome if m.get("target_hit"))
    avg = sum(float(m["outcome_pct"]) for m in with_outcome) / len(with_outcome)
    return f"Similar pattern: {hits}/{len(with_outcome)} wins, avg {avg:+.1f}%"


@dataclass
class PatternStat:
    pattern_type: str
    sample_count: int
    hit_count: int
    avg_gain_pct: float
    avg_weeks: float

    @property
    def hit_rate_pct(self) -> float:
        if self.sample_count <= 0:
            return 0.0
        return self.hit_count / self.sample_count * 100
