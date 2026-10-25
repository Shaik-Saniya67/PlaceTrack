import streamlit as st

from services import auth_service
from services.errors import PlaceTrackError
from services.models import DEPARTMENTS
from services.profile_service import get_profile, save_profile
from services.timeutil import now_utc
from ui.components import page_header
from ui.session import require_login

conn, user = require_login()
page_header("My profile", f"{user.email} · role: {user.role}", eyebrow="Account")

if user.role != "student":
    st.info("Administrator accounts have no academic profile.")
    st.stop()

profile = get_profile(conn, user)
years = list(range(now_utc().year - 1, now_utc().year + 6))
with st.form("profile_form"):
    name = st.text_input("Full name", value=user.full_name, max_chars=120)
    c1, c2 = st.columns(2)
    dept = c1.selectbox("Department", DEPARTMENTS, index=DEPARTMENTS.index(profile.department) if profile.department in DEPARTMENTS else None,
                        placeholder="Choose your department")
    grad = c2.selectbox("Graduation year", years, index=years.index(profile.graduation_year) if profile.graduation_year in years else None,
                        placeholder="Choose year")
    c3, c4 = st.columns(2)
    cgpa = c3.number_input("CGPA (0–10)", 0.0, 10.0, value=profile.cgpa, step=0.01, format="%.2f")
    backlogs = c4.number_input("Active backlogs", 0, 50, value=profile.backlogs, step=1)
    skills = st.text_input("Skills (comma separated)", value=", ".join(profile.skills))
    saved = st.form_submit_button("Save profile", type="primary")
if saved:
    try:
        save_profile(conn, user, name, {"department": dept, "graduation_year": grad, "cgpa": cgpa,
                                         "backlogs": backlogs, "skills": skills})
        st.success("Profile saved.")
        st.rerun()
    except PlaceTrackError as exc:
        st.error(str(exc))
