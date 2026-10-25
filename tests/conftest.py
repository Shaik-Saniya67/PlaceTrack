import os
from datetime import datetime, timedelta, timezone

os.environ["PLACETRACK_BCRYPT_ROUNDS"] = "4"   # fast hashing in tests only

import pytest

from database.db import connect, init_db
from services import auth_service
from services.models import Drive, Profile

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def now():
    return NOW


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    monkeypatch.setenv("PLACETRACK_DB", path)
    return path


@pytest.fixture
def conn(db_file):
    c = connect(db_file)
    init_db(c, seed_samples=False)
    auth_service.reset_throttle()
    yield c
    c.close()


@pytest.fixture
def admin(conn):
    return auth_service.create_first_admin(conn, "admin@college.edu", "AdminPass123", "Ada Admin")


@pytest.fixture
def student(conn):
    return auth_service.register_student(conn, "asha@college.edu", "StudentPass1", "Asha Rao")


@pytest.fixture
def other_student(conn):
    return auth_service.register_student(conn, "ravi@college.edu", "StudentPass2", "Ravi Kumar")


def make_profile(**kw):
    base = dict(user_id=1, department="CSE", graduation_year=2027, cgpa=8.0, backlogs=0)
    base.update(kw)
    return Profile(**base)


def make_drive(**kw):
    base = dict(id=1, company_name="Acme", role_title="SDE", status="published", min_cgpa=7.0,
                eligible_departments=("CSE", "IT"), eligible_years=(2027,), max_backlogs=0,
                deadline=NOW + timedelta(days=5))
    base.update(kw)
    return Drive(**base)


GOOD_PROFILE = {"department": "CSE", "graduation_year": 2027, "cgpa": 8.2, "backlogs": 0, "skills": "Python, SQL"}


def drive_payload(**kw):
    base = {"company_name": "Acme", "role_title": "SDE", "package_lpa": 6, "min_cgpa": 7,
            "eligible_departments": ["CSE"], "eligible_years": [2027], "max_backlogs": 0,
            "deadline": datetime.now(timezone.utc) + timedelta(days=10), "application_url": "https://acme.example/jobs"}
    base.update(kw)
    return base


@pytest.fixture
def ready_student(conn, student):
    """A student with a complete profile."""
    from services.profile_service import save_profile
    save_profile(conn, student, "Asha Rao", GOOD_PROFILE)
    return student


@pytest.fixture
def open_drive(conn, admin):
    from services import drive_service
    d = drive_service.create_drive(conn, admin, drive_payload())
    return drive_service.set_drive_status(conn, admin, d.id, "published")
