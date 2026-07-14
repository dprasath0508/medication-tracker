"""/dashboard — family caregiver overview.

Family members see patients they monitor, average adherence, alerts.
Patients see their circles and a shortcut to today's meds.
"""

from __future__ import annotations

import streamlit as st

from ui.icons import icon
from ui.primitives import (
    page_shell,
    empty_state,
    status_pill,
    divider,
    stack_open,
    stack_close,
)
from utils.session import (
    db as _db,
    family_manager as _family_manager,
    current_user,
    init_session_state,
    cached_user_family_circles,
)


def render() -> None:
    init_session_state()
    user = current_user()
    if user is None:
        st.info("Sign in to see the dashboard.")
        return

    db = _db()
    family_manager = _family_manager()

    page_shell(
        "Dashboard",
        eyebrow=f"Signed in as {user.get('type', 'user').title()}",
        subtitle=f"Welcome back, {user['name']}.",
    )

    if user["type"] == "patient":
        _render_patient_shortcut()

    circles = cached_user_family_circles(user["id"])

    if not circles:
        empty_state(
            "No family circles yet",
            "Create a circle to start monitoring together, or join one with an invite code.",
        )
        cols = st.columns([1, 1])
        with cols[0]:
            if st.button("Create a circle", key="dash_create", type="primary", use_container_width=True):
                st.query_params["action"] = "create"
                st.switch_page("pages/circle.py") if hasattr(st, "switch_page") else st.rerun()
        with cols[1]:
            if st.button("Join a circle", key="dash_join", use_container_width=True):
                st.query_params["action"] = "join"
                st.switch_page("pages/circle.py") if hasattr(st, "switch_page") else st.rerun()
        return

    data = family_manager.get_family_dashboard_data(user["id"])

    if data["total_patients"] == 0:
        _render_circles(circles)
        divider(5)
        empty_state(
            "No patients yet",
            "Add someone to a circle to start tracking their medications.",
        )
        if st.button("Add a patient", key="dash_add_patient", type="primary"):
            st.session_state["show_add_patient"] = True
            st.rerun()
        return

    _render_metrics(data)
    divider(5)
    _render_alerts(data)
    _render_patient_grid(db, data)


# ---------------------------------------------------------------------------

def _render_patient_shortcut() -> None:
    """Prominent card at top of dashboard for patient personas."""
    st.markdown(
        """
        <div class="med-card page-fade" style="
            margin-bottom: var(--space-6);
            background: linear-gradient(135deg, var(--accent-subtle) 0%, var(--surface-card) 100%);
            border-color: var(--border-strong);">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:var(--space-5);">
            <div>
              <p class="eyebrow" style="color:var(--accent);">Right now</p>
              <h2 style="margin:0;">Your medications for today</h2>
              <p class="muted" style="margin: var(--space-2) 0 0 0;">Check them off as you take them.</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Open today's list", key="dash_open_today", type="primary"):
        st.switch_page("pages/today.py") if hasattr(st, "switch_page") else st.rerun()
    divider(6)


def _render_circles(circles: list[dict]) -> None:
    st.markdown('<h2>Your family circles</h2>', unsafe_allow_html=True)
    stack_open()
    for c in circles:
        st.markdown(
            f"""
            <div class="med-card">
              <h3 style="margin:0 0 var(--space-1) 0;">{c['name']}</h3>
              <p class="muted tabular" style="margin:0;font-size:0.9375rem;">
                Invite code: <span style="font-family:var(--font-mono);color:var(--text);">{c['invite_code']}</span>
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    stack_close()


def _render_metrics(data: dict) -> None:
    st.markdown('<h2 style="margin-top: var(--space-6);">Overview</h2>', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        st.metric("Patients", data["total_patients"])
    with cols[1]:
        adh = data["average_adherence"]
        st.metric("Avg adherence", f"{adh}%" if adh > 0 else "—")
    with cols[2]:
        st.metric("Need attention", data["patients_needing_attention"])
    with cols[3]:
        st.metric("Circles", len(data["family_circles"]))


def _render_alerts(data: dict) -> None:
    alerts = data.get("alerts") or []
    if not alerts:
        return
    st.markdown('<h2 style="margin-top: var(--space-6);">Alerts</h2>', unsafe_allow_html=True)
    for alert in alerts:
        kind = "warning" if "low medication adherence" in alert else "success"
        bg = "var(--warning-subtle)" if kind == "warning" else "var(--success-subtle)"
        fg = "var(--warning)" if kind == "warning" else "var(--success)"
        st.markdown(
            f'<div class="med-card page-fade" style="background:{bg};color:{fg};'
            f'border-color:{fg};padding: var(--space-4) var(--space-5);">{alert}</div>',
            unsafe_allow_html=True,
        )
    divider(5)


def _render_patient_grid(db, data: dict) -> None:
    st.markdown('<h2 style="margin-top: var(--space-6);">Patients</h2>', unsafe_allow_html=True)
    stack_open()
    for p in data["patients_status"]:
        adherence = p["adherence_rate"]
        pill_kind = "success" if adherence >= 90 else "warning" if adherence >= 70 else "error"
        adh_display = f"{adherence:.0f}% adherence" if adherence > 0 else "No data yet"
        st.markdown(
            f"""
            <div class="med-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:var(--space-4);">
                <div>
                  <h3 style="margin:0 0 var(--space-1) 0;">{p['name']}</h3>
                  <p class="muted" style="margin:0;font-size:0.9375rem;">
                    Age {p['age']} · {p['family_circle_name']} · {p['total_medications']} meds
                  </p>
                </div>
                <div>{status_pill(adh_display, pill_kind)}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cols = st.columns([1, 1, 1])
        with cols[0]:
            if st.button("View", key=f"view_{p['id']}", use_container_width=True):
                st.query_params["id"] = str(p["id"])
                if hasattr(st, "switch_page"):
                    st.switch_page("pages/patient.py")
                else:
                    st.session_state["selected_patient"] = p["id"]
                    st.rerun()
        with cols[1]:
            if st.button("Add med", key=f"addmed_{p['id']}", use_container_width=True):
                st.query_params["patient"] = str(p["id"])
                if hasattr(st, "switch_page"):
                    st.switch_page("pages/add_med.py")
                else:
                    st.session_state["add_medication_for"] = p["id"]
                    st.rerun()
        with cols[2]:
            if st.button("Log today", key=f"logtoday_{p['id']}", type="primary", use_container_width=True):
                if hasattr(st, "switch_page"):
                    st.switch_page("pages/today.py")
                else:
                    st.session_state["show_medication_logging"] = True
                    st.rerun()
        divider(3)
    stack_close()
