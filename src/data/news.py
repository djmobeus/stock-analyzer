"""RSS news ingestion for UK market feeds."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

import feedparser

from config.loader import load_config

logger = logging.getLogger(__name__)

# RNS / regulatory noise — skip for catalyst and sentiment
NOISE_PATTERNS = re.compile(
    r"transaction in own shares|total voting rights|"
    r"director.?pdmr|holding\(s\) in company|"
    r"notification of transactions|"
    r"block listing interim review|"
    r"treasury stock",
    re.IGNORECASE,
)


@dataclass
class NewsArticle:
    title: str
    url: str
    summary: str
    published_at: datetime | None
    source: str
    tickers: list[str]


def _default_feeds() -> list[dict[str, str]]:
    return [
        {
            "name": "proactive",
            "url": "https://www.proactiveinvestors.co.uk/rss/articles",
        },
        {
            "name": "investegate",
            "url": "https://www.investegate.co.uk/rss/latest",
        },
    ]


def load_feed_urls() -> list[dict[str, str]]:
    config = load_config()
    feeds = config.get("news", {}).get("feeds")
    return feeds if feeds else _default_feeds()


def is_noise(title: str, summary: str = "") -> bool:
    """True if article is low-value regulatory noise."""
    return bool(NOISE_PATTERNS.search(f"{title} {summary}"))


def build_ticker_matcher(tickers: list[str], names: dict[str, str]) -> re.Pattern:
    """
    Build regex to find tickers and company names in text.

    names: ticker -> company name
    """
    parts: list[str] = []
    for t in tickers:
        epic = t.replace(".L", "")
        parts.append(re.escape(epic))
        parts.append(re.escape(t))
        name = names.get(t, "")
        if name and len(name) > 3:
            parts.append(re.escape(name))
    if not parts:
        return re.compile(r"a^")  # match nothing
    return re.compile("|".join(parts), re.IGNORECASE)


def match_tickers(text: str, pattern: re.Pattern) -> list[str]:
    """Return epic matches found in text (uppercase, no .L)."""
    found = {m.group(0).upper().replace(".L", "") for m in pattern.finditer(text)}
    return sorted(found)


def fetch_feed_articles(
    feed_url: str,
    source: str,
    ticker_pattern: re.Pattern | None = None,
    universe_epics: set[str] | None = None,
) -> Iterator[NewsArticle]:
    """Parse one RSS feed and yield relevant articles."""
    try:
        parsed = feedparser.parse(feed_url)
    except Exception as exc:
        logger.warning("Feed parse failed %s: %s", feed_url, exc)
        return

    for entry in parsed.entries:
        title = entry.get("title", "").strip()
        summary = entry.get("summary", entry.get("description", ""))
        if is_noise(title, summary):
            continue

        url = entry.get("link", "")
        if not url:
            continue

        published = None
        if entry.get("published_parsed"):
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        matched: list[str] = []
        if ticker_pattern and universe_epics:
            text = f"{title} {summary}"
            for epic in match_tickers(text, ticker_pattern):
                if epic in universe_epics:
                    matched.append(f"{epic}.L")

        if universe_epics and not matched:
            continue  # only store articles mentioning our universe

        yield NewsArticle(
            title=title,
            url=url,
            summary=summary[:2000] if summary else "",
            published_at=published,
            source=source,
            tickers=matched,
        )


def fetch_all_news(
    universe_tickers: list[str],
    name_map: dict[str, str] | None = None,
) -> list[NewsArticle]:
    """Fetch and filter news from all configured feeds."""
    name_map = name_map or {}
    epics = {t.replace(".L", "").upper() for t in universe_tickers}
    pattern = build_ticker_matcher(universe_tickers, name_map)

    articles: list[NewsArticle] = []
    seen_urls: set[str] = set()

    for feed in load_feed_urls():
        logger.info("Fetching feed: %s", feed["name"])
        for article in fetch_feed_articles(
            feed["url"],
            feed["name"],
            ticker_pattern=pattern,
            universe_epics=epics,
        ):
            if article.url in seen_urls:
                continue
            seen_urls.add(article.url)
            articles.append(article)

    logger.info("Fetched %d relevant news articles", len(articles))
    return articles


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]
