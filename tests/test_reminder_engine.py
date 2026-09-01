"""Stage 3 — the reconciliation engine (REMINDER_ENGINE.md).

Drives services.reminder_engine.tick with an injected ``now`` and a fake
notifier — no real clock, no real SMS. Proves the escalation offsets, the
gating on logged doses, idempotency, and the most-advanced-stage catch-up.
"""

from datetime import date, datetime, time

import pytest

from services import reminder_engine
from utils.database import MedicationDB


class FakeNotifier:
    """Records send calls; returns a configurable success flag."""

    def __init__(self, succeed=True):
        self.succeed = succeed
        self.calls = []  # (stage, recipient_name, med_name, scheduled_time)

    def send_dose_reminder(self, patient, med, t):
        self.calls.append(("reminder", patient["name"], med["name"], t))
        return self.succeed

    def send_dose_followup(self, patient, med, t):
        self.calls.append(("followup", patient["name"], med["name"], t))
        return self.succeed

    def send_caregiver_alert(self, caregiver, patient, med, t):
        self.calls.append(("alert", caregiver["name"], med["name"], t))
        return self.succeed

    def stages(self):
        return [c[0] for c in self.calls]


@pytest.fixture
def db(tmp_path):
    return MedicationDB(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def world(db):
    """A patient with a phone, one caregiver with a phone in their circle, and
    a single daily medication scheduled at 08:00."""
    caregiver = db.add_user("Cara", email="cara@x.com", role="family_member", phone="+14155550111")
    patient = db.add_user("Pat", email="pat@x.com", role="patient", phone="+14155550100")
    _, invite = db.create_family_circle("Circle", caregiver)
    db.join_family_circle(invite, patient, relationship="patient")
    med_id = db.add_medication(patient, patient, "Metformin", "500mg", "daily", ["08:00"])
    return {"db": db, "caregiver": caregiver, "patient": patient, "med_id": med_id}


def _at(hh, mm):
    """A naive ``now`` on today's date (aligns with log_dose's real date)."""
    return datetime.combine(date.today(), time(hh, mm))


TODAY = date.today().isoformat()


# --- Stage timing -----------------------------------------------------------

def test_no_reminder_before_dose_time(world):
    notifier = FakeNotifier()
    reminder_engine.tick(world["db"], notifier, _at(7, 59))
    assert notifier.calls == []


def test_patient_reminder_at_dose_time(world):
    notifier = FakeNotifier()
    reminder_engine.tick(world["db"], notifier, _at(8, 0))
    assert notifier.stages() == ["reminder"]
    assert notifier.calls[0][1] == "Pat"


def test_followup_at_t30_when_not_logged(world):
    db, notifier = world["db"], FakeNotifier()
    reminder_engine.tick(db, notifier, _at(8, 0))      # reminder
    reminder_engine.tick(db, notifier, _at(8, 30))     # follow-up
    assert notifier.stages() == ["reminder", "followup"]


def test_caregiver_alert_at_t60_goes_to_caregiver(world):
    db, notifier = world["db"], FakeNotifier()
    reminder_engine.tick(db, notifier, _at(8, 0))
    reminder_engine.tick(db, notifier, _at(8, 30))
    reminder_engine.tick(db, notifier, _at(9, 0))
    assert notifier.stages() == ["reminder", "followup", "alert"]
    assert notifier.calls[-1][1] == "Cara"  # the caregiver, not the patient


# --- Gating -----------------------------------------------------------------

def test_logged_dose_halts_escalation(world):
    db, notifier = world["db"], FakeNotifier()
    reminder_engine.tick(db, notifier, _at(8, 0))          # reminder goes out
    db.log_dose(world["patient"], world["patient"], "Metformin", "08:00", True)
    reminder_engine.tick(db, notifier, _at(8, 30))         # would be follow-up
    reminder_engine.tick(db, notifier, _at(9, 0))          # would be alert
    assert notifier.stages() == ["reminder"]  # nothing after the dose was logged


def test_as_needed_medication_is_never_reminded(db):
    patient = db.add_user("Pat", email="p@x.com", role="patient", phone="+14155550100")
    db.add_medication(patient, patient, "Ibuprofen", "200mg", "as_needed", ["08:00"])
    notifier = FakeNotifier()
    reminder_engine.tick(db, notifier, _at(9, 0))
    assert notifier.calls == []


# --- Idempotency + catch-up -------------------------------------------------

def test_reminder_is_idempotent_across_repeated_ticks(world):
    db, notifier = world["db"], FakeNotifier()
    for _ in range(3):
        reminder_engine.tick(db, notifier, _at(8, 0))
    assert notifier.stages() == ["reminder"]  # sent exactly once


def test_catchup_sends_only_most_advanced_stage(world):
    """Fresh state, dose 70 min overdue: only the caregiver alert fires, and the
    earlier stages are recorded as superseded so they never fire later."""
    db, notifier = world["db"], FakeNotifier()
    reminder_engine.tick(db, notifier, _at(9, 10))  # T+70, nothing sent yet

    assert notifier.stages() == ["alert"]  # no burst of three texts
    p, m = world["patient"], "Metformin"
    assert db.notification_sent(p, m, "08:00", TODAY, "patient_reminder") is True   # superseded
    assert db.notification_sent(p, m, "08:00", TODAY, "patient_followup") is True   # superseded
    assert db.notification_sent(p, m, "08:00", TODAY, "caregiver_alert") is True    # sent

    # A later tick does nothing more.
    reminder_engine.tick(db, notifier, _at(9, 11))
    assert notifier.stages() == ["alert"]


# --- Send failures + missing caregiver --------------------------------------

def test_failed_send_is_not_recorded_and_retries(world):
    db = world["db"]
    failing = FakeNotifier(succeed=False)
    reminder_engine.tick(db, failing, _at(8, 0))
    # Not recorded, because the SMS did not go out.
    assert db.notification_sent(world["patient"], "Metformin", "08:00", TODAY, "patient_reminder") is False

    ok = FakeNotifier(succeed=True)
    reminder_engine.tick(db, ok, _at(8, 1))
    assert ok.stages() == ["reminder"]  # retried and succeeded
    assert db.notification_sent(world["patient"], "Metformin", "08:00", TODAY, "patient_reminder") is True


def test_all_caregivers_are_alerted(db):
    """Every caregiver with a phone gets the alert, not just the first."""
    c1 = db.add_user("Cara One", email="c1@x.com", role="family_member", phone="+14155550111")
    c2 = db.add_user("Cara Two", email="c2@x.com", role="family_member", phone="+14155550122")
    patient = db.add_user("Pat", email="pat@x.com", role="patient", phone="+14155550100")
    _, invite = db.create_family_circle("Circle", c1)
    db.join_family_circle(invite, patient, relationship="patient")
    db.join_family_circle(invite, c2)
    db.add_medication(patient, patient, "Metformin", "500mg", "daily", ["08:00"])

    notifier = FakeNotifier()
    reminder_engine.tick(db, notifier, _at(8, 0))
    reminder_engine.tick(db, notifier, _at(8, 30))
    reminder_engine.tick(db, notifier, _at(9, 0))

    alerted = {name for stage, name, *_ in notifier.calls if stage == "alert"}
    assert alerted == {"Cara One", "Cara Two"}


def test_no_caregiver_contact_does_not_crash_or_record(db):
    # Patient with a med but no caregiver in any circle.
    patient = db.add_user("Lon", email="lon@x.com", role="patient", phone="+14155550100")
    db.add_medication(patient, patient, "Metformin", "500mg", "daily", ["08:00"])
    notifier = FakeNotifier()

    reminder_engine.tick(db, notifier, _at(9, 0))  # T+60, alert stage but no caregiver
    assert "alert" not in notifier.stages()
    assert db.notification_sent(patient, "Metformin", "08:00", TODAY, "caregiver_alert") is False
