"""Placement drive queries and admin management."""
import json
from typing import Optional

from database.db import transaction
from services.errors import InvalidTransitionError, NotFoundError
from services.models import Drive
from services.permissions import require_admin, require_role
from services.statuses import DriveStatus, can_transition_drive
from services.timeutil import now_utc, to_iso_utc
from services.validators import validate_drive


def list_drives(conn, actor) -> list:
    """Admins: every drive. Students: published drives plus any drive they are already tracking."""
    me = require_role(conn, actor, "student", "admin")
    if me.role == "admin":
        rows = conn.execute("SELECT * FROM placement_drives ORDER BY deadline IS NULL, deadline, id").fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM placement_drives
               WHERE status = 'published'
                  OR id IN (SELECT drive_id FROM applications WHERE student_id = ?)
               ORDER BY deadline IS NULL, deadline, id""", (me.id,)).fetchall()
    return [Drive.from_row(r) for r in rows]


def list_open_drives(conn, actor) -> list:
    return [d for d in list_drives(conn, actor) if d.status == DriveStatus.PUBLISHED.value]


def get_drive(conn, actor, drive_id: int) -> Drive:
    visible = [d for d in list_drives(conn, actor) if d.id == drive_id]
    if not visible:
        raise NotFoundError("Drive not found.")
    return visible[0]


def _params(c: dict) -> tuple:
    return (c["company_name"], c["role_title"], c["package_lpa"], c["description"], c["location"], c["min_cgpa"],
            json.dumps(c["eligible_departments"]), json.dumps(c["eligible_years"]), c["max_backlogs"],
            c["deadline"], c["application_url"])


def create_drive(conn, actor, data: dict) -> Drive:
    me = require_admin(conn, actor)
    clean = validate_drive(data)
    with transaction(conn):
        cur = conn.execute(
            """INSERT INTO placement_drives (company_name, role_title, package_lpa, description, location, min_cgpa,
                 eligible_departments, eligible_years, max_backlogs, deadline, application_url, status, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)""", _params(clean) + (me.id,))
        drive_id = cur.lastrowid
    return get_drive(conn, me, drive_id)


def update_drive(conn, actor, drive_id: int, data: dict) -> Drive:
    me = require_admin(conn, actor)
    clean = validate_drive(data)
    with transaction(conn):
        cur = conn.execute(
            """UPDATE placement_drives SET company_name = ?, role_title = ?, package_lpa = ?, description = ?,
                 location = ?, min_cgpa = ?, eligible_departments = ?, eligible_years = ?, max_backlogs = ?,
                 deadline = ?, application_url = ?, updated_at = ? WHERE id = ?""",
            _params(clean) + (to_iso_utc(now_utc()), drive_id))
        if cur.rowcount == 0:
            raise NotFoundError("Drive not found.")
    return get_drive(conn, me, drive_id)


def set_drive_status(conn, actor, drive_id: int, new_status) -> Drive:
    """Publish / close / re-open with a validated lifecycle."""
    me = require_admin(conn, actor)
    new_status = DriveStatus(new_status)
    with transaction(conn):
        row = conn.execute("SELECT status FROM placement_drives WHERE id = ?", (drive_id,)).fetchone()
        if row is None:
            raise NotFoundError("Drive not found.")
        if not can_transition_drive(row["status"], new_status):
            raise InvalidTransitionError(f"A {row['status']} drive cannot become {new_status.value}.")
        conn.execute("UPDATE placement_drives SET status = ?, updated_at = ? WHERE id = ?",
                     (new_status.value, to_iso_utc(now_utc()), drive_id))
    return get_drive(conn, me, drive_id)


def filter_drives(drives, search: str = "", companies: Optional[list] = None, location: str = "",
                  min_package: Optional[float] = None, department: str = "") -> list:
    q, loc = (search or "").strip().lower(), (location or "").strip().lower()
    out = []
    for d in drives:
        if q and q not in d.company_name.lower() and q not in d.role_title.lower() and q not in d.description.lower():
            continue
        if companies and d.company_name not in companies:
            continue
        if loc and loc not in (d.location or "").lower():
            continue
        if min_package and (d.package_lpa is None or d.package_lpa < min_package):
            continue
        if department and d.eligible_departments and department not in d.eligible_departments:
            continue
        out.append(d)
    return out
