"""Finding 1 — authorization chokepoint tests (HARDENING_SPRINT.md).

Every patient-scoped data method must require caller identity and authorize
through utils/authz.py. Runs against the SQLite backend with a tmp DB.

Fixture cast:
- caregiver: created the circle → permissions include manage_meds (can write)
- patient:   joined the circle, role='patient'
- viewer:    joined the circle → default permissions ['view', 'set_reminders']
- stranger:  authenticated user with no circle relationship to the patient
"""

import sqlite3

import pytest

from utils.authz import SYSTEM_CALLER, AuthorizationError
from utils.database import MedicationDB


@pytest.fixture
def db(tmp_path):
    return MedicationDB(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def circle(db):
    caregiver = db.add_user("Cara Caregiver", email="cara@example.com", role="family_member")
    patient = db.add_user("Pat Patient", email="pat@example.com", role="patient", age=78)
    viewer = db.add_user("Vic Viewer", email="vic@example.com", role="family_member")
    stranger = db.add_user("Sam Stranger", email="sam@example.com", role="family_member")

    _, invite_code = db.create_family_circle("Pat's Circle", caregiver)
    assert db.join_family_circle(invite_code, patient, relationship="patient")
    assert db.join_family_circle(invite_code, viewer)

    return {
        "caregiver": caregiver,
        "patient": patient,
        "viewer": viewer,
        "stranger": stranger,
    }


def _add_med_as_patient(db, patient_id):
    return db.add_medication(patient_id, patient_id, "Aspirin", "81mg", "daily", ["08:00"])


# --- Strangers: no relationship, no access ---------------------------------

def test_user_cannot_read_other_patients_medications(db, circle):
    _add_med_as_patient(db, circle["patient"])
    with pytest.raises(AuthorizationError):
        db.get_patient_medications(circle["stranger"], circle["patient"])


def test_user_cannot_write_medication_for_other_patient(db, circle):
    with pytest.raises(AuthorizationError):
        db.add_medication(circle["stranger"], circle["patient"], "Fentanyl", "100mg", "daily", ["08:00"])
    assert db.get_patient_medications(circle["patient"], circle["patient"]) == []


def test_user_cannot_log_dose_for_other_patient(db, circle):
    _add_med_as_patient(db, circle["patient"])
    with pytest.raises(AuthorizationError):
        db.log_dose(circle["stranger"], circle["patient"], "Aspirin", "08:00", True)


def test_user_cannot_read_other_patients_history_or_profile(db, circle):
    stranger, patient = circle["stranger"], circle["patient"]
    with pytest.raises(AuthorizationError):
        db.get_patient_adherence(stranger, patient)
    with pytest.raises(AuthorizationError):
        db.get_daily_dose_counts(stranger, patient)
    with pytest.raises(AuthorizationError):
        db.get_dose_log_for_date(stranger, patient, "Aspirin", "08:00", "2026-07-14")
    with pytest.raises(AuthorizationError):
        db.get_patient(stranger, patient)


def test_denied_read_raises_instead_of_returning_empty(db, circle):
    """A denial must be an exception the caller cannot mistake for 'no data'."""
    _add_med_as_patient(db, circle["patient"])
    with pytest.raises(AuthorizationError) as excinfo:
        db.get_patient_medications(circle["stranger"], circle["patient"])
    assert excinfo.value.caller_id == circle["stranger"]
    assert excinfo.value.patient_id == circle["patient"]
    assert excinfo.value.level == "read"


# --- Circle members: permission levels --------------------------------------

def test_family_member_with_view_permission_can_read_but_not_write(db, circle):
    viewer, patient = circle["viewer"], circle["patient"]
    _add_med_as_patient(db, patient)

    meds = db.get_patient_medications(viewer, patient)
    assert [m["name"] for m in meds] == ["Aspirin"]
    assert db.get_patient(viewer, patient)["name"] == "Pat Patient"

    with pytest.raises(AuthorizationError):
        db.add_medication(viewer, patient, "Ibuprofen", "200mg", "daily", ["09:00"])
    with pytest.raises(AuthorizationError):
        db.log_dose(viewer, patient, "Aspirin", "08:00", True)


def test_family_member_with_manage_meds_permission_can_write(db, circle):
    caregiver, patient = circle["caregiver"], circle["patient"]

    med_id = db.add_medication(caregiver, patient, "Metformin", "500mg", "daily", ["08:00"])
    assert med_id > 0
    db.log_dose(caregiver, patient, "Metformin", "08:00", True, "08:05")

    meds = db.get_patient_medications(patient, patient)
    assert [m["name"] for m in meds] == ["Metformin"]


def test_patient_can_always_access_own_data(db):
    # No circle at all — self-access must still work.
    solo = db.add_user("Solo Patient", email="solo@example.com", role="patient")
    db.add_medication(solo, solo, "Lisinopril", "10mg", "daily", ["08:00"])
    db.log_dose(solo, solo, "Lisinopril", "08:00", True)

    assert len(db.get_patient_medications(solo, solo)) == 1
    assert db.get_patient_adherence(solo, solo) == 100.0
    assert db.get_patient(solo, solo)["name"] == "Solo Patient"


# --- Untrusted identifiers cannot escalate ----------------------------------

def test_query_param_patient_id_cannot_escalate_access(db, circle):
    """Simulates add_med.py / patient.py: an attacker edits ?patient=<id> /
    ?id=<id>, which becomes an arbitrary int patient_id. The data layer must
    refuse regardless of what identifier the URL supplied."""
    attacker = circle["stranger"]
    for forged_patient_id in (circle["patient"], circle["caregiver"], 999999):
        if forged_patient_id == attacker:
            continue
        with pytest.raises(AuthorizationError):
            db.get_patient(attacker, forged_patient_id)
        with pytest.raises(AuthorizationError):
            db.add_medication(attacker, forged_patient_id, "X", "1mg", "daily", ["08:00"])


def test_non_int_caller_is_rejected(db, circle):
    with pytest.raises(AuthorizationError):
        db.get_patient_medications(None, circle["patient"])
    with pytest.raises(AuthorizationError):
        db.get_patient_medications(str(circle["patient"]), circle["patient"])


# --- System identity: read-only, unforgeable --------------------------------

def test_system_caller_can_read(db, circle):
    _add_med_as_patient(db, circle["patient"])
    meds = db.get_patient_medications(SYSTEM_CALLER, circle["patient"])
    assert [m["name"] for m in meds] == ["Aspirin"]
    assert db.get_daily_dose_counts(SYSTEM_CALLER, circle["patient"]) == []


def test_system_caller_cannot_write(db, circle):
    with pytest.raises(AuthorizationError):
        db.add_medication(SYSTEM_CALLER, circle["patient"], "X", "1mg", "daily", ["08:00"])
    with pytest.raises(AuthorizationError):
        db.log_dose(SYSTEM_CALLER, circle["patient"], "Aspirin", "08:00", True)


# --- The caller is what gets recorded ---------------------------------------

def test_dose_is_recorded_as_logged_by_the_caller(db, circle):
    caregiver, patient = circle["caregiver"], circle["patient"]
    db.add_medication(caregiver, patient, "Metformin", "500mg", "daily", ["08:00"])
    log_id = db.log_dose(caregiver, patient, "Metformin", "08:00", True)

    with sqlite3.connect(db.db_path) as conn:
        row = conn.execute(
            "SELECT logged_by, patient_id FROM dose_logs WHERE id = ?", (log_id,)
        ).fetchone()
    assert row == (caregiver, patient)


def test_medication_is_recorded_as_managed_by_the_caller(db, circle):
    caregiver, patient = circle["caregiver"], circle["patient"]
    db.add_medication(caregiver, patient, "Metformin", "500mg", "daily", ["08:00"])

    (med,) = db.get_patient_medications(patient, patient)
    assert med["managed_by"] == caregiver
    assert med["patient_id"] == patient
