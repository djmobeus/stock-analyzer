"""scikit-learn model training, inference, and persistence."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from config.loader import ROOT_DIR, load_config
from db.connection import get_connection, get_placeholder
from db.repositories import get_latest_model_version, save_model_version

logger = logging.getLogger(__name__)

MODELS_DIR = ROOT_DIR / "data" / "models"
MODEL_PATH = MODELS_DIR / "ml_model.joblib"

FEATURE_KEYS = [
    "support_score",
    "confluence",
    "analyst_upside_score",
    "catalyst_score",
    "news_sentiment_score",
    "market_regime_score",
    "sector_relative_score",
    "distance_support_pct",
    "distance_resistance_pct",
]


@dataclass
class MLResult:
    probability: float | None
    model_version: str | None
    sample_count: int
    reason: str
    feature_importance: dict[str, float] = field(default_factory=dict)


@dataclass
class _ModelBundle:
    model: object
    model_type: str
    feature_keys: list[str]
    sample_count: int
    cv_score: float
    version: str
    trained_at: str


def _features_vector(features: dict) -> list[float]:
    vec = []
    for key in FEATURE_KEYS:
        val = features.get(key)
        if val is None:
            vec.append(0.0)
        else:
            vec.append(float(val))
    if features.get("conflict_flag"):
        vec.append(1.0)
    else:
        vec.append(0.0)
    return vec


def _load_training_rows() -> list[dict]:
    """Labelled rows from user observations and shadow candidates."""
    ph = get_placeholder()
    rows: list[dict] = []

    obs_sql = f"""
        SELECT o.features_json, oc.target_hit, o.observed_at
        FROM observations o
        JOIN outcomes oc ON oc.observation_id = o.id AND oc.weeks = 8
        WHERE o.prediction IN ('buy', 'watch') AND o.features_json IS NOT NULL
    """
    shadow_sql = f"""
        SELECT c.features_json, oc.target_hit, c.scan_date
        FROM candidates c
        JOIN outcomes oc ON oc.candidate_id = c.id AND oc.weeks = 8
        WHERE c.features_json IS NOT NULL
    """

    with get_connection() as conn:
        cur = conn.cursor()
        for sql, date_col in ((obs_sql, "observed_at"), (shadow_sql, "scan_date")):
            cur.execute(sql)
            for feat_json, target_hit, observed in cur.fetchall():
                try:
                    features = json.loads(feat_json or "{}")
                except json.JSONDecodeError:
                    continue
                rows.append(
                    {
                        "features": features,
                        "label": int(target_hit or 0),
                        "date": str(observed)[:10],
                    }
                )
    rows.sort(key=lambda r: r["date"])
    return rows


def _choose_model_type(n: int, config: dict) -> str | None:
    ml = config.get("ml", {})
    if n < int(ml.get("min_samples_logistic", 100)):
        return None
    if n >= int(ml.get("min_samples_forest", 300)):
        return "random_forest"
    return "logistic"


def train_model(force: bool = False) -> dict:
    """Train walk-forward model when enough labelled outcomes exist."""
    config = load_config()
    rows = _load_training_rows()
    n = len(rows)
    model_type = _choose_model_type(n, config)

    if model_type is None:
        return {
            "status": "skipped",
            "reason": "insufficient_samples",
            "sample_count": n,
            "min_required": config.get("ml", {}).get("min_samples_logistic", 100),
        }

    latest = get_latest_model_version()
    if not force and latest and latest.get("sample_count", 0) >= n:
        return {
            "status": "skipped",
            "reason": "no_new_samples",
            "sample_count": n,
        }

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    X = np.array([_features_vector(r["features"]) for r in rows])
    y = np.array([r["label"] for r in rows])

    tscv = TimeSeriesSplit(n_splits=min(5, max(2, n // 20)))
    scores: list[float] = []

    if model_type == "random_forest":
        estimator = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            class_weight="balanced",
        )
        final = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            class_weight="balanced",
        )
    else:
        estimator = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=500, class_weight="balanced")),
            ]
        )
        final = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=500, class_weight="balanced")),
            ]
        )

    for train_idx, test_idx in tscv.split(X):
        estimator.fit(X[train_idx], y[train_idx])
        scores.append(float(estimator.score(X[test_idx], y[test_idx])))

    cv_score = float(np.mean(scores)) if scores else 0.0
    final.fit(X, y)

    version = datetime.now(timezone.utc).strftime("v%Y%m%d_%H%M")
    bundle = _ModelBundle(
        model=final,
        model_type=model_type,
        feature_keys=FEATURE_KEYS + ["conflict_flag"],
        sample_count=n,
        cv_score=cv_score,
        version=version,
        trained_at=datetime.now(timezone.utc).isoformat(),
    )

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)

    importance: dict[str, float] = {}
    keys = FEATURE_KEYS + ["conflict_flag"]
    if model_type == "random_forest":
        imp = getattr(final, "feature_importances_", None)
        if imp is not None:
            importance = {k: round(float(v), 4) for k, v in zip(keys, imp)}
    else:
        clf = final.named_steps["clf"]
        coef = getattr(clf, "coef_", None)
        if coef is not None:
            importance = {k: round(float(v), 4) for k, v in zip(keys, coef[0])}

    save_model_version(
        version=version,
        sample_count=n,
        cv_score=cv_score,
        artifact_path=str(MODEL_PATH),
        features_json=json.dumps({"model_type": model_type, "importance": importance}),
    )

    logger.info("ML model %s trained on %d samples (CV=%.3f)", version, n, cv_score)
    return {
        "status": "trained",
        "version": version,
        "model_type": model_type,
        "sample_count": n,
        "cv_score": round(cv_score, 4),
    }


def load_model_bundle() -> _ModelBundle | None:
    if not MODEL_PATH.exists():
        return None
    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:
        logger.warning("Failed to load model: %s", exc)
        return None


def predict_probability(features: dict) -> MLResult:
    """Return P(target hit) or insufficient-data message."""
    config = load_config()
    ml = config.get("ml", {})
    min_samples = int(ml.get("min_samples_logistic", 100))

    bundle = load_model_bundle()
    if bundle is None:
        rows = _load_training_rows()
        return MLResult(
            probability=None,
            model_version=None,
            sample_count=len(rows),
            reason="insufficient_data",
        )

    if bundle.sample_count < min_samples:
        return MLResult(
            probability=None,
            model_version=bundle.version,
            sample_count=bundle.sample_count,
            reason="insufficient_data",
        )

    vec = np.array([_features_vector(features)]).reshape(1, -1)
    proba = bundle.model.predict_proba(vec)[0][1]

    importance: dict[str, float] = {}
    latest = get_latest_model_version()
    if latest and latest.get("features_json"):
        try:
            meta = json.loads(latest["features_json"])
            importance = meta.get("importance", {})
        except json.JSONDecodeError:
            pass

    return MLResult(
        probability=round(float(proba) * 100, 1),
        model_version=bundle.version,
        sample_count=bundle.sample_count,
        reason="ok",
        feature_importance=importance,
    )


def get_feature_importance() -> dict[str, float]:
    latest = get_latest_model_version()
    if not latest or not latest.get("features_json"):
        return {}
    try:
        meta = json.loads(latest["features_json"])
        return meta.get("importance", {})
    except json.JSONDecodeError:
        return {}
