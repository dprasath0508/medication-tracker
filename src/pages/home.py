"""/ — landing router. Redirects based on auth + onboarding state."""

from __future__ import annotations

import streamlit as st

from utils.session import init_session_state, current_user, switch_to


def render() -> None:
    init_session_state()
    user = current_user()

    if user is None:
        try:
            switch_to("auth")
        except KeyError:
            _fallback("/auth")
        return

    if not st.session_state.get("onboarding_complete"):
        _fallback("/onboarding")
        return

    if user.get("type") == "patient":
        _fallback("/today")
    else:
        _fallback("/dashboard")


def _fallback(path: str) -> None:
    """When ``st.switch_page`` isn't available (or fails), render an inline redirect."""
    st.markdown(
        f'<meta http-equiv="refresh" content="0; url={path}">'
        f'<p class="muted">Redirecting to <a href="{path}">{path}</a>…</p>',
        unsafe_allow_html=True,
    )
