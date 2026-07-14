"""Session-level singletons and helpers shared across all pages.

Wraps DB, auth service, and notification service in Streamlit's cache to avoid
re-instantiating on every rerun (perf), and centralises initial session state
so every page starts from a known baseline.
"""

from __future__ import annotations

import streamlit as st

from models.family import FamilyCircleManager
from services.auth import AuthService
from services.notifications import NotificationService
from utils.db_factory import get_database


@st.cache_resource(show_spinner=False)
def _db_singleton():
    return get_database()


@st.cache_resource(show_spinner=False)
def _notification_service_singleton():
    return NotificationService()


@st.cache_resource(show_spinner=False)
def _family_manager_singleton():
    return FamilyCircleManager(_db_singleton())


@st.cache_resource(show_spinner=False)
def _auth_service_singleton():
    return AuthService(_db_singleton(), _notification_service_singleton())


def db():
    return _db_singleton()


def family_manager():
    return _family_manager_singleton()


def auth_service():
    return _auth_service_singleton()


def notification_service():
    return _notification_service_singleton()


def init_session_state() -> None:
    """Ensure baseline keys exist on session_state. Idempotent."""
    defaults = {
        "user_profile": None,
        "onboarding_complete": False,
        "family_circles": [],
        "show_login": True,
        "show_register": False,
        "auth_step": "phone",
        "auth_phone": None,
        "otp_sent_time": None,
        "session_token": None,
        "snoozed_meds": {},
        "theme": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def current_user() -> dict | None:
    """Return the logged-in user profile or None."""
    return st.session_state.get("user_profile")


def is_authenticated() -> bool:
    return current_user() is not None


def sign_out() -> None:
    """Clear all session state related to the user's session, keeping the DB caches."""
    token = st.session_state.get("session_token")
    if token:
        try:
            auth_service().logout(token)
        except Exception:
            pass
    for key in list(st.session_state.keys()):
        if key in {"theme"}:
            continue
        del st.session_state[key]
    init_session_state()
