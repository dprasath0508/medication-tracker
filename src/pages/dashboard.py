"""Dashboard page — split from the original monolithic web_app.py.

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


def show_family_dashboard():
    """Display family overview dashboard with user's real data."""
    db, family_manager = init_database()
    user = st.session_state.user_profile

    st.markdown('<h1 class="main-header">Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="welcome-subheader">Welcome back, {user["name"]}</p>',
        unsafe_allow_html=True,
    )

    if user["type"] == "patient":
        st.markdown(
            """
        <style>
            .todays-meds-card {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .todays-meds-title {
                color: var(--text);
                font-size: 1rem;
                font-weight: 600;
                margin: 0 0 0.25rem 0;
                letter-spacing: -0.01em;
            }
            .todays-meds-subtitle {
                color: var(--text-muted);
                font-size: 0.875rem;
                margin: 0;
            }
        </style>
        """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                """
            <div class="todays-meds-card">
                <div>
                    <p class="todays-meds-title">Today's medications</p>
                    <p class="todays-meds-subtitle">Check off your medications as you take them</p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
            if st.button(
                "Open", key="go_todays_meds", use_container_width=True, type="primary"
            ):
                st.session_state.show_medication_logging = True
                st.rerun()

        st.markdown("---")

        # Get user's family circles
    user_circles = db.get_user_family_circles(user["id"])

    if not user_circles:
        # Empty state - no family circles
        st.markdown(
            """
 <div class="empty-state">
 <h3> No Family Circles Yet</h3>
 <p>Create your first family circle to start monitoring medications and connecting with family members.</p>
 </div>
 """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "Create Your First Family Circle",
                key="create_first",
                use_container_width=True,
            ):
                st.session_state.show_create_circle = True
                st.rerun()

        return

        # Get dashboard data for the user
    dashboard_data = family_manager.get_family_dashboard_data(user["id"])

    if dashboard_data["total_patients"] == 0:
        # Has circles but no patients
        st.markdown("## Your Family Circles")
        for circle in user_circles:
            st.markdown(f"### {circle['name']}")
            st.info(
                f"**Invite Code:** `{circle['invite_code']}` - Share this with family members"
            )

        st.markdown(
            """
 <div class="empty-state">
 <h3> No Patients Added Yet</h3>
 <p>Add elderly family members to start tracking their medications and health progress.</p>
 </div>
 """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "Add Your First Patient",
                key="add_first_patient",
                use_container_width=True,
            ):
                st.session_state.show_add_patient = True
                st.rerun()

        return

        # Show full dashboard with data
        # Overview metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="Patients Monitoring", value=dashboard_data["total_patients"])

    with col2:
        adherence = dashboard_data["average_adherence"]
        color = "" if adherence >= 90 else "" if adherence >= 70 else ""
        st.metric(
            label=f"{color} Average Adherence",
            value=f"{adherence}%" if adherence > 0 else "No data",
        )

    with col3:
        st.metric(
            label="Need Attention", value=dashboard_data["patients_needing_attention"]
        )

    with col4:
        st.metric(
            label="‍‍‍ Family Circles", value=len(dashboard_data["family_circles"])
        )

        # Alerts section
    if dashboard_data["alerts"]:
        st.markdown("## Alerts & Notifications")
        for alert in dashboard_data["alerts"]:
            if "low medication adherence" in alert:
                st.markdown(
                    f'<div class="alert-warning">{alert}</div>', unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="alert-success">{alert}</div>', unsafe_allow_html=True
                )

                # Patient status cards
    st.markdown("## Patient Status Overview")

    for patient in dashboard_data["patients_status"]:
        with st.expander(
            f"{patient['name']} ({patient['age']} years old)", expanded=True
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Medications", patient["total_medications"])

            with col2:
                adherence = patient["adherence_rate"]
                color = "" if adherence >= 90 else "" if adherence >= 70 else ""
                st.metric(
                    f"{color} Adherence",
                    f"{adherence:.1f}%" if adherence > 0 else "No data",
                )

            with col3:
                st.metric("Family Circle", patient["family_circle_name"])

                # Get patient's medications
            medications = db.get_patient_medications(patient["id"])

            if medications:
                st.markdown("**Current Medications:**")
                med_data = []
                for med in medications:
                    med_data.append(
                        {
                            "Medication": med["name"],
                            "Dosage": med["dosage"],
                            "Times": ", ".join(med["times"]),
                            "Notes": med["notes"] or "None",
                        }
                    )

                st.dataframe(pd.DataFrame(med_data), use_container_width=True)
            else:
                st.info("No medications added yet for this patient.")

                # Quick actions
            st.markdown("**Quick Actions:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"View Details", key=f"details_{patient['id']}"):
                    st.session_state["selected_patient"] = patient["id"]
                    st.rerun()

            with col2:
                if st.button(f"Add Medication", key=f"add_med_{patient['id']}"):
                    st.session_state["add_medication_for"] = patient["id"]
                    st.rerun()

            with col3:
                if st.button(f"Log Doses", key=f"log_{patient['id']}"):
                    st.session_state["show_medication_logging"] = True
                    st.rerun()




def render() -> None:
    init_session_state()
    show_family_dashboard()
