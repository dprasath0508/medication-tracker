"""Today page — split from the original monolithic web_app.py.

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


def show_medication_logging():
    """Show interface for logging today's medications."""
    db, family_manager = init_database()
    user = st.session_state.user_profile

    if "snoozed_meds" not in st.session_state:
        st.session_state.snoozed_meds = {}

    st.markdown(
        """
    <style>
        .page-eyebrow {
            font-size: 0.8125rem;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.25rem;
        }
        .page-title {
            font-size: 1.875rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: var(--text);
            margin-bottom: 2rem;
        }
        .progress-section {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
        }
        .progress-label {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 0.75rem;
        }
        .progress-label-text {
            font-size: 0.9375rem;
            font-weight: 500;
            color: var(--text);
        }
        .progress-label-count {
            font-size: 0.8125rem;
            color: var(--text-muted);
            font-variant-numeric: tabular-nums;
        }
        .med-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem 1.5rem;
            margin: 0.75rem 0;
            transition: border-color 0.15s ease;
        }
        .med-card:hover { border-color: var(--border-strong); }
        .med-card-taken {
            background: var(--surface);
            border-color: var(--border);
            opacity: 0.75;
        }
        .med-name {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text);
            margin: 0 0 0.125rem 0;
            letter-spacing: -0.01em;
        }
        .med-meta {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin: 0;
            font-variant-numeric: tabular-nums;
        }
        .med-meta-sep { color: var(--text-subtle); margin: 0 0.375rem; }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.25rem 0.625rem;
            border-radius: 4px;
            font-size: 0.8125rem;
            font-weight: 500;
            font-variant-numeric: tabular-nums;
        }
        .status-badge-taken {
            background: var(--success-subtle);
            color: var(--success);
            border: 1px solid rgba(5, 150, 105, 0.15);
        }
        .status-badge-snoozed {
            background: var(--warning-subtle);
            color: var(--warning);
            border: 1px solid rgba(217, 119, 6, 0.15);
        }
        .status-badge-missed {
            background: #FEF2F2;
            color: var(--error);
            border: 1px solid rgba(220, 38, 38, 0.15);
        }
        .med-note {
            font-size: 0.8125rem;
            color: var(--text-muted);
            margin: 0.5rem 0 0 0;
            padding-top: 0.5rem;
            border-top: 1px solid var(--border);
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    if st.button("Back", key="back_to_dash"):
        st.session_state.show_medication_logging = False
        st.rerun()

    if user["type"] == "patient":
        patient_id = user["id"]
        patient_name = user["name"]
    else:
        circles = db.get_user_family_circles(user["id"])
        if not circles:
            st.warning("No family circles found.")
            return

        patients_status = db.get_family_patients_status(user["id"])
        if not patients_status:
            st.info("No patients to log medications for.")
            return

        patient_names = {p["id"]: p["name"] for p in patients_status}
        selected_patient_id = st.selectbox(
            "Patient",
            options=list(patient_names.keys()),
            format_func=lambda x: patient_names[x],
            key="patient_selector",
        )
        patient_id = selected_patient_id
        patient_name = patient_names[patient_id]

    today_str = datetime.now().strftime("%A, %B %-d")
    st.markdown(f'<p class="page-eyebrow">{today_str}</p>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="page-title">Today\'s medications</h1>', unsafe_allow_html=True
    )

    medications = db.get_patient_medications(patient_id)

    if not medications:
        st.markdown(
            """
        <div class="empty-state">
            <h3>No medications scheduled</h3>
            <p>Add medications from the dashboard to see them here.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    today = datetime.now().date().isoformat()

    all_doses = []
    for medication in medications:
        for med_time in medication["times"]:
            snooze_key = f"{medication['id']}_{med_time}"
            if snooze_key in st.session_state.snoozed_meds:
                snoozed_until = st.session_state.snoozed_meds[snooze_key]
                if datetime.now() < snoozed_until:
                    display_time = snoozed_until.strftime("%H:%M")
                    is_snoozed = True
                else:
                    display_time = med_time
                    is_snoozed = False
                    del st.session_state.snoozed_meds[snooze_key]
            else:
                display_time = med_time
                is_snoozed = False

            try:
                if hasattr(db, "db_path") and db.db_path:
                    with sqlite3.connect(db.db_path) as conn:
                        cursor = conn.execute(
                            """
                            SELECT taken, actual_time FROM dose_logs
                            WHERE patient_id = ? AND medication_name = ?
                            AND scheduled_time = ? AND date = ?
                        """,
                            (patient_id, medication["name"], med_time, today),
                        )
                        existing_log = cursor.fetchone()
                else:
                    result = (
                        db.client.table("dose_logs")
                        .select("taken, actual_time")
                        .eq("patient_id", patient_id)
                        .eq("medication_name", medication["name"])
                        .eq("scheduled_time", med_time)
                        .eq("date", today)
                        .execute()
                    )
                    existing_log = (
                        (result.data[0]["taken"], result.data[0]["actual_time"])
                        if result.data
                        else None
                    )
            except Exception:
                existing_log = None

            all_doses.append(
                {
                    "medication": medication,
                    "scheduled_time": med_time,
                    "display_time": display_time,
                    "is_snoozed": is_snoozed,
                    "existing_log": existing_log,
                    "sort_time": datetime.strptime(display_time, "%H:%M").time(),
                }
            )

    all_doses.sort(key=lambda x: x["sort_time"])

    total_doses = len(all_doses)
    taken_doses = sum(
        1 for d in all_doses if d["existing_log"] and d["existing_log"][0]
    )
    progress_pct = (taken_doses / total_doses * 100) if total_doses > 0 else 0

    st.markdown(
        f"""
    <div class="progress-section">
        <div class="progress-label">
            <span class="progress-label-text">Progress</span>
            <span class="progress-label-count">{taken_doses} of {total_doses} taken</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.progress(progress_pct / 100)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    for dose in all_doses:
        medication = dose["medication"]
        med_time = dose["scheduled_time"]
        display_time = dose["display_time"]
        existing_log = dose["existing_log"]
        is_snoozed = dose["is_snoozed"]

        try:
            time_obj = datetime.strptime(display_time, "%H:%M")
            formatted_time = time_obj.strftime("%-I:%M %p")
        except ValueError:
            formatted_time = display_time

        card_class = (
            "med-card med-card-taken"
            if existing_log and existing_log[0]
            else "med-card"
        )

        with st.container():
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

            col1, col2 = st.columns([3, 2])

            with col1:
                st.markdown(
                    f'<p class="med-name">{medication["name"]}</p>',
                    unsafe_allow_html=True,
                )
                meta = f'{medication["dosage"]}<span class="med-meta-sep">·</span>{formatted_time}'
                st.markdown(f'<p class="med-meta">{meta}</p>', unsafe_allow_html=True)

                if is_snoozed:
                    original_time = datetime.strptime(med_time, "%H:%M").strftime(
                        "%-I:%M %p"
                    )
                    st.markdown(
                        f'<span class="status-badge status-badge-snoozed">Snoozed from {original_time}</span>',
                        unsafe_allow_html=True,
                    )

                if medication.get("notes"):
                    st.markdown(
                        f'<p class="med-note">{medication["notes"]}</p>',
                        unsafe_allow_html=True,
                    )

            with col2:
                if existing_log and existing_log[0]:
                    taken_time = existing_log[1]
                    try:
                        taken_time_obj = datetime.strptime(taken_time, "%H:%M")
                        taken_formatted = taken_time_obj.strftime("%-I:%M %p")
                    except ValueError:
                        taken_formatted = taken_time
                    st.markdown(
                        f'<div style="display: flex; justify-content: flex-end; align-items: center; height: 100%;">'
                        f'<span class="status-badge status-badge-taken">Taken at {taken_formatted}</span>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                elif existing_log and not existing_log[0]:
                    st.markdown(
                        '<div style="display: flex; justify-content: flex-end; align-items: center; height: 100%;">'
                        '<span class="status-badge status-badge-missed">Missed</span>'
                        "</div>",
                        unsafe_allow_html=True,
                    )

                else:
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(
                            "Mark taken",
                            key=f"take_{medication['id']}_{med_time}",
                            use_container_width=True,
                            type="primary",
                        ):
                            db.log_dose(
                                patient_id,
                                medication["name"],
                                med_time,
                                True,
                                user["id"],
                                datetime.now().strftime("%H:%M"),
                            )
                            st.rerun()
                    with btn_col2:
                        if st.button(
                            "Snooze",
                            key=f"snooze_{medication['id']}_{med_time}",
                            use_container_width=True,
                        ):
                            snooze_key = f"{medication['id']}_{med_time}"
                            snooze_until = datetime.now() + timedelta(minutes=30)
                            st.session_state.snoozed_meds[snooze_key] = snooze_until
                            st.toast(f"Snoozed {medication['name']} for 30 minutes")
                            st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)




def render() -> None:
    init_session_state()
    show_medication_logging()
