"""PlaceTrack entrypoint: theme, DB initialisation, role-based navigation, sidebar."""
import streamlit as st

from ui.components import esc, stretch
from ui.session import close_conn, current_user, logout, open_conn
from ui.theme import inject_theme

st.set_page_config(page_title="PlaceTrack", page_icon="🎯", layout="wide")
inject_theme()

conn = open_conn()          # also creates tables and seeds sample drives on the very first run
try:
    user = current_user()
    if user is None:
        nav = st.navigation([st.Page("pages/login.py", title="Sign in", icon="🔐")], position="hidden")
    elif user.role == "admin":
        nav = st.navigation({
            "Admin": [st.Page("pages/admin_dashboard.py", title="Overview", icon="📊", default=True),
                      st.Page("pages/admin_drives.py", title="Manage drives", icon="🏢"),
                      st.Page("pages/admin_applications.py", title="Applications", icon="🗂️")]})
    else:
        nav = st.navigation({
            "Student": [st.Page("pages/student_dashboard.py", title="Dashboard", icon="🏠", default=True),
                        st.Page("pages/drives.py", title="Drives", icon="🔎"),
                        st.Page("pages/my_applications.py", title="My applications", icon="📌"),
                        st.Page("pages/notifications.py", title="Notifications", icon="🔔"),
                        st.Page("pages/profile.py", title="Profile", icon="👤")]})

    if user is not None:
        with st.sidebar:
            initials = "".join(p[0] for p in user.full_name.split()[:2]).upper() or "?"
            st.markdown(f'<div class="pt-userchip"><div class="pt-avatar">{esc(initials)}</div><div>'
                        f'<b>{esc(user.full_name)}</b><small>{esc(user.role.title())} · {esc(user.email)}</small></div></div>',
                        unsafe_allow_html=True)
            if st.button("Log out", **stretch()):
                logout()
                st.rerun()
    nav.run()
finally:
    close_conn()
