"""Database write helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

from db.connection import get_connection, get_placeholder
from data.universe import StockRecord


def _execute_many(conn: Any, sql: str, rows: list[tuple]) -> None:
    if not rows:
        return
    cur = conn.cursor()
    cur.executemany(sql, rows)


def upsert_stocks(records: list[StockRecord], as_of: datetime) -> None:
    """Insert or update stocks in universe."""
    ph = get_placeholder()
    sql = f"""
        INSERT INTO stocks (ticker, name, sector, market_cap_gbp, avg_volume, is_active, last_updated)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 1, {ph})
        ON CONFLICT (ticker) DO UPDATE SET
            name = excluded.name,
            sector = excluded.sector,
            market_cap_gbp = excluded.market_cap_gbp,
            avg_volume = excluded.avg_volume,
            is_active = 1,
            last_updated = excluded.last_updated
    """
    rows = [
        (r.ticker, r.name, r.sector, r.market_cap_gbp, r.avg_volume, as_of.isoformat())
        for r in records
    ]
    with get_connection() as conn:
        _execute_many(conn, sql, rows)


def upsert_daily_prices(
    ticker: str,
    df: pd.DataFrame,
    currency_source: str | None,
) -> int:
    """Upsert OHLCV rows. Returns number of rows written."""
    if df.empty:
        return 0
    ph = get_placeholder()
    sql = f"""
        INSERT INTO daily_prices
            (ticker, date, open_gbx, high_gbx, low_gbx, close_gbx, adj_close_gbx, volume, currency_source)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ON CONFLICT (ticker, date) DO UPDATE SET
            open_gbx = excluded.open_gbx,
            high_gbx = excluded.high_gbx,
            low_gbx = excluded.low_gbx,
            close_gbx = excluded.close_gbx,
            adj_close_gbx = excluded.adj_close_gbx,
            volume = excluded.volume,
            currency_source = excluded.currency_source
    """
    rows: list[tuple] = []
    for ts, row in df.iterrows():
        d = ts.date() if hasattr(ts, "date") else ts
        adj = row.get("Adj Close", row.get("Close"))
        rows.append(
            (
                ticker,
                d.isoformat() if hasattr(d, "isoformat") else str(d),
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                float(adj) if pd.notna(adj) else None,
                float(row.get("Volume", 0)),
                currency_source,
            )
        )
    with get_connection() as conn:
        _execute_many(conn, sql, rows)
    return len(rows)


def upsert_indicators(rows: list[dict[str, Any]]) -> int:
    """Upsert technical indicator rows."""
    if not rows:
        return 0
    ph = get_placeholder()
    sql = f"""
        INSERT INTO technical_indicators
            (ticker, date, timeframe, indicator_name, value, metadata)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ON CONFLICT (ticker, date, timeframe, indicator_name) DO UPDATE SET
            value = excluded.value,
            metadata = excluded.metadata
    """
    tuples = [
        (
            r["ticker"],
            r["date"].isoformat() if hasattr(r["date"], "isoformat") else r["date"],
            r["timeframe"],
            r["indicator_name"],
            r["value"],
            r.get("metadata"),
        )
        for r in rows
    ]
    with get_connection() as conn:
        _execute_many(conn, sql, tuples)
    return len(tuples)


def save_quality_flag(
    ticker: str,
    flag_date: date,
    flag_type: str,
    details: str,
    quarantined: bool = False,
) -> None:
    """Insert or update a data quality flag."""
    ph = get_placeholder()
    sql = f"""
        INSERT INTO data_quality_flags (ticker, flag_date, flag_type, details, quarantined)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
        ON CONFLICT (ticker, flag_date, flag_type) DO UPDATE SET
            details = excluded.details,
            quarantined = excluded.quarantined
    """
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                sql,
                (ticker, flag_date.isoformat(), flag_type, details, int(quarantined)),
            )
        except Exception:
            cur.execute(
                f"DELETE FROM data_quality_flags WHERE ticker={ph} AND flag_date={ph} AND flag_type={ph}",
                (ticker, flag_date.isoformat(), flag_type),
            )
            cur.execute(
                f"""
                INSERT INTO data_quality_flags (ticker, flag_date, flag_type, details, quarantined)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (ticker, flag_date.isoformat(), flag_type, details, int(quarantined)),
            )


