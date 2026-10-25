"""Role enforcement. Roles are always re-read from the database, so a forged or stale User
object (for example one edited in session state) can never grant extra rights."""
from services.errors import AuthorizationError
from services.models import User


def require_role(conn, actor, *roles) -> User:
    if actor is None:
        raise AuthorizationError("Please sign in.")
    row = conn.execute("SELECT id, email, full_name, role, is_active FROM users WHERE id = ?", (actor.id,)).fetchone()
    if row is None or not row["is_active"]:
        raise AuthorizationError("Your account is not active.")
    fresh = User.from_row(row)
    if fresh.role not in roles:
        raise AuthorizationError("You do not have permission to perform this action.")
    return fresh


def require_admin(conn, actor) -> User:
    return require_role(conn, actor, "admin")


def require_student(conn, actor) -> User:
    return require_role(conn, actor, "student")
