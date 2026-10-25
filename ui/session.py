"""Streamlit session plumbing: per-run DB connection, login state, page guards."""
import threading

import streamlit as st

from database.db import connect, init_db
from services import auth_service
from services.errors import AuthorizationError
from services.permissions import require_role as _require_role

_local = threading.local()


@st.cache_resource(show_spinner=False)
def _initialise(path: str) -> bool:
    conn = connect(path)
    init_db(conn)          # creates tables on first start and seeds sample drives
    conn.close()
    return True


def open_conn():
    """Called once per script run by app.py; connections are not shared across threads."""
    from database.db import db_path
    _initialise(db_path())
    _local.conn = connect()
    return _local.conn


def close_conn() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def get_conn():
    conn = getattr(_local, "conn", None)
    return conn if conn is not None else open_conn()


def current_user():
    """The signed-in user, re-read from the database every run (role and active flag are never cached)."""
    user = auth_service.get_user(get_conn(), st.session_state.get("user_id"))
    if user is None:
        st.session_state.pop("user_id", None)
    return user


def login_user(user) -> None:
    st.session_state["user_id"] = user.id


def logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def require_login():
    user = current_user()
    if user is None:
        st.warning("Please sign in to continue.")
        st.stop()
    return get_conn(), user


def require_role(*roles):
    conn, user = require_login()
    try:
        _require_role(conn, user, *roles)
    except AuthorizationError as exc:
        st.error(str(exc))
        st.stop()
    return conn, user
