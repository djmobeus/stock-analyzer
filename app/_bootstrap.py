"""Add src/ to path and load environment for Streamlit pages."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config.loader import load_env  # noqa: E402
from db.connection import init_database  # noqa: E402


def _ensure_page_config() -> None:
    import streamlit as st

    if st.session_state.get("_page_config_done"):
        return
    try:
        st.set_page_config(
            page_title="UK Stock Analyzer",
            page_icon="📈",
            layout="wide",
        )
    except Exception:
        pass
    st.session_state["_page_config_done"] = True


def _load_streamlit_secrets() -> None:
    """Copy Streamlit Cloud secrets into environment variables."""
    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if not secrets:
            return
        for key in (
            "DATABASE_URL",
            "APP_PASSWORD",
            "ANTHROPIC_API_KEY",
            "EMAIL_TO",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "EMAIL_FROM",
        ):
            if key in secrets and not os.getenv(key):
                os.environ[key] = str(secrets[key])
    except Exception:
        pass


def require_login() -> None:
    """Simple password gate when APP_PASSWORD is set in secrets/.env."""
    import streamlit as st

    password = os.getenv("APP_PASSWORD", "").strip()
    if not password:
        return

    if st.session_state.get("authenticated"):
        return

    st.title("UK Stock Analyzer")
    st.caption("Enter your private app password")
    entered = st.text_input("Password", type="password")
    if st.button("Sign in", type="primary"):
        if entered == password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()


def bootstrap() -> None:
    import streamlit as st

    _ensure_page_config()
    load_env()
    _load_streamlit_secrets()
    require_login()
    if st.session_state.get("_schema_ready"):
        return
    try:
        init_database()
        st.session_state["_schema_ready"] = True
    except Exception as exc:
        st.error(
            "Could not connect to the database. Check `DATABASE_URL` in Streamlit secrets "
            f"and that Supabase is reachable. ({exc})"
        )
        st.stop()
