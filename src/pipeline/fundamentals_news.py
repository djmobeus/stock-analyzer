"""Phase 2 — fundamentals, news, sentiment, catalysts."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.loader import load_config
from data.fundamentals import enrich_and_filter_universe
from data.news import fetch_all_news
from data.universe import StockRecord
from db.repositories import upsert_catalyst, upsert_news_item
from intelligence.catalysts import (
    calendar_catalysts_from_yfinance,
    extract_catalysts_from_article,
    is_upcoming,
)
from intelligence.sentiment import score_headline

logger = logging.getLogger(__name__)


def apply_phase2_filters(records: list[StockRecord]) -> list[StockRecord]:
    """Apply yfinance fundamental filters 4–6."""
    config = load_config()
    min_analysts = config.get("universe", {}).get("min_analyst_count", 4)
    return enrich_and_filter_universe(records, min_analysts=min_analysts)


def _ingest_yfinance_calendars(tickers: list[str], workers: int = 8) -> int:
    """Store Yahoo earnings / ex-div dates as catalysts."""
    stored = 0

    def _one(ticker: str) -> int:
        n = 0
        for cat in calendar_catalysts_from_yfinance(ticker):
            upsert_catalyst(
                ticker=cat.ticker,
                event_type=cat.event_type,
                event_date=cat.event_date,
                description=cat.description,
                source=cat.source,
            )
            n += 1
        return n

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_one, t): t for t in tickers}
        for fut in as_completed(futs):
            try:
                stored += fut.result()
            except Exception as exc:
                logger.debug("Calendar ingest failed %s: %s", futs[fut], exc)
    return stored


def ingest_news_and_catalysts(universe: list[StockRecord]) -> dict:
    """Fetch RSS news + Yahoo calendars; score sentiment; extract catalysts."""
    tickers = [r.ticker for r in universe]
    name_map = {r.ticker: r.name or "" for r in universe if r.name}

    articles = fetch_all_news(tickers, name_map)
    news_count = 0
    catalyst_count = 0
    upcoming_count = 0

    for article in articles:
        sentiment = score_headline(f"{article.title} {article.summary}")
        primary_ticker = article.tickers[0] if article.tickers else None
        upsert_news_item(
            ticker=primary_ticker,
            title=article.title,
            url=article.url,
            published_at=article.published_at,
            sentiment_score=sentiment,
            summary=article.summary,
        )
        news_count += 1

        for ticker in article.tickers or ([primary_ticker] if primary_ticker else []):
            if not ticker:
                continue
            for cat in extract_catalysts_from_article(
                ticker, article.title, article.summary, article.source
            ):
                upsert_catalyst(
                    ticker=cat.ticker,
                    event_type=cat.event_type,
                    event_date=cat.event_date,
                    description=cat.description,
                    source=cat.source,
                )
                catalyst_count += 1
                if is_upcoming(cat.event_date):
                    upcoming_count += 1

    workers = int(load_config().get("pipeline", {}).get("max_workers", 8))
    # Cap Yahoo calendar calls on huge universes (still covers active/scorable set)
    cal_tickers = tickers[:200]
    logger.info("Fetching Yahoo calendars for %d tickers...", len(cal_tickers))
    yf_cats = _ingest_yfinance_calendars(cal_tickers, workers=workers)
    catalyst_count += yf_cats
    # Re-count upcoming roughly via yf_cats quality — detailed score uses DB at score time

    summary = {
        "news_articles": news_count,
        "catalysts": catalyst_count,
        "upcoming_catalysts": upcoming_count,
        "yfinance_calendar_catalysts": yf_cats,
    }
    logger.info("News/catalyst ingest: %s", summary)
    return summary
