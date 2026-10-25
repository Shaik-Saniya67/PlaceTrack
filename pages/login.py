import streamlit as st

from services import auth_service
from services.errors import PlaceTrackError
from ui.components import page_header
from ui.session import get_conn, login_user

conn = get_conn()
page_header("PlaceTrack", "Your placement season, organised: eligibility checks, deadlines and every interview stage in one place.",
            eyebrow="Placement portal tracker")

first_run = not auth_service.admin_exists(conn)
tabs = st.tabs(["Sign in", "Create student account"] + (["🛠 First-time setup"] if first_run else []))

with tabs[0]:
    with st.form("signin"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        go = st.form_submit_button("Sign in", type="primary")
    if go:
        try:
            with st.spinner("Signing in…"):
                login_user(auth_service.login(conn, email, password))
            st.rerun()
        except PlaceTrackError as exc:
            st.error(str(exc))

with tabs[1]:
    st.caption("Public sign-up always creates a **student** account. Administrators are created separately.")
    with st.form("signup"):
        name = st.text_input("Full name")
        email2 = st.text_input("Email", key="su_email")
        pw2 = st.text_input("Password (8+ characters)", type="password", key="su_pw")
        go2 = st.form_submit_button("Create account", type="primary")
    if go2:
        try:
            with st.spinner("Creating account…"):
                login_user(auth_service.register_student(conn, email2, pw2, name))
            st.rerun()
        except PlaceTrackError as exc:
            st.error(str(exc))

if first_run:
    with tabs[2]:
        st.info("No administrator exists yet. Create the placement-cell admin account now; this option disappears afterwards.")
        with st.form("first_admin"):
            aname = st.text_input("Admin full name")
            aemail = st.text_input("Admin email", key="ad_email")
            apw = st.text_input("Admin password (8+ characters)", type="password", key="ad_pw")
            go3 = st.form_submit_button("Create administrator", type="primary")
        if go3:
            try:
                login_user(auth_service.create_first_admin(conn, aemail, apw, aname))
                st.rerun()
            except PlaceTrackError as exc:
                st.error(str(exc))