def start_scan_run() -> int:
    """Record pipeline start; return scan_run id."""
    ph = get_placeholder()
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.cursor()
        if ph == "%s":
            cur.execute(
                f"INSERT INTO scan_runs (started_at, status) VALUES ({ph}, {ph}) RETURNING id",
                (now, "running"),
            )
            run_id = cur.fetchone()[0]
        else:
            cur.execute(
                f"INSERT INTO scan_runs (started_at, status) VALUES ({ph}, {ph})",
                (now, "running"),
            )
            run_id = cur.lastrowid
    return int(run_id)


def finish_scan_run(
    run_id: int,
    status: str,
    stocks_processed: int,
    stocks_quarantined: int,
    error_message: str | None = None,
) -> None:
    """Update scan_run with results."""
    ph = get_placeholder()
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE scan_runs SET
                finished_at = {ph},
                status = {ph},
                stocks_processed = {ph},
                stocks_quarantined = {ph},
                error_message = {ph}
            WHERE id = {ph}
            """,
            (now, status, stocks_processed, stocks_quarantined, error_message, run_id),
        )


def upsert_news_item(
    ticker: str | None,
    title: str,
    url: str,
    published_at: datetime | None,
    sentiment_score: float | None,
    summary: str,
) -> None:
    ph = get_placeholder()
    pub = published_at.isoformat() if published_at else None
    sql = f"""
        INSERT INTO news_items (ticker, title, url, published_at, sentiment_score, summary)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ON CONFLICT (url) DO UPDATE SET
            sentiment_score = excluded.sentiment_score,
            summary = excluded.summary
    """
    with get_connection() as conn:
        conn.cursor().execute(sql, (ticker, title, url, pub, sentiment_score, summary))


def upsert_catalyst(
    ticker: str,
    event_type: str,
    event_date: date | None,
    description: str,
    source: str,
) -> None:
    ph = get_placeholder()
    ed = event_date.isoformat() if event_date else None
    sql = f"""
        INSERT INTO catalysts (ticker, event_type, event_date, description, source)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """
    with get_connection() as conn:
        conn.cursor().execute(sql, (ticker, event_type, ed, description, source))


def upsert_candidates(scan_date: date, scores: list) -> None:
    """Shadow-log ranked candidates for a scan date."""
    import json

    ph = get_placeholder()
    sql = f"""
        INSERT INTO candidates (scan_date, ticker, rank, composite_score, features_json)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """
    rows = [
        (
            scan_date.isoformat(),
            s.ticker,
            rank,
            s.composite_score,
            json.dumps(s.features),
        )
        for rank, s in enumerate(scores, 1)
    ]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM candidates WHERE scan_date = {ph}", (scan_date.isoformat(),))
        _execute_many(conn, sql, rows)


# --- Observations & outcomes (Phase 4) ---


def insert_observation(
    ticker: str,
    observed_at: datetime,
    entry_price_gbx: float | None,
    prediction: str,
    confidence: str,
    chart_description: str,
    features_json: str,
) -> int:
    ph = get_placeholder()
    obs = observed_at.isoformat()
    with get_connection() as conn:
        cur = conn.cursor()
        if ph == "%s":
            cur.execute(
                f"""
                INSERT INTO observations
                    (ticker, observed_at, entry_price_gbx, prediction, confidence,
                     chart_description, features_json)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                RETURNING id
                """,
                (
                    ticker,
                    obs,
                    entry_price_gbx,
                    prediction,
                    confidence,
                    chart_description,
                    features_json,
                ),
            )
            return int(cur.fetchone()[0])
        cur.execute(
            f"""
            INSERT INTO observations
                (ticker, observed_at, entry_price_gbx, prediction, confidence,
                 chart_description, features_json)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                ticker,
                obs,
                entry_price_gbx,
                prediction,
                confidence,
                chart_description,
                features_json,
            ),
        )
        return int(cur.lastrowid)


