"""
UK Stock Analyzer — FastAPI + HTMX web app (v2 primary UI).

Run locally:
  python -m uvicorn webapp.main:app --reload --reload-dir webapp --reload-dir src --reload-dir config
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from webapp.deps import app_password, ensure_ready

ensure_ready()

from config.loader import load_config  # noqa: E402
from data.ii_import import parse_ii_csv  # noqa: E402
from db.repositories import (  # noqa: E402
    get_analysis_note,
    get_analysis_notes,
    get_candidates_for_scan,
    get_feedback_summary,
    get_holdings,
    get_holdings_tickers,
    get_latest_candidate_scan,
    get_latest_price_gbx,
    get_scan_summary,
    get_shadow_hit_rates,
    get_shortlist_feedback_map,
    get_stock_name,
    insert_analysis_note,
    update_analysis_critique,
    upsert_holdings,
    upsert_shortlist_feedback,
)
from intelligence.coaching import critique_user_analysis  # noqa: E402
from intelligence.why_chosen import enrich_why_with_live_catalyst  # noqa: E402
from intelligence.ml_model import get_feature_importance, load_model_bundle, predict_probability  # noqa: E402
from intelligence.usage_tracking import usage_display  # noqa: E402
from visualization.charts import (  # noqa: E402
    TIMEFRAMES,
    chart_series,
    score_breakdown_rows,
)
from visualization.links import research_links  # noqa: E402


def _normalise_ticker(raw: str) -> str:
    t = (raw or "").strip().upper()
    if not t:
        return ""
    if not t.endswith(".L"):
        t = f"{t}.L"
    return t


def _chart_tf(raw: str | None) -> str:
    tf = (raw or "Daily").strip().title()
    return tf if tf in TIMEFRAMES else "Daily"

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

app = FastAPI(title="UK Stock Analyzer", docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", os.getenv("APP_PASSWORD", "dev-secret-change-me")),
)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

UK = ZoneInfo("Europe/London")


def _authed(request: Request) -> bool:
    pwd = app_password()
    if not pwd:
        return True
    return bool(request.session.get("authenticated"))


def require_auth(request: Request) -> None:
    if not _authed(request):
        raise _LoginRedirect()


class _LoginRedirect(Exception):
    pass


@app.exception_handler(_LoginRedirect)
async def _login_redirect(_request: Request, _exc: _LoginRedirect):
    return RedirectResponse("/login", status_code=303)


def _render(request: Request, template: str, status_code: int = 200, **extra):
    """Starlette 1.3+: TemplateResponse(request, name, context)."""
    return templates.TemplateResponse(
        request,
        template,
        {"authed": _authed(request), **extra},
        status_code=status_code,
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _authed(request):
        return RedirectResponse("/", status_code=303)
    return _render(request, "login.html", error=None)


@app.post("/login")
async def login_submit(request: Request, password: Annotated[str, Form()] = ""):
    expected = app_password()
    if not expected or password == expected:
        request.session["authenticated"] = True
        return RedirectResponse("/", status_code=303)
    return _render(request, "login.html", status_code=401, error="Incorrect password")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, _: None = Depends(require_auth)):
    summary = get_scan_summary()
    usage = usage_display()
    bundle = load_model_bundle()
    ml_cfg = load_config().get("ml", {})
    need = int(ml_cfg.get("min_samples_logistic", 100))
    have = int(summary.get("outcome_8w_count", 0) or 0)
    hour = int(load_config().get("schedule", {}).get("results_by_hour_uk", 7))
    now = datetime.now(UK)
    hit_rates = get_shadow_hit_rates()
    feedback = get_feedback_summary()
    return _render(
        request,
        "home.html",
        summary=summary,
        usage=usage,
        bundle=bundle,
        ml_need=need,
        ml_have=have,
        results_by=hour,
        now_uk=now.strftime("%Y-%m-%d %H:%M %Z"),
        hit_rates=hit_rates,
        feedback=feedback,
        app_url=os.getenv("APP_BASE_URL", "").rstrip("/"),
    )


@app.get("/shortlist", response_class=HTMLResponse)
async def shortlist(request: Request, _: None = Depends(require_auth)):
    scan_date = get_latest_candidate_scan()
    rows = []
    flash = request.query_params.get("msg")
    if scan_date:
        model_active = load_model_bundle() is not None
        held = {t.upper() for t in get_holdings_tickers()}
        feedback_map = get_shortlist_feedback_map(scan_date)
        for c in get_candidates_for_scan(scan_date, limit=10):
            features = {}
            try:
                features = json.loads(c.get("features_json") or "{}")
            except json.JSONDecodeError:
                pass
            why = features.get("why_chosen") or {}
            name = why.get("name") or features.get("company_name") or c["ticker"]
            ml_prob = None
            if model_active:
                ml_prob = predict_probability(features).probability
            ticker = c["ticker"]
            why = enrich_why_with_live_catalyst(ticker, why)
            support = features.get("distance_support_pct")
            try:
                if support is not None and float(support) != float(support):
                    support = None
            except (TypeError, ValueError):
                support = None
            rows.append(
                {
                    "rank": c["rank"],
                    "ticker": ticker,
                    "name": name or ticker,
                    "score": c["composite_score"],
                    "support": support,
                    "confluence": features.get("confluence", 0),
                    "conflict": bool(features.get("conflict_flag")),
                    "ml": ml_prob,
                    "links": research_links(ticker),
                    "why_bullets": why.get("bullets") or [],
                    "already_held": ticker.upper() in held,
                    "price_gbx": get_latest_price_gbx(ticker),
                    "verdict": feedback_map.get(ticker),
                }
            )
    return _render(
        request,
        "shortlist.html",
        scan_date=scan_date,
        active_rows=[r for r in rows if r.get("verdict") != "drop"],
        dropped_rows=[r for r in rows if r.get("verdict") == "drop"],
        flash=flash,
        show_dropped=request.query_params.get("show_dropped") == "1",
    )


@app.post("/shortlist/feedback")
async def shortlist_feedback(
    request: Request,
    ticker: Annotated[str, Form()] = "",
    verdict: Annotated[str, Form()] = "",
    scan_date: Annotated[str, Form()] = "",
    _: None = Depends(require_auth),
):
    from datetime import date as date_cls

    ticker = _normalise_ticker(ticker) or ticker.strip().upper()
    if not ticker or verdict not in ("keep", "drop") or not scan_date:
        return RedirectResponse("/shortlist", status_code=303)
    try:
        sd = date_cls.fromisoformat(scan_date[:10])
    except ValueError:
        return RedirectResponse("/shortlist", status_code=303)
    try:
        upsert_shortlist_feedback(sd, ticker, verdict)
    except Exception:
        # Table may not exist yet on old DB — init_database on next boot should add it
        from db.connection import init_database

        init_database()
        upsert_shortlist_feedback(sd, ticker, verdict)
    label = "Dropped (hidden from list)" if verdict == "drop" else "Kept"
    return RedirectResponse(
        f"/shortlist?msg={label}:+{ticker}",
        status_code=303,
    )


@app.get("/lookup", response_class=HTMLResponse)
async def lookup_page(request: Request, _: None = Depends(require_auth)):
    q = request.query_params.get("ticker", "")
    ticker = _normalise_ticker(q)
    if ticker:
        return RedirectResponse(f"/stock/{ticker}", status_code=303)
    return _render(request, "lookup.html", error=None)


@app.get("/stock/{ticker}", response_class=HTMLResponse)
async def stock_detail(request: Request, ticker: str, _: None = Depends(require_auth)):
    ticker = _normalise_ticker(ticker) or ticker.upper()
    tf = _chart_tf(request.query_params.get("tf"))
    scan_date = get_latest_candidate_scan()
    features: dict = {}
    score = None
    why = {}
    if scan_date:
        for c in get_candidates_for_scan(scan_date, limit=15):
            if c["ticker"].upper() == ticker.upper():
                score = c["composite_score"]
                try:
                    features = json.loads(c.get("features_json") or "{}")
                except json.JSONDecodeError:
                    features = {}
                why = enrich_why_with_live_catalyst(
                    ticker, features.get("why_chosen") or {}
                )
                break
    why = enrich_why_with_live_catalyst(ticker, why)
    name = why.get("name") or features.get("company_name") or get_stock_name(ticker)
    candles, volumes = chart_series(ticker, timeframe=tf)
    notes = get_analysis_notes(limit=10, ticker=ticker)
    ml = predict_probability(features)
    breakdown = score_breakdown_rows(features) if features else []
    return _render(
        request,
        "stock.html",
        ticker=ticker,
        name=name or ticker,
        score=score,
        why=why,
        features=features,
        breakdown=breakdown,
        candles_json=json.dumps(candles),
        volumes_json=json.dumps(volumes),
        timeframe=tf,
        timeframes=list(TIMEFRAMES.keys()),
        links=research_links(ticker),
        notes=notes,
        ml=ml,
        scan_date=scan_date,
    )


@app.post("/stock/{ticker}/analyse")
async def stock_analyse(
    request: Request,
    ticker: str,
    notes: Annotated[str, Form()] = "",
    agree: Annotated[str, Form()] = "",
    _: None = Depends(require_auth),
):
    if not notes.strip():
        return RedirectResponse(f"/stock/{ticker}", status_code=303)
    scan_date = get_latest_candidate_scan()
    note_id = insert_analysis_note(
        ticker=ticker,
        user_notes=notes.strip(),
        agree_with_system=agree or None,
        scan_date=scan_date,
    )
    features: dict = {}
    why_bullets: list[str] = []
    name = get_stock_name(ticker)
    if scan_date:
        for c in get_candidates_for_scan(scan_date, limit=15):
            if c["ticker"].upper() == ticker.upper():
                try:
                    features = json.loads(c.get("features_json") or "{}")
                except json.JSONDecodeError:
                    features = {}
                why = features.get("why_chosen") or {}
                why_bullets = why.get("bullets") or []
                name = why.get("name") or name
                break
    feat_summary = json.dumps(
        {
            k: features.get(k)
            for k in (
                "support_score",
                "distance_support_pct",
                "confluence",
                "conflict_flag",
                "catalyst_score",
                "analyst_upside_score",
                "news_sentiment_score",
            )
        },
        indent=2,
    )
    critique, _src = critique_user_analysis(
        ticker=ticker,
        company_name=name,
        why_bullets=why_bullets,
        user_notes=notes.strip(),
        agree_with_system=agree or None,
        features_summary=feat_summary,
    )
    model = load_config().get("anthropic", {}).get("model", "claude-haiku-4-5-20251001")
    update_analysis_critique(note_id, critique, model)
    return RedirectResponse(f"/stock/{ticker}#notes", status_code=303)


@app.get("/holdings", response_class=HTMLResponse)
async def holdings_page(request: Request, _: None = Depends(require_auth)):
    holdings = get_holdings()
    table = []
    for h in holdings:
        latest = get_latest_price_gbx(h["ticker"])
        cost = h.get("avg_cost_gbx")
        qty = float(h.get("quantity") or 0)
        pnl = None
        if latest and cost and cost > 0:
            pnl = (latest - cost) / cost * 100
        table.append(
            {
                **h,
                "latest": latest,
                "pnl": pnl,
                "value": latest * qty if latest else None,
            }
        )
    return _render(request, "holdings.html", table=table, message=None, preview=None)


@app.post("/holdings/import")
async def holdings_import(request: Request, _: None = Depends(require_auth)):
    form = await request.form()
    upload = form.get("file")
    if not upload:
        return RedirectResponse("/holdings", status_code=303)
    content = await upload.read()
    rows = parse_ii_csv(content)
    n = upsert_holdings(rows)
    holdings = get_holdings()
    table = []
    for h in holdings:
        latest = get_latest_price_gbx(h["ticker"])
        cost = h.get("avg_cost_gbx")
        qty = float(h.get("quantity") or 0)
        pnl = None
        if latest and cost and cost > 0:
            pnl = (latest - cost) / cost * 100
        table.append({**h, "latest": latest, "pnl": pnl, "value": latest * qty if latest else None})
    return _render(
        request,
        "holdings.html",
        table=table,
        message=f"Saved {n} holdings.",
        preview=[(r.ticker, r.name, r.quantity) for r in rows],
    )


@app.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request, _: None = Depends(require_auth)):
    ticker_q = request.query_params.get("ticker") or None
    if ticker_q:
        ticker_q = _normalise_ticker(ticker_q) or ticker_q.upper()
    awaiting = request.query_params.get("awaiting") in ("1", "true", "yes")
    notes = get_analysis_notes(
        limit=100, ticker=ticker_q, awaiting_critique=awaiting
    )
    return _render(
        request,
        "notes.html",
        notes=notes,
        filter_ticker=ticker_q or "",
        awaiting=awaiting,
    )


@app.get("/ml", response_class=HTMLResponse)
async def ml_page(request: Request, _: None = Depends(require_auth)):
    summary = get_scan_summary()
    bundle = load_model_bundle()
    ml_cfg = load_config().get("ml", {})
    need = int(ml_cfg.get("min_samples_logistic", 100))
    have = int(summary.get("outcome_8w_count", 0) or 0)
    hit_rates = get_shadow_hit_rates()
    importance = get_feature_importance() or {}
    feedback = get_feedback_summary()
    return _render(
        request,
        "ml.html",
        need=need,
        have=have,
        bundle=bundle,
        hit_rates=hit_rates,
        importance=importance,
        summary=summary,
        feedback=feedback,
    )


@app.get("/health")
async def health():
    return {"ok": True}
