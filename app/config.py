import os

import streamlit as st


def _get_setting(key: str, default: str) -> str:
    # Local dev / Render-style env vars first (this already worked).
    if key in os.environ:
        return os.environ[key]
    # Streamlit Community Cloud's secrets don't always surface as plain
    # env vars, so fall back to st.secrets — but accessing it at all
    # raises StreamlitSecretNotFoundError when no secrets.toml exists
    # anywhere (confirmed locally: even .get() doesn't protect against
    # this, since the error isn't a KeyError), so this must stay wrapped.
    try:
        return st.secrets[key]
    except Exception:
        return default


API_BASE_URL = _get_setting("API_BASE_URL", "http://localhost:8000")