def get_observations(ticker: str | None = None, limit: int = 200) -> list[dict]:
    ph = get_placeholder()
    sql = f"""
        SELECT id, ticker, observed_at, entry_price_gbx, prediction, confidence,
               chart_description, features_json, created_at
        FROM observations
    """
    params: list = []
    if ticker:
        sql += f" WHERE ticker = {ph}"
        params.append(ticker)
    sql += " ORDER BY observed_at DESC"
    sql += f" LIMIT {ph}"
    params.append(limit)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

    cols = (
        "id",
        "ticker",
        "observed_at",
        "entry_price_gbx",
        "prediction",
        "confidence",
        "chart_description",
        "features_json",
        "created_at",
    )
    return [dict(zip(cols, row)) for row in rows]


def get_latest_candidate_scan() -> date | None:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MAX(scan_date) FROM candidates")
        row = cur.fetchone()
    if not row or not row[0]:
        return None
    val = row[0]
    return date.fromisoformat(str(val)) if not isinstance(val, date) else val


def _ticker_price_aliases(ticker: str) -> list[str]:
    """Yahoo / DB ticker variants (BT-A.L vs BT.A.L)."""
    variants = [ticker]
    if ticker.endswith(".L"):
        base = ticker[:-2]
        if "." in base and "-" not in base:
            variants.append(base.replace(".", "-") + ".L")
        elif "-" in base:
            variants.append(base.replace("-", ".") + ".L")
    return list(dict.fromkeys(variants))


def get_latest_price_gbx(ticker: str) -> float | None:
    ph = get_placeholder()
    tickers = _ticker_price_aliases(ticker)

    with get_connection() as conn:
        cur = conn.cursor()
        for t in tickers:
            cur.execute(
                f"SELECT close_gbx FROM daily_prices WHERE ticker = {ph} ORDER BY date DESC LIMIT 1",
                (t,),
            )
            row = cur.fetchone()
            if row:
                return float(row[0])

    try:
        import yfinance as yf

        for t in tickers:
            hist = yf.Ticker(t).history(period="5d")
            if hist.empty:
                continue
            close = float(hist["Close"].iloc[-1])
            info = yf.Ticker(t).info or {}
            currency = info.get("currency", "GBp")
            if currency in ("GBP", "GBp", "GBX") and currency == "GBP":
                close *= 100
            return close
    except Exception:
        pass
    return None


def get_price_on_or_before(ticker: str, on_date: date) -> float | None:
    """Close price on or nearest trading day before on_date."""
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT close_gbx FROM daily_prices
            WHERE ticker = {ph} AND date <= {ph}
            ORDER BY date DESC LIMIT 1
            """,
            (ticker, on_date.isoformat()),
        )
        row = cur.fetchone()
    if row:
        return float(row[0])

    try:
        import yfinance as yf

        start = on_date - timedelta(days=10)
        df = yf.Ticker(ticker).history(start=start.isoformat(), end=(on_date + timedelta(days=1)).isoformat())
        if df.empty:
            return None
        return float(df["Close"].iloc[-1])
    except Exception:
        return None


def get_outcome_weeks(observation_id: int) -> list[int]:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT weeks FROM outcomes WHERE observation_id = {ph}",
            (observation_id,),
        )
        return [int(r[0]) for r in cur.fetchall()]


def get_outcomes_for_observation(observation_id: int) -> list[dict]:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT weeks, price_gbx, pct_change, target_hit, stop_hit, recorded_at
            FROM outcomes WHERE observation_id = {ph}
            ORDER BY weeks ASC
            """,
            (observation_id,),
        )
        rows = cur.fetchall()
    return [
        {
            "weeks": r[0],
            "price_gbx": r[1],
            "pct_change": r[2],
            "target_hit": r[3],
            "stop_hit": r[4],
            "recorded_at": r[5],
        }
        for r in rows
    ]


def insert_outcome(
    observation_id: int,
    candidate_id: int | None,
    weeks: int,
    price_gbx: float,
    pct_change: float,
    target_hit: int,
    stop_hit: int,
) -> None:
    ph = get_placeholder()
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.cursor().execute(
            f"""
            INSERT INTO outcomes
                (observation_id, candidate_id, weeks, price_gbx, pct_change,
                 target_hit, stop_hit, recorded_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                observation_id,
                candidate_id,
                weeks,
                price_gbx,
                pct_change,
                target_hit,
                stop_hit,
                now,
            ),
        )


def get_pattern_stats() -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT pattern_type, sample_count, hit_count, avg_gain_pct, avg_weeks, last_updated
            FROM pattern_stats
            ORDER BY sample_count DESC
            """
        )
        rows = cur.fetchall()
    return [
        {
            "pattern_type": r[0],
            "sample_count": r[1],
            "hit_count": r[2],
            "avg_gain_pct": r[3],
            "avg_weeks": r[4],
            "last_updated": r[5],
        }
        for r in rows
    ]


