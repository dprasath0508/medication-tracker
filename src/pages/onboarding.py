"""Onboarding page — split from the original monolithic web_app.py.

Behaviour is preserved verbatim from the pre-modernization app. The visual
redesign against ``design-system/MASTER.md`` happens in Commit 4.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from models.family import FamilyCircleManager
from services.auth import AuthService
from services.notifications import NotificationService
from utils.session import (
    db as _db, family_manager as _family_manager,
    auth_service as _auth_service, notification_service as _notification_service,
    init_session_state, current_user, sign_out,
)


def init_database():
    """Compatibility shim — the legacy screens call this expecting (db, family_manager)."""
    return _db(), _family_manager()


def get_auth_service():
    return _auth_service()


def show_getting_started():
    """Show getting started options after profile creation."""
    from ui.primitives import page_shell

    user = st.session_state.user_profile

    page_shell(
        f"Welcome, {user['name']}",
        eyebrow="Getting started",
        subtitle="A couple of choices to make this feel like yours.",
    )

    if user["type"] == "family_member":
        st.markdown("## ‍‍‍ Create Your First Family Circle")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(
                """
 <div class="empty-state">
 <h3> Start Your Family Care Journey</h3>
 <p>Create a family circle to begin monitoring and supporting your loved one's health. You can invite family members and add patients to track their medications together.</p>
 </div>
 """,
                unsafe_allow_html=True,
            )

        with col2:
            if st.button(
                "Create Family Circle", key="create_circle", use_container_width=True
            ):
                st.session_state.show_create_circle = True
                st.rerun()

            st.markdown("**OR**")

            if st.button(
                "Join Existing Circle", key="join_circle", use_container_width=True
            ):
                st.session_state.show_join_circle = True
                st.rerun()

    else:  # patient
        st.markdown("## Set Up Your Medication Profile")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(
                """
 <div class="empty-state">
 <h3> Get Started with Your Health</h3>
 <p>Add your medications and connect with family members who can help support your health journey. They'll be able to monitor your progress and provide assistance when needed.</p>
 </div>
 """,
                unsafe_allow_html=True,
            )

        with col2:
            if st.button(
                "Add My Medications", key="add_medications", use_container_width=True
            ):
                st.session_state.show_add_patient_medication = True
                st.rerun()

            st.markdown("**OR**")

            if st.button(
                "‍‍‍ Connect with Family",
                key="connect_family",
                use_container_width=True,
            ):
                st.session_state.show_join_circle = True
                st.rerun()




def render() -> None:
    init_session_state()
    show_getting_started()
