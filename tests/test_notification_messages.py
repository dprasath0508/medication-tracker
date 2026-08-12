"""Stage 2 — escalation SMS messages (REMINDER_ENGINE.md).

Each message method must send to the right recipient with the dose details and
the scheduled time, and must return send_sms's real result so a missing phone
or a failed send is False (the engine then retries — never a phantom send).
"""

import pytest

from services.notifications import NotificationService


@pytest.fixture
def notifier():
    # No Twilio credentials in the test env -> twilio_client is None.
    return NotificationService()


PATIENT = {"name": "Pat Patient", "phone": "+14155550100"}
CAREGIVER = {"name": "Cara Caregiver", "phone": "+14155550111"}
MED = {"name": "Metformin", "dosage": "500mg"}


def test_messages_send_to_recipient_with_dose_details_and_time(notifier, monkeypatch):
    sent = []
    monkeypatch.setattr(notifier, "send_sms", lambda to, msg: sent.append((to, msg)) or True)

    assert notifier.send_dose_reminder(PATIENT, MED, "08:00") is True
    assert notifier.send_dose_followup(PATIENT, MED, "08:00") is True
    assert notifier.send_caregiver_alert(CAREGIVER, PATIENT, MED, "08:00") is True

    assert [to for to, _ in sent] == [PATIENT["phone"], PATIENT["phone"], CAREGIVER["phone"]]
    # Patient-facing messages name the med, dose, and the scheduled time (not now).
    for _, msg in sent[:2]:
        assert "Metformin" in msg and "500mg" in msg and "8:00" in msg
    # Caregiver alert names the patient so the caregiver knows who to check on.
    assert "Pat Patient" in sent[2][1]


def test_no_emoji_or_exclamation_in_copy(notifier, monkeypatch):
    sent = []
    monkeypatch.setattr(notifier, "send_sms", lambda to, msg: sent.append(msg) or True)
    notifier.send_dose_reminder(PATIENT, MED, "08:00")
    notifier.send_caregiver_alert(CAREGIVER, PATIENT, MED, "08:00")
    for msg in sent:
        assert "!" not in msg
        assert msg.isascii()  # no emoji


def test_returns_false_when_recipient_has_no_phone(notifier):
    no_phone_patient = {"name": "Pat", "phone": None}
    no_phone_caregiver = {"name": "Cara", "phone": ""}
    assert notifier.send_dose_reminder(no_phone_patient, MED, "08:00") is False
    assert notifier.send_dose_followup(no_phone_patient, MED, "08:00") is False
    assert notifier.send_caregiver_alert(no_phone_caregiver, PATIENT, MED, "08:00") is False


def test_returns_false_when_send_sms_fails(notifier, monkeypatch):
    # Twilio not configured -> send_sms returns False -> the method must too,
    # so the engine does not record the stage and retries next tick.
    monkeypatch.setattr(notifier, "send_sms", lambda to, msg: False)
    assert notifier.send_dose_reminder(PATIENT, MED, "08:00") is False


def test_format_time_renders_twelve_hour_clock(notifier):
    assert notifier._format_time("08:00") == "8:00 AM"
    assert notifier._format_time("20:30") == "8:30 PM"
    assert notifier._format_time("bogus") == "bogus"  # unparseable falls through
