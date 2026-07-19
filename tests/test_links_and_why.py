"""Tests for research links and why_chosen builder."""

from visualization.links import investing_url, research_links, yahoo_finance_url
from intelligence.why_chosen import build_why_chosen


def test_yahoo_finance_url():
    assert "BT-A.L" in yahoo_finance_url("BT-A.L")


def test_investing_slug_for_known_ticker():
    url = investing_url("BT-A.L")
    assert url is not None
    assert "bt-group" in url
    assert "/search/" not in url


def test_research_links_fallback_yahoo():
    links = research_links("UNKNOWNXYZ.L")
    assert links["primary"].startswith("https://uk.finance.yahoo.com/")
    assert links["primary_label"] == "Yahoo Finance"


def test_build_why_chosen_has_bullets(monkeypatch):
    monkeypatch.setattr("intelligence.why_chosen._company_name", lambda t: "Test Co")
    monkeypatch.setattr("intelligence.why_chosen._nearest_catalyst", lambda t: None)
    why = build_why_chosen(
        "TEST.L",
        {
            "distance_support_pct": 1.2,
            "confluence": 2,
            "conflict_flag": True,
            "analyst_upside_score": 60,
            "catalyst_score": 20,
            "news_sentiment_score": 50,
            "market_regime_score": 55,
        },
        54.0,
    )
    assert why["name"] == "Test Co"
    assert any("support" in b.lower() for b in why["bullets"])
    assert any("conflict" in b.lower() for b in why["bullets"])


def test_score_breakdown_rows():
    from visualization.charts import score_breakdown_rows

    rows = score_breakdown_rows(
        {
            "support_score": 80,
            "confluence": 2,
            "analyst_upside_score": 50,
            "catalyst_score": 40,
            "news_sentiment_score": 55,
            "market_regime_score": 60,
            "sector_relative_score": 50,
        }
    )
    assert len(rows) >= 5
    assert rows[0]["label"] == "Near support"
    assert rows[0]["contribution"] is not None


def test_resample_weekly_fewer_bars():
    import pandas as pd
    from visualization.charts import _resample_ohlcv

    idx = pd.date_range("2024-01-01", periods=40, freq="B")
    df = pd.DataFrame(
        {
            "Open": range(40),
            "High": range(1, 41),
            "Low": range(40),
            "Close": range(40),
            "Volume": [1000] * 40,
        },
        index=idx,
    )
    weekly = _resample_ohlcv(df, "Weekly")
    assert len(weekly) < len(df)
    assert len(weekly) >= 5
