import pytest

from services import auth_service
from services.errors import AuthenticationError, AuthorizationError, ValidationError


def test_register_creates_student_with_profile_row(conn):
    u = auth_service.register_student(conn, " New@Mail.com ", "Password123", "New Student")
    assert u.role == "student" and u.email == "new@mail.com"
    assert conn.execute("SELECT COUNT(*) FROM student_profiles WHERE user_id = ?", (u.id,)).fetchone()[0] == 1

def test_password_is_hashed_never_plaintext(conn):
    auth_service.register_student(conn, "a@b.co", "Password123", "A")
    h = conn.execute("SELECT password_hash FROM users").fetchone()[0]
    assert "Password123" not in h and h.startswith("$2") and auth_service.verify_password("Password123", h)
    assert not auth_service.verify_password("wrong-password", h)

def test_same_password_gets_different_salts(conn):
    auth_service.register_student(conn, "a@b.co", "Password123", "A")
    auth_service.register_student(conn, "c@d.co", "Password123", "C")
    hs = [r[0] for r in conn.execute("SELECT password_hash FROM users")]
    assert hs[0] != hs[1]

def test_duplicate_email_rejected_case_insensitively(conn):
    auth_service.register_student(conn, "a@b.co", "Password123", "A")
    with pytest.raises(ValidationError):
        auth_service.register_student(conn, "A@B.CO", "Password123", "Again")

@pytest.mark.parametrize("email,pw,name", [("bad", "Password123", "A"), ("a@b.co", "short", "A"),
                                           ("a@b.co", "x" * 80, "A"), ("a@b.co", "Password123", "  ")])
def test_registration_validation(conn, email, pw, name):
    with pytest.raises(ValidationError):
        auth_service.register_student(conn, email, pw, name)

def test_login_success_and_case_insensitive_email(conn, student):
    assert auth_service.login(conn, "ASHA@college.edu", "StudentPass1").id == student.id

def test_login_wrong_password_and_unknown_email_same_message(conn, student):
    with pytest.raises(AuthenticationError) as a:
        auth_service.login(conn, "asha@college.edu", "nope-nope-1")
    with pytest.raises(AuthenticationError) as b:
        auth_service.login(conn, "ghost@college.edu", "nope-nope-1")
    assert str(a.value) == str(b.value) == "Invalid email or password."

def test_sql_injection_attempts_fail_safely(conn, student):
    for evil in ("' OR '1'='1", "asha@college.edu' --", "x'; DROP TABLE users; --"):
        with pytest.raises(AuthenticationError):
            auth_service.login(conn, evil, "' OR '1'='1")
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1   # table intact

def test_injection_in_name_is_stored_literally(conn):
    u = auth_service.register_student(conn, "q@b.co", "Password123", "Robert'); DROP TABLE users;--")
    assert conn.execute("SELECT full_name FROM users WHERE id = ?", (u.id,)).fetchone()[0].startswith("Robert')")

def test_lockout_after_repeated_failures(conn, student):
    for _ in range(auth_service.MAX_FAILED_LOGINS):
        with pytest.raises(AuthenticationError):
            auth_service.login(conn, "asha@college.edu", "wrong-pass-1")
    with pytest.raises(AuthenticationError) as e:
        auth_service.login(conn, "asha@college.edu", "StudentPass1")   # even the right password
    assert "Too many" in str(e.value)

def test_inactive_user_cannot_login(conn, student):
    conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (student.id,))
    with pytest.raises(AuthenticationError):
        auth_service.login(conn, "asha@college.edu", "StudentPass1")
    assert auth_service.get_user(conn, student.id) is None

def test_first_admin_only_once(conn):
    assert not auth_service.admin_exists(conn)
    a = auth_service.create_first_admin(conn, "boss@c.edu", "BossPass123", "Boss")
    assert a.role == "admin" and auth_service.admin_exists(conn)
    with pytest.raises(AuthorizationError):
        auth_service.create_first_admin(conn, "evil@c.edu", "EvilPass123", "Evil")

def test_student_cannot_create_admin(conn, student, admin):
    with pytest.raises(AuthorizationError):
        auth_service.create_admin(conn, student, "x@c.edu", "Password123", "X")
    assert auth_service.create_admin(conn, admin, "x@c.edu", "Password123", "X").role == "admin"

def test_public_registration_has_no_role_parameter(conn):
    import inspect
    assert "role" not in inspect.signature(auth_service.register_student).parameters