def upsert_pattern_stats(stat: Any) -> None:
    ph = get_placeholder()
    now = datetime.utcnow().isoformat()
    sql = f"""
        INSERT INTO pattern_stats
            (pattern_type, sample_count, hit_count, avg_gain_pct, avg_weeks, last_updated)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ON CONFLICT (pattern_type) DO UPDATE SET
            sample_count = excluded.sample_count,
            hit_count = excluded.hit_count,
            avg_gain_pct = excluded.avg_gain_pct,
            avg_weeks = excluded.avg_weeks,
            last_updated = excluded.last_updated
    """
    with get_connection() as conn:
        conn.cursor().execute(
            sql,
            (
                stat.pattern_type,
                stat.sample_count,
                stat.hit_count,
                stat.avg_gain_pct,
                stat.avg_weeks,
                now,
            ),
        )


def get_candidates_for_scan(scan_date: date, limit: int = 10, include_id: bool = False) -> list[dict]:
    ph = get_placeholder()
    cols = "id, ticker, rank, composite_score, features_json" if include_id else "ticker, rank, composite_score, features_json"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT {cols}
            FROM candidates
            WHERE scan_date = {ph}
            ORDER BY rank ASC
            LIMIT {ph}
            """,
            (scan_date.isoformat(), limit),
        )
        rows = cur.fetchall()
    if include_id:
        return [
            {
                "id": r[0],
                "ticker": r[1],
                "rank": r[2],
                "composite_score": r[3],
                "features_json": r[4],
            }
            for r in rows
        ]
    return [
        {
            "ticker": r[0],
            "rank": r[1],
            "composite_score": r[2],
            "features_json": r[3],
        }
        for r in rows
    ]


def get_shadow_candidates_pending() -> list[dict]:
    """Shadow-logged candidates without 8-week outcomes yet."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.scan_date, c.ticker, c.composite_score, c.features_json
            FROM candidates c
            WHERE NOT EXISTS (
                SELECT 1 FROM outcomes o
                WHERE o.candidate_id = c.id AND o.weeks = 8
            )
            ORDER BY c.scan_date ASC
            """
        )
        rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "scan_date": r[1],
            "ticker": r[2],
            "composite_score": r[3],
            "features_json": r[4],
        }
        for r in rows
    ]


def get_candidate_outcome_weeks(candidate_id: int) -> list[int]:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT weeks FROM outcomes WHERE candidate_id = {ph}",
            (candidate_id,),
        )
        return [int(r[0]) for r in cur.fetchall()]


def get_price_on_date(ticker: str, on_date: date) -> float | None:
    """Exact close on date, or None."""
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT close_gbx FROM daily_prices WHERE ticker = {ph} AND date = {ph}",
            (ticker, on_date.isoformat()),
        )
        row = cur.fetchone()
    return float(row[0]) if row else None


def get_daily_prices_df(ticker: str, limit: int = 180) -> pd.DataFrame:
    """Recent OHLCV from DB as a DataFrame indexed by date."""
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT date, open_gbx, high_gbx, low_gbx, close_gbx, volume
            FROM daily_prices
            WHERE ticker = {ph}
            ORDER BY date DESC
            LIMIT {ph}
            """,
            (ticker, limit),
        )
        rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        rows,
        columns=["Date", "Open", "High", "Low", "Close", "Volume"],
    )
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").set_index("Date")


def get_observations_with_outcomes(limit: int = 200) -> list[dict]:
    """Observations enriched with 8-week outcome for similarity search."""
    obs_list = get_observations(limit=limit)
    for obs in obs_list:
        outcomes = get_outcomes_for_observation(int(obs["id"]))
        o8 = next((o for o in outcomes if o["weeks"] == 8), None)
        obs["outcome_8w_pct"] = o8["pct_change"] if o8 else None
        obs["outcome_8w_hit"] = bool(o8["target_hit"]) if o8 else None
    return obs_list


