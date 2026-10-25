import sqlite3
from dataclasses import replace

import pytest

from services import application_service as svc
from services import drive_service
from services.errors import (AuthorizationError, DuplicateApplicationError, InvalidTransitionError,
                             NotEligibleError, ValidationError)
from services.profile_service import save_profile
from services.statuses import ApplicationStatus as S


def test_create_application_logs_initial_event(conn, ready_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive, S.APPLIED)
    assert app.status is S.APPLIED and app.drive.company_name == "Acme"
    ev = svc.list_events(conn, ready_student, app.id)
    assert len(ev) == 1 and ev[0]["from_status"] is None and ev[0]["to_status"] == "applied"

def test_duplicate_application_prevented(conn, ready_student, open_drive):
    svc.create_application(conn, ready_student, open_drive)
    with pytest.raises(DuplicateApplicationError):
        svc.create_application(conn, ready_student, open_drive, S.APPLIED)
    assert conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 1

def test_database_itself_rejects_duplicates(conn, ready_student, open_drive):
    svc.create_application(conn, ready_student, open_drive)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO applications (student_id, drive_id) VALUES (?, ?)", (ready_student.id, open_drive.id))

def test_two_students_may_apply_to_same_drive(conn, ready_student, other_student, open_drive):
    save_profile(conn, other_student, "Ravi", {"department": "CSE", "graduation_year": 2027, "cgpa": 9, "backlogs": 0, "skills": ""})
    svc.create_application(conn, ready_student, open_drive)
    svc.create_application(conn, other_student, open_drive)
    assert len(svc.list_applications_admin(conn, conn_admin(conn), open_drive.id)) == 2

def conn_admin(conn):
    from services.models import User
    r = conn.execute("SELECT * FROM users WHERE role='admin'").fetchone()
    return User.from_row(r)

def test_ineligible_student_is_blocked(conn, student, open_drive):
    save_profile(conn, student, "Asha", {"department": "ECE", "graduation_year": 2027, "cgpa": 8, "backlogs": 0, "skills": ""})
    with pytest.raises(NotEligibleError) as e:
        svc.create_application(conn, student, open_drive)
    assert "not eligible" in str(e.value).lower()
    assert conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0

def test_incomplete_profile_is_unknown_and_blocked(conn, student, open_drive):
    with pytest.raises(NotEligibleError):
        svc.create_application(conn, student, open_drive)

def test_cannot_start_in_late_stage(conn, ready_student, open_drive):
    with pytest.raises(ValidationError):
        svc.create_application(conn, ready_student, open_drive, S.SELECTED)

def test_closed_drive_blocks_new_applications(conn, admin, ready_student, open_drive):
    drive_service.set_drive_status(conn, admin, open_drive.id, "closed")
    with pytest.raises(NotEligibleError):
        svc.create_application(conn, ready_student, open_drive)

# --- transitions & history ---------------------------------------------
def test_status_walk_records_history(conn, ready_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive)
    for s in (S.APPLIED, S.ASSESSMENT, S.TECHNICAL_INTERVIEW, S.HR_INTERVIEW, S.SELECTED):
        app = svc.update_application(conn, ready_student, app.id, s)
    ev = svc.list_events(conn, ready_student, app.id)
    assert [e["to_status"] for e in ev] == ["interested", "applied", "assessment", "technical_interview", "hr_interview", "selected"]
    assert ev[3]["from_status"] == "assessment"

def test_invalid_transition_rejected_and_not_logged(conn, ready_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive)
    with pytest.raises(InvalidTransitionError):
        svc.update_application(conn, ready_student, app.id, S.SELECTED)
    assert len(svc.list_events(conn, ready_student, app.id)) == 1

def test_terminal_status_is_final(conn, ready_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive, S.APPLIED)
    app = svc.update_application(conn, ready_student, app.id, S.REJECTED)
    with pytest.raises(InvalidTransitionError):
        svc.update_application(conn, ready_student, app.id, S.APPLIED)

def test_notes_only_update_makes_no_event(conn, ready_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive)
    app = svc.update_application(conn, ready_student, app.id, notes="prep DSA")
    assert app.notes == "prep DSA" and len(svc.list_events(conn, ready_student, app.id)) == 1

def test_notes_length_limit(conn, ready_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive)
    with pytest.raises(ValidationError):
        svc.update_application(conn, ready_student, app.id, notes="x" * 2001)

def test_failed_update_rolls_back(conn, ready_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive)
    with pytest.raises(ValidationError):   # status change is staged before notes validation fails
        svc.update_application(conn, ready_student, app.id, S.APPLIED, notes="x" * 3000)
    assert svc.list_my_applications(conn, ready_student)[0].status is S.INTERESTED
    assert len(svc.list_events(conn, ready_student, app.id)) == 1

def test_admin_stage_change_notifies_student(conn, admin, ready_student, open_drive):
    from services import notification_service as ns
    app = svc.create_application(conn, ready_student, open_drive, S.APPLIED)
    svc.update_application(conn, admin, app.id, S.ASSESSMENT)
    notes = ns.list_notifications(conn, ready_student)
    assert any("Assessment" in n["message"] for n in notes)
    ev = svc.list_events(conn, ready_student, app.id)
    assert ev[-1]["changed_by_role"] == "admin"
