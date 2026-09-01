"""Stage 1 — the reminder-engine ledger + caregiver reads (REMINDER_ENGINE.md).

The notification_log ledger is what makes the per-minute engine idempotent and
restart-safe: a (dose, stage) recorded once is never sent again. These run
against the SQLite backend with a tmp DB.
"""

import pytest

from utils.database import MedicationDB


@pytest.fixture
def db(tmp_path):
    return MedicationDB(db_path=str(tmp_path / "test.db"))


DOSE = (1, "Metformin", "08:00", "2026-08-11")  # patient_id, med, scheduled_time, date


# --- Ledger: record + query ------------------------------------------------

def test_notification_sent_is_false_until_recorded(db):
    assert db.notification_sent(*DOSE, "patient_reminder") is False
    assert db.record_notification(*DOSE, "patient_reminder") is True
    assert db.notification_sent(*DOSE, "patient_reminder") is True


def test_record_notification_is_idempotent(db):
    assert db.record_notification(*DOSE, "patient_reminder") is True
    assert db.record_notification(*DOSE, "patient_reminder") is False  # duplicate ignored


def test_stages_are_independent(db):
    assert db.record_notification(*DOSE, "patient_reminder") is True
    # A different stage for the same dose is a separate ledger entry.
    assert db.record_notification(*DOSE, "caregiver_alert") is True
    assert db.notification_sent(*DOSE, "patient_followup") is False


def test_same_dose_next_day_and_other_time_are_independent(db):
    assert db.record_notification(1, "Metformin", "08:00", "2026-08-11", "patient_reminder") is True
    assert db.record_notification(1, "Metformin", "08:00", "2026-08-12", "patient_reminder") is True
    assert db.record_notification(1, "Metformin", "20:00", "2026-08-11", "patient_reminder") is True


# --- Caregiver contacts ----------------------------------------------------

def test_get_caregiver_contacts_returns_family_with_phone_only(db):
    patient = db.add_user("Pat", email="pat@x.com", role="patient", phone="+14155550100")
    withphone = db.add_user("Cara", email="cara@x.com", role="family_member", phone="+14155550111")
    nophone = db.add_user("Nyla", email="nyla@x.com", role="family_member")

    _, invite = db.create_family_circle("Circle", withphone)  # creator is a family member
    db.join_family_circle(invite, patient, relationship="patient")
    db.join_family_circle(invite, nophone)

    contacts = db.get_caregiver_contacts(patient)
    ids = {c["id"] for c in contacts}
    assert withphone in ids       # family member with a phone -> included
    assert nophone not in ids     # no phone -> excluded
    assert patient not in ids     # the patient is not a caregiver of themselves
    assert all(c["phone"] for c in contacts)


def test_get_caregiver_contacts_dedupes_across_circles(db):
    patient = db.add_user("Pat", email="pat@x.com", role="patient", phone="+14155550100")
    cara = db.add_user("Cara", email="cara@x.com", role="family_member", phone="+14155550111")

    _, inv1 = db.create_family_circle("C1", cara)
    db.join_family_circle(inv1, patient, relationship="patient")
    _, inv2 = db.create_family_circle("C2", cara)
    db.join_family_circle(inv2, patient, relationship="patient")

    contacts = db.get_caregiver_contacts(patient)
    assert [c["id"] for c in contacts].count(cara) == 1  # shared two circles, listed once


def test_get_caregiver_contacts_empty_when_no_circle(db):
    lonely = db.add_user("Lon", email="lon@x.com", role="patient", phone="+14155550100")
    assert db.get_caregiver_contacts(lonely) == []
