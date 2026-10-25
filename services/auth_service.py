"""Registration, login and account helpers. Passwords are hashed with bcrypt (salted, adaptive)."""
import os
import sqlite3
import time

import bcrypt

from database.db import transaction
from services.errors import AuthenticationError, AuthorizationError, ValidationError
from services.models import User
from services.validators import validate_email_password

MAX_FAILED_LOGINS = 5
LOCK_SECONDS = 300
_failed: dict = {}          # email -> [timestamps]; in-process throttle against password guessing
_dummy_hash = None


def _rounds() -> int:
    return int(os.getenv("PLACETRACK_BCRYPT_ROUNDS", "12"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_rounds())).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def reset_throttle() -> None:
    _failed.clear()


def _locked(email: str) -> bool:
    recent = [t for t in _failed.get(email, []) if time.time() - t < LOCK_SECONDS]
    _failed[email] = recent
    return len(recent) >= MAX_FAILED_LOGINS


def _create_user(conn, email, password, full_name, role) -> User:
    email, full_name = validate_email_password(email, password, full_name)
    pw_hash = hash_password(password)
    try:
        with transaction(conn):
            cur = conn.execute("INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                               (email, pw_hash, full_name, role))
            uid = cur.lastrowid
            if role == "student":
                conn.execute("INSERT INTO student_profiles (user_id) VALUES (?)", (uid,))
    except sqlite3.IntegrityError as exc:
        raise ValidationError("An account with this email already exists.") from exc
    return User(id=uid, email=email, full_name=full_name, role=role)


def register_student(conn, email, password, full_name) -> User:
    """Public sign-up. The role is hard-coded: nobody can register themselves as an admin."""
    return _create_user(conn, email, password, full_name, "student")


def admin_exists(conn) -> bool:
    return conn.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone() is not None


def create_first_admin(conn, email, password, full_name) -> User:
    """One-time bootstrap, refused as soon as any admin exists."""
    if admin_exists(conn):
        raise AuthorizationError("An administrator already exists.")
    return _create_user(conn, email, password, full_name, "admin")


def create_admin(conn, actor, email, password, full_name) -> User:
    """Existing admins can add further admins."""
    from services.permissions import require_admin
    require_admin(conn, actor)
    return _create_user(conn, email, password, full_name, "admin")


def login(conn, email, password) -> User:
    global _dummy_hash
    email = (email or "").strip().lower()
    if _locked(email):
        raise AuthenticationError("Too many failed attempts. Please try again in a few minutes.")
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None:  # still burn the same CPU time so response time does not reveal valid emails
        _dummy_hash = _dummy_hash or hash_password("placeholder-password")
        verify_password(password or "", _dummy_hash)
        ok = False
    else:
        ok = verify_password(password or "", row["password_hash"]) and bool(row["is_active"])
    if not ok:
        _failed.setdefault(email, []).append(time.time())
        raise AuthenticationError("Invalid email or password.")
    _failed.pop(email, None)
    return User.from_row(row)


def get_user(conn, user_id):
    if user_id is None:
        return None
    row = conn.execute("SELECT id, email, full_name, role, is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    return User.from_row(row) if row and row["is_active"] else None
