"""Tests for Phase 4 — observations, outcomes, patterns."""

from intelligence.patterns import parse_chart_patterns, pattern_key
from pipeline.outcomes import _pct_change, evaluate_flags


def test_parse_chart_patterns_support():
    patterns = parse_chart_patterns("Nice bounce off support with volume surge")
    assert "support_bounce" in patterns
    assert "volume_surge" in patterns


def test_parse_chart_patterns_unspecified():
    assert parse_chart_patterns("") == ["unspecified"]
    assert parse_chart_patterns(None) == ["unspecified"]


def test_pattern_key_sorted():
    assert pattern_key(["catalyst", "support_bounce"]) == "catalyst+support_bounce"


def test_evaluate_flags_buy_hit():
    target_hit, stop_hit, correct = evaluate_flags("buy", 10.0, 8.0, -5.0)
    assert target_hit == 1
    assert stop_hit == 0
    assert correct == 1


def test_evaluate_flags_buy_stop():
    target_hit, stop_hit, correct = evaluate_flags("buy", -6.0, 8.0, -5.0)
    assert target_hit == 0
    assert stop_hit == 1
    assert correct == 0


def test_evaluate_flags_avoid():
    _, _, correct = evaluate_flags("avoid", 2.0, 8.0, -5.0)
    assert correct == 1


def test_pct_change():
    assert _pct_change(100, 108) == 8.0