def get_scan_summary() -> dict:
    """Latest scan run stats for dashboard home."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status, stocks_processed, stocks_quarantined, finished_at
            FROM scan_runs ORDER BY id DESC LIMIT 1
            """
        )
        run = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM observations")
        obs_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM outcomes WHERE weeks = 8")
        outcome_count = cur.fetchone()[0]
    scan_date = get_latest_candidate_scan()
    return {
        "last_run_status": run[0] if run else None,
        "processed": run[1] if run else 0,
        "quarantined": run[2] if run else 0,
        "finished_at": run[3] if run else None,
        "latest_scan_date": scan_date.isoformat() if scan_date else None,
        "observation_count": obs_count,
        "outcome_8w_count": outcome_count,
    }


def save_model_version(
    version: str,
    sample_count: int,
    cv_score: float,
    artifact_path: str,
    features_json: str,
) -> None:
    ph = get_placeholder()
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.cursor().execute(
            f"""
            INSERT INTO model_versions
                (version, trained_at, sample_count, cv_score, artifact_path, features_json)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (version, now, sample_count, cv_score, artifact_path, features_json),
        )


def get_latest_model_version() -> dict | None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT version, trained_at, sample_count, cv_score, artifact_path, features_json
            FROM model_versions ORDER BY id DESC LIMIT 1
            """
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "version": row[0],
        "trained_at": row[1],
        "sample_count": row[2],
        "cv_score": row[3],
        "artifact_path": row[4],
        "features_json": row[5],
    }


def count_outcomes_since_model_train() -> int:
    latest = get_latest_model_version()
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        if latest and latest.get("trained_at"):
            cur.execute(
                f"SELECT COUNT(*) FROM outcomes WHERE weeks = 8 AND recorded_at > {ph}",
                (latest["trained_at"],),
            )
        else:
            cur.execute("SELECT COUNT(*) FROM outcomes WHERE weeks = 8")
        return int(cur.fetchone()[0])


def scan_completed_today() -> bool:
    """True if a successful scan already finished today (UK date)."""
    from zoneinfo import ZoneInfo

    from db.connection import get_database_url

    today = datetime.now(ZoneInfo("Europe/London")).date()
    ph = get_placeholder()
    url = get_database_url()
    with get_connection() as conn:
        cur = conn.cursor()
        if url and (url.startswith("postgresql") or url.startswith("postgres")):
            cur.execute(
                f"""
                SELECT 1 FROM scan_runs
                WHERE status = 'success' AND finished_at::date = {ph}::date
                LIMIT 1
                """,
                (today.isoformat(),),
            )
        else:
            cur.execute(
                f"""
                SELECT 1 FROM scan_runs
                WHERE status = 'success' AND date(finished_at) = {ph}
                LIMIT 1
                """,
                (today.isoformat(),),
            )
        row = cur.fetchone()
    return row is not None


def upsert_holdings(rows: list, source: str = "ii_csv") -> int:
    """Replace holdings from an import source."""
    ph = get_placeholder()
    now = datetime.now(timezone.utc).isoformat()
    sql = f"""
        INSERT INTO holdings (ticker, name, quantity, avg_cost_gbx, source, imported_at)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ON CONFLICT (ticker, source) DO UPDATE SET
            name = excluded.name,
            quantity = excluded.quantity,
            avg_cost_gbx = excluded.avg_cost_gbx,
            imported_at = excluded.imported_at
    """
    tuples = [
        (r.ticker, r.name, r.quantity, r.avg_cost_gbx, source, now) for r in rows
    ]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM holdings WHERE source = {ph}", (source,))
        _execute_many(conn, sql, tuples)
    return len(tuples)


