from dataclasses import replace

import pytest

from services import application_service as svc
from services import drive_service, notification_service, profile_service
from services.errors import AuthorizationError, NotFoundError
from services.statuses import ApplicationStatus as S
from tests.conftest import GOOD_PROFILE, drive_payload


def test_student_cannot_manage_drives(conn, student, open_drive):
    with pytest.raises(AuthorizationError):
        drive_service.create_drive(conn, student, drive_payload())
    with pytest.raises(AuthorizationError):
        drive_service.update_drive(conn, student, open_drive.id, drive_payload())
    with pytest.raises(AuthorizationError):
        drive_service.set_drive_status(conn, student, open_drive.id, "closed")

def test_student_cannot_use_admin_listings(conn, student):
    with pytest.raises(AuthorizationError):
        svc.list_applications_admin(conn, student)

def test_admin_cannot_use_student_only_features(conn, admin, open_drive):
    with pytest.raises(AuthorizationError):
        svc.create_application(conn, admin, open_drive)
    with pytest.raises(AuthorizationError):
        svc.list_my_applications(conn, admin)
    with pytest.raises(AuthorizationError):
        profile_service.get_profile(conn, admin)

def test_students_cannot_see_draft_drives(conn, admin, student):
    d = drive_service.create_drive(conn, admin, drive_payload(company_name="Secret"))
    assert d.status == "draft"
    assert "Secret" not in [x.company_name for x in drive_service.list_drives(conn, student)]
    with pytest.raises(NotFoundError):
        drive_service.get_drive(conn, student, d.id)
    assert "Secret" in [x.company_name for x in drive_service.list_drives(conn, admin)]

def test_student_keeps_access_to_closed_drive_they_tracked(conn, admin, ready_student, open_drive):
    svc.create_application(conn, ready_student, open_drive)
    drive_service.set_drive_status(conn, admin, open_drive.id, "closed")
    assert open_drive.id in [d.id for d in drive_service.list_drives(conn, ready_student)]

def test_student_cannot_update_others_application(conn, ready_student, other_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive)
    with pytest.raises(AuthorizationError):
        svc.update_application(conn, other_student, app.id, S.APPLIED)
    with pytest.raises(AuthorizationError):
        svc.list_events(conn, other_student, app.id)
    assert svc.list_my_applications(conn, other_student) == []

def test_admin_can_update_any_application(conn, admin, ready_student, open_drive):
    app = svc.create_application(conn, ready_student, open_drive, S.APPLIED)
    assert svc.update_application(conn, admin, app.id, S.REJECTED).status is S.REJECTED

def test_forged_role_on_user_object_is_ignored(conn, student):
    fake_admin = replace(student, role="admin")        # attacker edits the object, not the database
    with pytest.raises(AuthorizationError):
        drive_service.create_drive(conn, fake_admin, drive_payload())
    with pytest.raises(AuthorizationError):
        svc.list_applications_admin(conn, fake_admin)

def test_deactivated_user_loses_access(conn, student):
    conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (student.id,))
    with pytest.raises(AuthorizationError):
        svc.list_my_applications(conn, student)

def test_anonymous_actor_rejected(conn):
    with pytest.raises(AuthorizationError):
        drive_service.list_drives(conn, None)

def test_profile_isolation(conn, student, other_student, admin):
    profile_service.save_profile(conn, student, "Asha", GOOD_PROFILE)
    with pytest.raises(AuthorizationError):
        profile_service.get_profile_by_id(conn, other_student, student.id)
    assert profile_service.get_profile_by_id(conn, admin, student.id).cgpa == 8.2
    assert profile_service.get_profile_by_id(conn, student, student.id).department == "CSE"

def test_profile_save_cannot_change_role(conn, student):
    profile_service.save_profile(conn, student, "Asha", {**GOOD_PROFILE, "role": "admin"})
    assert conn.execute("SELECT role FROM users WHERE id = ?", (student.id,)).fetchone()[0] == "student"

def test_notifications_are_private(conn, ready_student, other_student, admin, open_drive):
    app = svc.create_application(conn, ready_student, open_drive, S.APPLIED)
    svc.update_application(conn, admin, app.id, S.ASSESSMENT)
    n = notification_service.list_notifications(conn, ready_student)[0]
    notification_service.mark_read(conn, other_student, n["id"])          # silently ignored for non-owner
    assert notification_service.unread_count(conn, ready_student) == 1
    assert notification_service.list_notifications(conn, other_student) == []
    notification_service.mark_read(conn, ready_student, n["id"])
    assert notification_service.unread_count(conn, ready_student) == 0
