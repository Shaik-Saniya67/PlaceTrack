from database.db import transaction
from services.models import Profile
from services.permissions import require_student
from services.timeutil import to_iso_utc, now_utc
import json


def get_profile(conn, actor) -> Profile:
    me = require_student(conn, actor)
    row = conn.execute("SELECT * FROM student_profiles WHERE user_id = ?", (me.id,)).fetchone()
    if row is None:
        with transaction(conn):
            conn.execute("INSERT OR IGNORE INTO student_profiles (user_id) VALUES (?)", (me.id,))
        row = conn.execute("SELECT * FROM student_profiles WHERE user_id = ?", (me.id,)).fetchone()
    return Profile.from_row(row)


def get_profile_by_id(conn, actor, student_id: int) -> Profile:
    """Admins may read any profile; students only their own."""
    from services.errors import AuthorizationError
    from services.permissions import require_role
    me = require_role(conn, actor, "student", "admin")
    if me.role != "admin" and me.id != student_id:
        raise AuthorizationError("You can only view your own profile.")
    row = conn.execute("SELECT * FROM student_profiles WHERE user_id = ?", (student_id,)).fetchone()
    return Profile.from_row(row) if row else Profile(user_id=student_id)


def save_profile(conn, actor, full_name: str, data: dict) -> Profile:
    from services.errors import ValidationError
    from services.validators import validate_profile
    me = require_student(conn, actor)
    name = (full_name or "").strip()
    if not name or len(name) > 120:
        raise ValidationError("Full name is required (max 120 characters).")
    clean = validate_profile(data)
    with transaction(conn):
        conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (name, me.id))
        conn.execute(
            """INSERT INTO student_profiles (user_id, department, graduation_year, cgpa, backlogs, skills, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET department = excluded.department,
                 graduation_year = excluded.graduation_year, cgpa = excluded.cgpa, backlogs = excluded.backlogs,
                 skills = excluded.skills, updated_at = excluded.updated_at""",
            (me.id, clean["department"], clean["graduation_year"], clean["cgpa"], clean["backlogs"],
             json.dumps(clean["skills"]), to_iso_utc(now_utc())))
    return get_profile(conn, me)
