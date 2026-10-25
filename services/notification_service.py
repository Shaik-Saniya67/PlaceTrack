"""In-app notifications (own rows only). Reminders are computed in Python, deduplicated by a unique key."""
from datetime import timedelta

from database.db import transaction
from services.eligibility_service import evaluate_eligibility
from services.permissions import require_student
from services.profile_service import get_profile
from services.statuses import INTERVIEW_STAGES
from services.timeutil import fmt_dt, now_utc, parse_ts


def refresh_reminders(conn, actor, now=None) -> int:
    me = require_student(conn, actor)
    now = now or now_utc()
    profile = get_profile(conn, me)
    from services.models import Drive
    created = 0
    with transaction(conn):
        soon = [Drive.from_row(r) for r in conn.execute(
            "SELECT * FROM placement_drives WHERE status = 'published' AND deadline IS NOT NULL").fetchall()]
        applied = {r["drive_id"] for r in conn.execute(
            "SELECT drive_id FROM applications WHERE student_id = ? AND status <> 'interested'", (me.id,))}
        for d in soon:
            if d.id in applied or not (now <= d.deadline <= now + timedelta(days=3)):
                continue
            if not evaluate_eligibility(profile, d, now).is_eligible:
                continue
            created += conn.execute(
                "INSERT OR IGNORE INTO notifications (user_id, drive_id, title, message, dedupe_key) VALUES (?, ?, ?, ?, ?)",
                (me.id, d.id, "Deadline approaching",
                 f"{d.company_name} ({d.role_title}) closes on {fmt_dt(d.deadline)}.", f"deadline:{d.id}")).rowcount
        for r in conn.execute(
                """SELECT a.id, a.drive_id, a.interview_at, a.status, d.company_name FROM applications a
                   JOIN placement_drives d ON d.id = a.drive_id
                   WHERE a.student_id = ? AND a.interview_at IS NOT NULL""", (me.id,)):
            when = parse_ts(r["interview_at"])
            if r["status"] in {s.value for s in INTERVIEW_STAGES} and now <= when <= now + timedelta(days=2):
                created += conn.execute(
                    "INSERT OR IGNORE INTO notifications (user_id, drive_id, title, message, dedupe_key) VALUES (?, ?, ?, ?, ?)",
                    (me.id, r["drive_id"], "Upcoming interview / assessment",
                     f"{r['company_name']}: scheduled for {fmt_dt(when)}.", f"interview:{r['id']}:{r['interview_at']}")).rowcount
    return created


def list_notifications(conn, actor, limit: int = 50) -> list:
    me = require_student(conn, actor)
    rows = conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                        (me.id, limit)).fetchall()
    return [dict(r) for r in rows]


def unread_count(conn, actor) -> int:
    me = require_student(conn, actor)
    return conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (me.id,)).fetchone()[0]


def mark_read(conn, actor, notification_id: int) -> None:
    me = require_student(conn, actor)
    with transaction(conn):   # the user_id filter makes it impossible to touch someone else's row
        conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, me.id))


def mark_all_read(conn, actor) -> None:
    me = require_student(conn, actor)
    with transaction(conn):
        conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (me.id,))
