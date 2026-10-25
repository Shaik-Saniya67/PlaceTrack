"""Create an administrator from the command line:   python create_admin.py

Useful if you prefer not to use the first-run screen, or need to add more admins.
Passwords are typed interactively (never passed as arguments, so they stay out of shell history).
"""
import getpass
import sys

from database.db import connect, init_db
from services import auth_service
from services.errors import PlaceTrackError


def main() -> int:
    conn = connect()
    init_db(conn)
    name = input("Full name: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password (8+ chars): ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match.")
        return 1
    try:
        user = auth_service._create_user(conn, email, password, name, "admin")
    except PlaceTrackError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Administrator created: {user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
