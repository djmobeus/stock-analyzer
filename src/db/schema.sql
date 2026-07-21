-- UK Stock Analyzer schema
-- Works on SQLite (local) and PostgreSQL/Supabase (cloud)

CREATE TABLE IF NOT EXISTS stocks (
    ticker TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    market_cap_gbp REAL,
    avg_volume REAL,
    is_active INTEGER DEFAULT 1,
    last_updated TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_prices (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    open_gbx REAL,
    high_gbx REAL,
    low_gbx REAL,
    close_gbx REAL,
    adj_close_gbx REAL,
    volume REAL,
    currency_source TEXT,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS technical_indicators (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    timeframe TEXT NOT NULL,
    indicator_name TEXT NOT NULL,
    value REAL,
    metadata TEXT,
    PRIMARY KEY (ticker, date, timeframe, indicator_name)
);

CREATE TABLE IF NOT EXISTS analyst_data (
    ticker TEXT PRIMARY KEY,
    target_mean REAL,
    target_high REAL,
    target_low REAL,
    buy_count INTEGER,
    hold_count INTEGER,
    sell_count INTEGER,
    analyst_count INTEGER,
    last_updated TIMESTAMP
);

CREATE TABLE IF NOT EXISTS catalysts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    event_type TEXT,
    event_date DATE,
    description TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    title TEXT,
    url TEXT UNIQUE,
    published_at TIMESTAMP,
    sentiment_score REAL,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date DATE NOT NULL,
    ticker TEXT NOT NULL,
    rank INTEGER,
    composite_score REAL,
    features_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    observed_at TIMESTAMP NOT NULL,
    entry_price_gbx REAL,
    prediction TEXT,
    confidence TEXT,
    chart_description TEXT,
    features_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER,
    candidate_id INTEGER,
    weeks INTEGER NOT NULL,
    price_gbx REAL,
    pct_change REAL,
    target_hit INTEGER DEFAULT 0,
    stop_hit INTEGER DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pattern_stats (
    pattern_type TEXT PRIMARY KEY,
    sample_count INTEGER,
    hit_count INTEGER,
    avg_gain_pct REAL,
    avg_weeks REAL,
    last_updated TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scan_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT,
    stocks_processed INTEGER,
    stocks_quarantined INTEGER,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS data_quality_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    flag_date DATE NOT NULL,
    flag_type TEXT NOT NULL,
    details TEXT,
    quarantined INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ticker, flag_date, flag_type)
);

CREATE TABLE IF NOT EXISTS model_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT,
    trained_at TIMESTAMP,
    sample_count INTEGER,
    cv_score REAL,
    artifact_path TEXT,
    features_json TEXT
);

CREATE TABLE IF NOT EXISTS config_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date DATE,
    weights_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    name TEXT,
    quantity REAL NOT NULL,
    avg_cost_gbx REAL,
    source TEXT DEFAULT 'ii_csv',
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ticker, source)
);

CREATE TABLE IF NOT EXISTS universe_tiers (
    ticker TEXT PRIMARY KEY,
    tier TEXT NOT NULL,
    filter_reason TEXT,
    last_checked DATE,
    next_check_after DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_universe_tiers_tier ON universe_tiers(tier);

CREATE TABLE IF NOT EXISTS analysis_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    scan_date DATE,
    user_notes TEXT NOT NULL,
    agree_with_system TEXT,
    critique_text TEXT,
    critique_model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_analysis_notes_ticker ON analysis_notes(ticker);

CREATE TABLE IF NOT EXISTS shortlist_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date DATE NOT NULL,
    ticker TEXT NOT NULL,
    verdict TEXT NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scan_date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_shortlist_feedback_scan ON shortlist_feedback(scan_date);

CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    estimated_cost_usd REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_usage_recorded ON api_usage(recorded_at);
CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker ON daily_prices(ticker);
CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices(date);
CREATE INDEX IF NOT EXISTS idx_data_quality_ticker ON data_quality_flags(ticker);
CREATE INDEX IF NOT EXISTS idx_candidates_scan_date ON candidates(scan_date);
