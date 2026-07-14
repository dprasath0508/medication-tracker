"""Patient page — split from the original monolithic web_app.py.

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


def show_patient_details():
    """Show detailed view for a specific patient."""
    if "selected_patient" not in st.session_state:
        return

    db, family_manager = init_database()
    patient_id = st.session_state["selected_patient"]

    # Get patient info
    users = db.get_users()
    patient = next((u for u in users if u["id"] == patient_id), None)

    if not patient:
        st.error("Patient not found")
        return

    from ui.primitives import page_shell
    page_shell(
        patient["name"],
        eyebrow="Patient",
        subtitle=f"Age {patient.get('age', '—')} · {patient.get('role', '').title()}",
    )

    if st.button("Back to dashboard", key="patient_back"):
        del st.session_state["selected_patient"]
        st.query_params.clear()
        if hasattr(st, "switch_page"):
            st.switch_page("pages/dashboard.py")
        else:
            st.rerun()

        # Create adherence chart
    st.markdown("## 7-Day Adherence Trend")

    # Get real adherence data from database
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute(
            """
            SELECT date, 
                   COUNT(*) as total,
                   SUM(taken) as taken
            FROM dose_logs
            WHERE patient_id = ? AND date >= date('now', '-7 days')
            GROUP BY date
            ORDER BY date
        """,
            (patient_id,),
        )

        logs = cursor.fetchall()

    if logs:
        dates = [datetime.fromisoformat(log[0]) for log in logs]
        adherence_data = [(log[2] / log[1] * 100) if log[1] > 0 else 0 for log in logs]
    else:
        # Mock data if no logs
        dates = [datetime.now().date() - timedelta(days=x) for x in range(6, -1, -1)]
        adherence_data = [0] * 7

    fig = px.line(
        x=dates,
        y=adherence_data,
        title="Daily Medication Adherence",
        labels={"x": "Date", "y": "Adherence %"},
    )
    # Plotly needs literal color values (can't consume CSS vars). These match
    # the warm-cream theme; TODO expose theme_tokens() from ui.theme so this
    # can follow theme switches.
    fig.update_traces(
        line_color="#C2410C", line_width=3, marker_color="#C2410C", marker_size=8
    )
    fig.update_layout(
        yaxis_range=[0, 100],
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        title_font_color="#2A241D",
        font_color="#3F372E",
        title_font_size=18,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Medication schedule
    st.markdown("## ⏰ Today's Medication Schedule")

    medications = db.get_patient_medications(patient_id)

    if medications:
        today = datetime.now().date().isoformat()
        schedule_data = []

        for med in medications:
            for time in med["times"]:
                # Check if logged today
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.execute(
                        """
                        SELECT taken FROM dose_logs
                        WHERE patient_id = ? AND medication_name = ? 
                        AND scheduled_time = ? AND date = ?
                    """,
                        (patient_id, med["name"], time, today),
                    )
                    log = cursor.fetchone()

                if log:
                    status = "Taken" if log[0] else "Missed"
                else:
                    status = "⏳ Pending"

                schedule_data.append(
                    {
                        "Time": time,
                        "Medication": med["name"],
                        "Dosage": med["dosage"],
                        "Status": status,
                    }
                )

        df = pd.DataFrame(schedule_data).sort_values("Time")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No medications scheduled for this patient yet.")




def render() -> None:
    init_session_state()
    # ``show_patient_details`` reads st.session_state['selected_patient'].
    # Sync from ?id= for URL-driven navigation.
    pid = st.query_params.get("id")
    if pid is not None:
        try:
            st.session_state["selected_patient"] = int(pid)
        except (TypeError, ValueError):
            pass
    if "selected_patient" not in st.session_state:
        st.info("No patient selected. Go to Dashboard to pick one.")
        return
    show_patient_details()