def get_holdings(source: str = "ii_csv") -> list[dict]:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT ticker, name, quantity, avg_cost_gbx, imported_at
            FROM holdings WHERE source = {ph}
            ORDER BY ticker ASC
            """,
            (source,),
        )
        rows = cur.fetchall()
    return [
        {
            "ticker": r[0],
            "name": r[1],
            "quantity": r[2],
            "avg_cost_gbx": r[3],
            "imported_at": r[4],
        }
        for r in rows
    ]


def get_holdings_tickers(source: str = "ii_csv") -> list[str]:
    return [h["ticker"] for h in get_holdings(source)]


def get_recent_shadow_tickers(limit: int = 15) -> list[str]:
    """Top shadow-logged candidates from the latest scan."""
    scan_date = get_latest_candidate_scan()
    if not scan_date:
        return []
    rows = get_candidates_for_scan(scan_date, limit=limit)
    return [r["ticker"] for r in rows]


def count_universe_tiers() -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM universe_tiers")
        row = cur.fetchone()
    return int(row[0]) if row else 0


def get_universe_tiers_map() -> dict[str, dict]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ticker, tier, filter_reason, last_checked, next_check_after
            FROM universe_tiers
            """
        )
        rows = cur.fetchall()
    return {
        r[0]: {
            "tier": r[1],
            "filter_reason": r[2],
            "last_checked": r[3],
            "next_check_after": r[4],
        }
        for r in rows
    }


def upsert_universe_tiers(rows: list[tuple]) -> int:
    """Rows: (ticker, tier, filter_reason, last_checked, next_check_after)."""
    if not rows:
        return 0
    ph = get_placeholder()
    now = datetime.now(timezone.utc).isoformat()
    sql = f"""
        INSERT INTO universe_tiers
            (ticker, tier, filter_reason, last_checked, next_check_after, updated_at)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ON CONFLICT (ticker) DO UPDATE SET
            tier = excluded.tier,
            filter_reason = excluded.filter_reason,
            last_checked = excluded.last_checked,
            next_check_after = excluded.next_check_after,
            updated_at = excluded.updated_at
    """
    tuples = [(*row, now) for row in rows]
    with get_connection() as conn:
        _execute_many(conn, sql, tuples)
    return len(tuples)


def record_api_usage(
    provider: str,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    estimated_cost_usd: float,
) -> None:
    ph = get_placeholder()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.cursor().execute(
            f"""
            INSERT INTO api_usage
                (provider, model, input_tokens, output_tokens, estimated_cost_usd, recorded_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (provider, model, input_tokens, output_tokens, estimated_cost_usd, now),
        )


def get_api_usage_summary(provider: str = "anthropic") -> dict:
    """Month-to-date and lifetime estimated spend (USD)."""
    from zoneinfo import ZoneInfo

    uk = ZoneInfo("Europe/London")
    now = datetime.now(uk)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start_iso = month_start.isoformat()
    empty = {
        "month_usd": 0.0,
        "month_calls": 0,
        "month_input_tokens": 0,
        "month_output_tokens": 0,
        "lifetime_usd": 0.0,
        "lifetime_calls": 0,
        "lifetime_input_tokens": 0,
        "lifetime_output_tokens": 0,
        "month_label": now.strftime("%B %Y"),
    }

    ph = get_placeholder()
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT COALESCE(SUM(estimated_cost_usd), 0), COALESCE(SUM(input_tokens), 0),
                       COALESCE(SUM(output_tokens), 0), COUNT(*)
                FROM api_usage WHERE provider = {ph} AND recorded_at >= {ph}
                """,
                (provider, month_start_iso),
            )
            month_row = cur.fetchone()
            cur.execute(
                f"""
                SELECT COALESCE(SUM(estimated_cost_usd), 0), COALESCE(SUM(input_tokens), 0),
                       COALESCE(SUM(output_tokens), 0), COUNT(*)
                FROM api_usage WHERE provider = {ph}
                """,
                (provider,),
            )
            life_row = cur.fetchone()
    except Exception:
        return empty

    return {
        "month_usd": round(float(month_row[0]), 4),
        "month_calls": int(month_row[3]),
        "month_input_tokens": int(month_row[1]),
        "month_output_tokens": int(month_row[2]),
        "lifetime_usd": round(float(life_row[0]), 4),
        "lifetime_calls": int(life_row[3]),
        "lifetime_input_tokens": int(life_row[1]),
        "lifetime_output_tokens": int(life_row[2]),
        "month_label": now.strftime("%B %Y"),
    }
