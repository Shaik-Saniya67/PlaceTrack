"""Application tracking, history and permissions.

PlaceTrack records the student's own progress. It never submits anything to a company portal.
"""
import sqlite3
from typing import Optional

from database.db import transaction
from services.errors import (AuthorizationError, DuplicateApplicationError, NotEligibleError,
                             NotFoundError, ValidationError)
from services.eligibility_service import evaluate_eligibility
from services.models import Application, Drive
from services.permissions import require_admin, require_role, require_student
from services.profile_service import get_profile
from services.statuses import ApplicationStatus, validate_transition
from services.timeutil import now_utc, to_iso_utc

_DRIVE_COLS = ["id", "company_name", "role_title", "package_lpa", "description", "location", "min_cgpa",
               "eligible_departments", "eligible_years", "max_backlogs", "deadline", "application_url",
               "status", "is_sample"]
_SELECT = ("SELECT a.*, " + ", ".join(f"d.{c} AS d_{c}" for c in _DRIVE_COLS) +
           ", u.full_name AS s_name, u.email AS s_email, p.department AS s_dept, p.cgpa AS s_cgpa "
           "FROM applications a JOIN placement_drives d ON d.id = a.drive_id "
           "JOIN users u ON u.id = a.student_id LEFT JOIN student_profiles p ON p.user_id = a.student_id ")
_UNSET = object()


def _one(conn, application_id: int) -> Application:
    row = conn.execute(_SELECT + "WHERE a.id = ?", (application_id,)).fetchone()
    if row is None:
        raise NotFoundError("Application not found.")
    return Application.from_row(row)


def list_my_applications(conn, actor) -> list:
    me = require_student(conn, actor)
    rows = conn.execute(_SELECT + "WHERE a.student_id = ? ORDER BY a.updated_at DESC, a.id DESC", (me.id,)).fetchall()
    return [Application.from_row(r) for r in rows]


def list_applications_admin(conn, actor, drive_id: Optional[int] = None) -> list:
    require_admin(conn, actor)
    if drive_id is None:
        rows = conn.execute(_SELECT + "ORDER BY a.updated_at DESC, a.id DESC").fetchall()
    else:
        rows = conn.execute(_SELECT + "WHERE a.drive_id = ? ORDER BY a.updated_at DESC, a.id DESC", (drive_id,)).fetchall()
    return [Application.from_row(r) for r in rows]


def create_application(conn, actor, drive: Drive, status=ApplicationStatus.INTERESTED, now=None) -> Application:
    """Track a drive as Interested, or record that the student applied on the company's own site."""
    me = require_student(conn, actor)
    status = ApplicationStatus(status)
    if status not in (ApplicationStatus.INTERESTED, ApplicationStatus.APPLIED):
        raise ValidationError("A new application must start as Interested or Applied.")
    with transaction(conn):
        # Re-read the drive and profile inside the transaction so decisions use current data.
        row = conn.execute("SELECT * FROM placement_drives WHERE id = ?", (drive.id,)).fetchone()
        if row is None:
            raise NotFoundError("Drive not found.")
        fresh_drive = Drive.from_row(row)
        result = evaluate_eligibility(get_profile_in_tx(conn, me.id), fresh_drive, now)
        if not result.is_eligible:
            raise NotEligibleError(result.explanations)
        try:
            cur = conn.execute("INSERT INTO applications (student_id, drive_id, status) VALUES (?, ?, ?)",
                               (me.id, fresh_drive.id, status.value))
        except sqlite3.IntegrityError as exc:
            raise DuplicateApplicationError("You already have an application for this drive.") from exc
        app_id = cur.lastrowid
        _log_event(conn, app_id, None, status.value, me.id)
    return _one(conn, app_id)


def get_profile_in_tx(conn, student_id: int):
    from services.models import Profile
    row = conn.execute("SELECT * FROM student_profiles WHERE user_id = ?", (student_id,)).fetchone()
    return Profile.from_row(row) if row else Profile(user_id=student_id)


def _log_event(conn, app_id, from_status, to_status, changed_by) -> None:
    conn.execute("INSERT INTO application_events (application_id, from_status, to_status, changed_by) VALUES (?, ?, ?, ?)",
                 (app_id, from_status, to_status, changed_by))


def update_application(conn, actor, application_id: int, new_status=None, notes=_UNSET, interview_at=_UNSET) -> Application:
    """Students update only their own records; admins may update any. Stage changes are logged."""
    me = require_role(conn, actor, "student", "admin")
    with transaction(conn):
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if row is None:
            raise NotFoundError("Application not found.")
        if me.role != "admin" and row["student_id"] != me.id:
            raise AuthorizationError("You can only update your own applications.")
        sets, params, changed_stage = [], [], False
        if new_status is not None and ApplicationStatus(new_status).value != row["status"]:
            validate_transition(row["status"], new_status)
            sets.append("status = ?")
            params.append(ApplicationStatus(new_status).value)
            changed_stage = True
        if notes is not _UNSET:
            notes = (notes or "").strip()
            if len(notes) > 2000:
                raise ValidationError("Notes must be at most 2000 characters.")
            sets.append("notes = ?")
            params.append(notes or None)
        if interview_at is not _UNSET:
            sets.append("interview_at = ?")
            params.append(to_iso_utc(interview_at))
        if sets:
            sets.append("updated_at = ?")
            params.append(to_iso_utc(now_utc()))
            conn.execute(f"UPDATE applications SET {', '.join(sets)} WHERE id = ?", (*params, application_id))
        if changed_stage:
            _log_event(conn, application_id, row["status"], ApplicationStatus(new_status).value, me.id)
            if me.id != row["student_id"]:   # tell the student when the placement cell moves their stage
                company = conn.execute("SELECT company_name FROM placement_drives WHERE id = ?",
                                       (row["drive_id"],)).fetchone()["company_name"]
                conn.execute("INSERT INTO notifications (user_id, drive_id, title, message) VALUES (?, ?, ?, ?)",
                             (row["student_id"], row["drive_id"], "Application stage updated",
                              f'Your application to {company} was moved to "{ApplicationStatus(new_status).label}" '
                              f"by the placement team."))
    return _one(conn, application_id)


def list_events(conn, actor, application_id: int) -> list:
    me = require_role(conn, actor, "student", "admin")
    owner = conn.execute("SELECT student_id FROM applications WHERE id = ?", (application_id,)).fetchone()
    if owner is None:
        raise NotFoundError("Application not found.")
    if me.role != "admin" and owner["student_id"] != me.id:
        raise AuthorizationError("You can only view your own application history.")
    rows = conn.execute(
        """SELECT e.id, e.from_status, e.to_status, e.created_at, u.full_name AS changed_by_name, u.role AS changed_by_role
           FROM application_events e LEFT JOIN users u ON u.id = e.changed_by
           WHERE e.application_id = ? ORDER BY e.created_at, e.id""", (application_id,)).fetchall()
    return [dict(r) for r in rows]
