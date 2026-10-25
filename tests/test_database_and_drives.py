import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from database.db import connect, init_db, transaction
from database.seed import SAMPLES
from services import analytics_service as an
from services import drive_service
from services.errors import InvalidTransitionError, ValidationError
from services.statuses import ApplicationStatus as S
from tests.conftest import drive_payload, make_drive


def test_all_required_tables_exist(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "student_profiles", "placement_drives", "applications", "application_events", "notifications"} <= names

def test_init_is_idempotent_and_foreign_keys_on(db_file):
    c = connect(db_file)
    init_db(c, seed_samples=False)
    init_db(c, seed_samples=False)
    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    c.close()

def test_indexes_present(conn):
    idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_applications_student", "idx_drives_status_deadline", "idx_notifications_user"} <= idx

def test_foreign_key_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO applications (student_id, drive_id) VALUES (999, 999)")

def test_check_constraints(conn, student):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE student_profiles SET cgpa = 11 WHERE user_id = ?", (student.id,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO placement_drives (company_name, role_title, status) VALUES ('a','b','weird')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO placement_drives (company_name, role_title, application_url) VALUES ('a','b','javascript:x')")

def test_deleting_student_cascades(conn, ready_student, open_drive):
    from services import application_service as svc
    svc.create_application(conn, ready_student, open_drive)
    conn.execute("DELETE FROM users WHERE id = ?", (ready_student.id,))
    assert conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM application_events").fetchone()[0] == 0

def test_cannot_delete_drive_with_applications(conn, ready_student, open_drive):
    from services import application_service as svc
    svc.create_application(conn, ready_student, open_drive)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM placement_drives WHERE id = ?", (open_drive.id,))

def test_transaction_rolls_back_on_error(conn):
    with pytest.raises(RuntimeError):
        with transaction(conn):
            conn.execute("INSERT INTO placement_drives (company_name, role_title) VALUES ('X','Y')")
            raise RuntimeError("boom")
    assert conn.execute("SELECT COUNT(*) FROM placement_drives").fetchone()[0] == 0

def test_sample_seed_runs_once(db_file):
    c = connect(db_file)
    init_db(c)
    init_db(c)
    assert c.execute("SELECT COUNT(*) FROM placement_drives").fetchone()[0] == len(SAMPLES)
    assert c.execute("SELECT COUNT(*) FROM placement_drives WHERE is_sample = 1").fetchone()[0] == len(SAMPLES)
    c.close()

# --- drive service ---------------------------------------------------
def test_admin_drive_lifecycle(conn, admin):
    d = drive_service.create_drive(conn, admin, drive_payload())
    assert d.status == "draft" and d.eligible_departments == ("CSE",)
    d = drive_service.update_drive(conn, admin, d.id, drive_payload(company_name="Acme Corp", min_cgpa=7.5))
    assert d.company_name == "Acme Corp" and d.min_cgpa == 7.5
    assert drive_service.set_drive_status(conn, admin, d.id, "published").status == "published"
    assert drive_service.set_drive_status(conn, admin, d.id, "closed").status == "closed"
    assert drive_service.set_drive_status(conn, admin, d.id, "published").status == "published"  # re-open

def test_cannot_close_a_draft(conn, admin):
    d = drive_service.create_drive(conn, admin, drive_payload())
    with pytest.raises(InvalidTransitionError):
        drive_service.set_drive_status(conn, admin, d.id, "closed")

@pytest.mark.parametrize("patch", [{"company_name": ""}, {"min_cgpa": 11}, {"max_backlogs": -2},
                                   {"application_url": "javascript:alert(1)"}, {"application_url": "ftp://x.io"},
                                   {"eligible_departments": ["Wizardry"]}, {"package_lpa": -3}, {"deadline": "tomorrow"}])
def test_drive_validation(conn, admin, patch):
    with pytest.raises(ValidationError):
        drive_service.create_drive(conn, admin, drive_payload(**patch))

def test_drive_sql_injection_is_inert(conn, admin):
    d = drive_service.create_drive(conn, admin, drive_payload(company_name="x'); DROP TABLE users;--"))
    assert d.company_name.startswith("x')") and conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1

def test_filter_drives():
    ds = [make_drive(id=1, company_name="Acme", location="Pune", package_lpa=5),
          make_drive(id=2, company_name="Globex", role_title="Analyst", location="Delhi", package_lpa=12, eligible_departments=("ECE",))]
    f = drive_service.filter_drives
    assert [d.id for d in f(ds, search="analy")] == [2]
    assert [d.id for d in f(ds, companies=["Acme"])] == [1]
    assert [d.id for d in f(ds, location="del")] == [2]
    assert [d.id for d in f(ds, min_package=10)] == [2]
    assert [d.id for d in f(ds, department="CSE")] == [1]
    assert len(f(ds)) == 2

# --- analytics -------------------------------------------------------
def test_status_counts_and_metrics(conn, ready_student, open_drive):
    from services import application_service as svc
    app = svc.create_application(conn, ready_student, open_drive, S.APPLIED)
    apps = svc.list_my_applications(conn, ready_student)
    df = an.status_counts(apps)
    assert len(df) == 8 and df["count"].sum() == 1 and df.set_index("status").loc["Applied", "count"] == 1
    assert an.summary_metrics(apps) == {"total": 1, "active": 1, "interviews": 0, "selected": 0}
    assert not an.drive_application_matrix(apps).empty and len(an.applications_over_time(apps)) == 1

def test_upcoming_deadlines_and_interviews(conn, ready_student, open_drive, now):
    from services import application_service as svc
    ds = [make_drive(id=1, deadline=now + timedelta(days=9)), make_drive(id=2, deadline=now + timedelta(days=2)),
          make_drive(id=3, deadline=now + timedelta(days=40)), make_drive(id=4, deadline=now - timedelta(days=1))]
    assert [d.id for d in an.upcoming_deadlines(ds, 14, now)] == [2, 1]
    app = svc.create_application(conn, ready_student, open_drive, S.APPLIED)
    when = datetime.now(timezone.utc) + timedelta(days=1)
    svc.update_application(conn, ready_student, app.id, S.TECHNICAL_INTERVIEW, interview_at=when)
    assert len(an.upcoming_interviews(svc.list_my_applications(conn, ready_student))) == 1

def test_reminders_are_deduplicated(conn, ready_student, admin):
    from services import notification_service as ns
    d = drive_service.create_drive(conn, admin, drive_payload(deadline=datetime.now(timezone.utc) + timedelta(days=1)))
    drive_service.set_drive_status(conn, admin, d.id, "published")
    assert ns.refresh_reminders(conn, ready_student) == 1
    assert ns.refresh_reminders(conn, ready_student) == 0
    assert "closes" in ns.list_notifications(conn, ready_student)[0]["message"]
