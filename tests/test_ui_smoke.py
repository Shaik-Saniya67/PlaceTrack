"""Runs every page headlessly (Streamlit AppTest) against a temporary database."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from database.db import connect, init_db  # noqa: E402
from services import application_service, auth_service, drive_service  # noqa: E402
from services.profile_service import save_profile  # noqa: E402
from tests.conftest import GOOD_PROFILE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def world(db_file):
    c = connect(db_file)
    init_db(c)   # seeds the 8 sample drives
    auth_service.reset_throttle()
    admin = auth_service.create_first_admin(c, "admin@c.edu", "AdminPass123", "Ada Admin")
    stu = auth_service.register_student(c, "asha@c.edu", "StudentPass1", "Asha Rao")
    save_profile(c, stu, "Asha Rao", GOOD_PROFILE)
    drive = [d for d in drive_service.list_open_drives(c, stu) if d.company_name.startswith("Northwind")][0]
    application_service.create_application(c, stu, drive, "applied")
    yield {"admin": admin, "student": stu}
    c.close()


def run(page, user=None):
    at = AppTest.from_file(str(ROOT / page), default_timeout=60)
    if user:
        at.session_state["user_id"] = user.id
    at.run()
    return at


@pytest.mark.parametrize("page,who", [
    ("app.py", None), ("app.py", "student"), ("app.py", "admin"),
    ("pages/login.py", None),
    ("pages/student_dashboard.py", "student"), ("pages/drives.py", "student"), ("pages/my_applications.py", "student"),
    ("pages/notifications.py", "student"), ("pages/profile.py", "student"),
    ("pages/admin_dashboard.py", "admin"), ("pages/admin_drives.py", "admin"), ("pages/admin_applications.py", "admin"),
])
def test_page_renders(world, page, who):
    at = run(page, world[who] if who else None)
    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("page", ["pages/admin_dashboard.py", "pages/admin_drives.py", "pages/admin_applications.py"])
def test_student_blocked_from_admin_pages(world, page):
    at = run(page, world["student"])
    assert at.error and "permission" in at.error[0].value.lower() and not at.metric


@pytest.mark.parametrize("page", ["pages/student_dashboard.py", "pages/drives.py", "pages/my_applications.py"])
def test_admin_blocked_from_student_pages(world, page):
    at = run(page, world["admin"])
    assert at.error and "permission" in at.error[0].value.lower()


def test_signed_out_user_is_asked_to_sign_in(world):
    at = run("pages/drives.py")
    assert at.warning and "sign in" in at.warning[0].value.lower()


def test_login_form_signs_user_in(world):
    at = run("pages/login.py")
    at.text_input[0].set_value("asha@c.edu")
    at.text_input[1].set_value("StudentPass1")
    at.button[0].click().run()
    assert not at.exception and at.session_state["user_id"] == world["student"].id


def test_bad_login_shows_error(world):
    at = run("pages/login.py")
    at.text_input[0].set_value("asha@c.edu")
    at.text_input[1].set_value("wrong-password")
    at.button[0].click().run()
    assert at.error and "Invalid" in at.error[0].value


def test_app_creates_database_on_first_run(tmp_path, monkeypatch):
    path = tmp_path / "fresh.db"
    monkeypatch.setenv("PLACETRACK_DB", str(path))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception and path.exists()
    c = connect(str(path))
    assert c.execute("SELECT COUNT(*) FROM placement_drives").fetchone()[0] >= 6
    c.close()
