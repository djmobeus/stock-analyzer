"""yfinance price fetching with LSE GBX normalisation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


@dataclass
class TickerPriceResult:
    """Result of fetching and normalising one ticker."""

    ticker: str
    currency: str | None
    dataframe: pd.DataFrame
    warnings: list[str] = field(default_factory=list)
    quarantine: bool = False
    quarantine_reason: str | None = None


def _normalise_currency_label(currency: str | None) -> str | None:
    if currency is None:
        return None
    return currency.strip()


def is_pence_currency(currency: str | None) -> bool:
    """True if Yahoo reports this ticker in pence (GBX)."""
    if not currency:
        return True  # Assume pence for LSE .L tickers when unknown
    c = currency.strip()
    # Yahoo uses "GBp" for pence — must check before GBP
    return c in ("GBp", "GBX") or c.upper() == "GBX"


def is_pound_currency(currency: str | None) -> bool:
    """True if Yahoo reports this ticker in pounds (needs x100)."""
    if not currency:
        return False
    c = currency.strip()
    # Exact "GBP" only — "GBp" is pence on Yahoo Finance
    return c == "GBP"


def normalise_ohlcv_to_gbx(
    df: pd.DataFrame,
    currency: str | None,
    ticker: str,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Convert OHLCV prices to GBX (pence).

    LSE stocks are quoted in pence. Yahoo sometimes returns GBP (pounds)
    in historical data — those rows need multiplying by 100.
    """
    warnings: list[str] = []
    if df.empty:
        return df, ["empty_dataframe"]

    out = df.copy()
    price_cols = [c for c in ("Open", "High", "Low", "Close", "Adj Close") if c in out.columns]

    if is_pound_currency(currency):
        warnings.append(f"{ticker}: currency is GBP — multiplying OHLC by 100 to GBX")
        for col in price_cols:
            out[col] = out[col] * 100.0
    elif not is_pence_currency(currency) and currency:
        warnings.append(f"{ticker}: unexpected currency '{currency}' — no conversion applied")

    # Detect rows that look like pounds slipped into pence series (price < £50 → <5000p typical)
    # If median close > 500 but some rows < 50, those rows may be in pounds
    if "Close" in out.columns and len(out) >= 4:
        closes = out["Close"].dropna()
        if len(closes) > 0:
            median = closes.median()
            if median > 100:  # typical LSE stock in pence
                pound_like = closes < median / 50
                if pound_like.any():
                    n = int(pound_like.sum())
                    warnings.append(
                        f"{ticker}: {n} rows look 100x too low (possible GBP in GBp series)"
                    )
                    idx = pound_like[pound_like].index
                    for col in price_cols:
                        out.loc[idx, col] = out.loc[idx, col] * 100.0

    return out, warnings


def fetch_ticker_metadata(ticker: str) -> dict:
    """Fetch Yahoo metadata for a ticker."""
    t = yf.Ticker(ticker)
    meta: dict = {}
    try:
        hist_meta = t.history_metadata
        if hist_meta:
            meta.update(hist_meta)
    except Exception:
        pass
    try:
        info = t.info
        if info:
            meta.setdefault("currency", info.get("currency"))
            meta.setdefault("exchange", info.get("exchange"))
    except Exception:
        pass
    return meta


def fetch_ohlcv(
    ticker: str,
    period: str = "2y",
    interval: str = "1d",
) -> TickerPriceResult:
    """
    Fetch daily OHLCV and normalise to GBX.

    Does NOT use repair=True (can corrupt valid GBp data).
    """
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=False)

    meta = fetch_ticker_metadata(ticker)
    currency = _normalise_currency_label(meta.get("currency"))

    warnings: list[str] = []
    if df.empty:
        return TickerPriceResult(
            ticker=ticker,
            currency=currency,
            dataframe=df,
            warnings=["no_price_data"],
            quarantine=True,
            quarantine_reason="no_price_data",
        )

    # Drop timezone for consistent storage
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df, norm_warnings = normalise_ohlcv_to_gbx(df, currency, ticker)
    warnings.extend(norm_warnings)

    return TickerPriceResult(
        ticker=ticker,
        currency=currency,
        dataframe=df,
        warnings=warnings,
    )


def latest_close_gbx(result: TickerPriceResult) -> float | None:
    """Most recent close price in pence."""
    if result.dataframe.empty or "Close" not in result.dataframe.columns:
        return None
    return float(result.dataframe["Close"].iloc[-1])
