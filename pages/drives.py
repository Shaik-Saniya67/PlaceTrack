import streamlit as st

from services import application_service, drive_service
from services.eligibility_service import evaluate_eligibility
from services.errors import PlaceTrackError
from services.models import DEPARTMENTS
from services.profile_service import get_profile
from services.statuses import ApplicationStatus
from ui.components import (MANUAL_NOTE, drive_details, drive_heading, page_header, render_eligibility,
                           sample_banner, status_text, stretch)
from ui.session import require_role

conn, user = require_role("student")
page_header("Placement drives", "Search, filter and see exactly why you are, or aren't, eligible.", eyebrow="Opportunities")

try:
    profile = get_profile(conn, user)
    drives = drive_service.list_open_drives(conn, user)
    mine = {a.drive_id: a for a in application_service.list_my_applications(conn, user)}
except PlaceTrackError as exc:
    st.error(str(exc))
    st.stop()
sample_banner(drives)

f1, f2, f3 = st.columns([2, 2, 2])
search = f1.text_input("Search", placeholder="company, role or keyword")
companies = f2.multiselect("Company", sorted({d.company_name for d in drives}))
location = f3.text_input("Location")
g1, g2, g3, g4 = st.columns([2, 2, 2, 1])
dept = g1.selectbox("Department", [""] + DEPARTMENTS, format_func=lambda x: x or "Any")
sort_by = g2.selectbox("Sort by", ["Deadline (soonest)", "Package (high to low)", "Company (A–Z)"])
max_pkg = max([d.package_lpa or 0 for d in drives] + [1])
min_pkg = g3.slider("Min package (LPA)", 0.0, float(max_pkg), 0.0, 0.5)
only_eligible = g4.toggle("Eligible only")

shown = drive_service.filter_drives(drives, search, companies, location, min_pkg or None, dept)
results = {d.id: evaluate_eligibility(profile, d) for d in shown}
if only_eligible:
    shown = [d for d in shown if results[d.id].is_eligible]
if sort_by.startswith("Package"):
    shown.sort(key=lambda d: -(d.package_lpa or 0))
elif sort_by.startswith("Company"):
    shown.sort(key=lambda d: d.company_name.lower())

st.caption(f"{len(shown)} drive(s)")
if not shown:
    st.info("No drives match your filters.")
for d in shown:
    res, existing = results[d.id], mine.get(d.id)
    with st.container(border=True):
        drive_heading(d, res)
        with st.expander("Details & eligibility"):
            drive_details(d)
            st.markdown("**Eligibility check**")
            render_eligibility(res)
        if existing:
            st.success(f"Tracking: {status_text(existing.status)}. Manage it under My applications.")
        else:
            b1, b2, b3 = st.columns(3)
            for col, label, status, key in ((b1, "🔖 Mark interested", ApplicationStatus.INTERESTED, "i"),
                                            (b2, "📨 I applied on their site", ApplicationStatus.APPLIED, "a")):
                if col.button(label, key=f"{key}-{d.id}", disabled=not res.is_eligible, **stretch()):
                    try:
                        application_service.create_application(conn, user, d, status)
                        st.toast("Saved to your applications.")
                        st.rerun()
                    except PlaceTrackError as exc:
                        st.error(str(exc))
            if d.application_url:
                b3.link_button("Open application page ↗", d.application_url, **stretch())
            st.caption(MANUAL_NOTE)
