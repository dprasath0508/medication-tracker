"""Single authorization chokepoint for patient-scoped data access.

Every patient-scoped method in both DB backends (SQLite ``MedicationDB`` in
``database.py``, Supabase ``MedicationDB`` in ``database_supabase.py``) calls
``_assert_can_access_patient`` as its first statement. There are no bypass
variants. See HARDENING_SPRINT.md, Finding 1.

Policy:
- A patient always has access to themselves.
- ``read`` requires sharing a family circle with the patient and holding the
  ``view`` permission in that circle.
- ``write`` requires sharing a circle and holding ``manage_meds``.
- ``SYSTEM_CALLER`` (background services) may read, never write.
- Denial raises :class:`AuthorizationError` — never an empty result.
"""

from __future__ import annotations

_LEVEL_PERMISSION = {"read": "view", "write": "manage_meds"}


class AuthorizationError(Exception):
    """Raised when a caller is not entitled to a patient's data.

    Raised instead of returning an empty result on purpose: a silent empty
    hides the bug and reads as correct behavior.
    """

    def __init__(self, caller_id, patient_id, level):
        self.caller_id = caller_id
        self.patient_id = patient_id
        self.level = level
        super().__init__(
            f"Caller {caller_id!r} is not authorized for {level!r} access "
            f"to patient {patient_id!r}"
        )


class _SystemCaller:
    """Unforgeable identity for trusted background services.

    Not an int, so no user-supplied identifier (e.g. a ``?patient=`` query
    param) can ever resolve to it. Read-only: writes as SYSTEM_CALLER raise.
    """

    __slots__ = ()

    def __repr__(self):
        return "SYSTEM_CALLER"


SYSTEM_CALLER = _SystemCaller()


class PatientAuthorizationMixin:
    """Authorization policy shared by both DB backends.

    Backends supply ``_get_caller_permissions_for_patient(caller_id,
    patient_id) -> set[str]``: the union of the caller's permissions across
    family circles shared with the patient (empty set if none).
    """

    def _assert_can_access_patient(self, caller_id, patient_id, level) -> None:
        if level not in _LEVEL_PERMISSION:
            raise ValueError(f"Unknown access level: {level!r}")

        if caller_id is SYSTEM_CALLER:
            if level == "read":
                return
            raise AuthorizationError(caller_id, patient_id, level)

        if not isinstance(caller_id, int) or isinstance(caller_id, bool):
            raise AuthorizationError(caller_id, patient_id, level)

        if caller_id == patient_id:
            return

        permissions = self._get_caller_permissions_for_patient(caller_id, patient_id)
        if _LEVEL_PERMISSION[level] not in permissions:
            raise AuthorizationError(caller_id, patient_id, level)
