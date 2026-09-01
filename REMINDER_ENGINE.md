# Reminder delivery engine — design

Status: **design locked, implementation in progress.** This is the plan of
record for the medication reminder + escalation system. Read it before
touching `services/reminder_engine.py`, `services/scheduler.py`, or the
deployment config.

---

## Goal

When a dose is due, prompt the patient; if they don't log it, follow up; if
they still don't, alert a caregiver. Concretely, a **two-stage escalation**
per scheduled dose:

| Stage | Offset | Recipient | Condition |
|-------|--------|-----------|-----------|
| `patient_reminder` | T+0 | patient (SMS) | dose not already logged |
| `patient_followup` | T+30 min | patient (SMS) | dose still not logged |
| `caregiver_alert`  | T+60 min | caregivers (SMS) | dose still not logged |

SMS is the primary channel (Twilio, already wired). A dose logged as taken
**or** explicitly missed halts further escalation.

## Architecture

Two processes on Railway, one shared database:

```
web service            worker service
streamlit web_app.py   python src/main.py --start   (the engine)
        \                      /
         \                    /
          Supabase Postgres  (shared state — the coherence requirement)
                   |
                   v
              Twilio SMS
```

**Why shared Supabase is mandatory:** web and worker are separate Railway
containers with separate filesystems. SQLite (a local file) cannot be seen by
both. The worker answering "did the patient log this dose?" requires reading
the same rows the web app writes. Both processes select the Supabase backend
via `utils.db_factory.get_database()` when `SUPABASE_URL`/`SUPABASE_KEY` are
set. SQLite remains local-dev only.

## Locked decisions

1. **Timezone — single `APP_TIMEZONE`.** All `HH:MM` dose times are
   interpreted in one deployment-wide timezone (env `APP_TIMEZONE`, e.g.
   `America/New_York`). `scheduled_time`/`actual_time` are naive TEXT columns;
   this is the documented ceiling. Per-user timezones (a `users.timezone`
   column) is the eventual fix and is out of scope here.
2. **Catch-up — most-advanced stage only.** After worker downtime, an overdue
   dose sends only the single most-advanced due stage (e.g. a 70-min-overdue,
   unlogged dose sends the caregiver alert). Earlier stages are recorded as
   *superseded* in the ledger so they never fire late. No burst of texts.
3. **No auto-miss.** The engine never writes dose data. Adherence continues to
   count only explicitly logged doses. The worker's only patient-data access is
   read-only (via `SYSTEM_CALLER`); its sole writes are to its own
   `notification_log` ledger.

## The reconciliation model

The engine does **not** hold per-dose timers in memory. Every minute it
recomputes desired state from the DB and sends whatever is due but unsent.
This is what makes it **restart-safe** — it closes the old "in-process
APScheduler loses pending reminders on restart" limitation.

`tick(db, notifier, now)` — a pure, injectable function (inject `now` and a
fake `notifier` → fully unit-testable, no real clock, no real SMS):

```
now    = current time in APP_TIMEZONE
today  = now.date()
for med in active medications (role=patient, read as SYSTEM_CALLER):
    if med.frequency == 'as_needed':  continue          # never nag PRN meds
    for dose_time in med.times:
        scheduled = today @ dose_time in APP_TIMEZONE
        delta_min = minutes(now - scheduled)
        if delta_min < 0:  continue                      # future dose
        logged = db.get_dose_log_for_date(SYSTEM_CALLER, ...) is not None

        due = []
        if delta_min >= 0  and not logged: due += ['patient_reminder']
        if delta_min >= 30 and not logged: due += ['patient_followup']
        if delta_min >= 60 and not logged: due += ['caregiver_alert']

        # send only the highest not-yet-sent stage; supersede the rest
        target = highest stage in `due` where not db.notification_sent(...)
        for earlier unsent stage below target: db.record_notification(...)  # supersede, no send
        if target and send(target) succeeds: db.record_notification(target)
```

### Idempotency

Every send is gated by `notification_sent(...)`, backed by a UNIQUE
constraint on `(patient_id, medication_name, scheduled_time, date, stage)`.
Running the tick twice, or restarting mid-tick, never double-texts.

## Data model — `notification_log`

```
id, patient_id, medication_name, scheduled_time, date, stage, sent_at
UNIQUE(patient_id, medication_name, scheduled_time, date, stage)
```

`stage ∈ {patient_reminder, patient_followup, caregiver_alert}`. A superseded
stage is recorded the same way as a sent one — the ledger records "this stage
will not fire," whether because it was sent or skipped. (The dead `reminders`
table is unrelated and left for a later cleanup.)

## What exists vs. what's built

**Reuse:** `notifications.send_sms` (Twilio); `SYSTEM_CALLER` +
`get_patient_medications(SYSTEM_CALLER, …)`; `get_dose_log_for_date`
(the escalation predicate); `get_family_circle_members`; `main.py --start`
worker entrypoint; `db_factory.get_database()`.

**Build (staged, one commit each):**
1. `notification_log` table (both backends + `supabase_schema.sql`) +
   `record_notification`/`notification_sent` (idempotent) +
   `get_caregiver_contacts(patient_id)` (family members with a phone, deduped).
2. `send_dose_followup` + `send_caregiver_alert` in `notifications.py`.
3. `services/reminder_engine.py` `tick()` (the logic above; the bulk of tests).
4. Rework `scheduler.py`: one `IntervalTrigger(minutes=1)` → `tick`; keep the
   weekly-report cron; build DB via `get_database()` (fixes the `scheduler.py`
   hardcoded SQLite import); set the scheduler timezone to `APP_TIMEZONE`.
5. Deploy config: `Procfile`, `.python-version`, env docs, README update.

## Deployment (Railway)

`Procfile`:
```
web:    streamlit run src/web_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
worker: python src/main.py --start
```

- **web** binds Railway's `$PORT`; `--headless true` suppresses the browser/
  telemetry prompt.
- **worker** has no port; run **exactly one** instance (the ledger makes
  duplicates safe, but one is correct and cheaper).
- Pin Python with `.python-version` = `3.11` (matches README + CI).

Environment variables (set in Railway, shared to both services unless noted):

| Var | web | worker | Notes |
|-----|-----|--------|-------|
| `SUPABASE_URL`, `SUPABASE_KEY` | ✓ | ✓ | Forces the shared Supabase backend. |
| `TWILIO_ACCOUNT_SID` / `AUTH_TOKEN` / `PHONE_NUMBER` | ✓ | ✓ | web sends OTP, worker sends reminders. |
| `MEDSYNC_OTP_SECRET` | ✓ | – | OTP hashing (web only). |
| `APP_TIMEZONE` | ✓ | ✓ | Dose scheduling + display. |
| `APP_BASE_URL` | ✓ | – | Public base for emailed verify/reset links; defaults to localhost. |
| `EMAIL_*` | ✓ | ✓ | Optional fallback / weekly reports. |

## Known limitations (document, don't fix here)

- Timezone-naive scheduling; per-user timezone is the real fix.
- `dose_logs.medication_name` is denormalized text, so escalation keys off
  `(name, scheduled_time)`; mitigated by the medication name-lock already
  shipped.
- Per-minute full scan of active meds is fine at current scale; add a
  due-dose query/index if patient volume grows.
