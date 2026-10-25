import streamlit as st

from services import drive_service
from services.errors import PlaceTrackError
from services.models import DEPARTMENTS, Drive
from services.statuses import DRIVE_TRANSITIONS, DriveStatus
from services.timeutil import combine_local, now_utc, to_local
from ui.components import drive_heading, page_header, sample_banner, stretch
from ui.session import require_role

conn, user = require_role("admin")
page_header("Manage drives", "Create, edit, publish and close placement drives.", eyebrow="Admin")
try:
    drives = drive_service.list_drives(conn, user)
except PlaceTrackError as exc:
    st.error(str(exc))
    st.stop()
sample_banner(drives)

flt = st.multiselect("Show", [s.value for s in DriveStatus], default=["draft", "published", "closed"])
for d in [x for x in drives if x.status in flt]:
    with st.container(border=True):
        a, b = st.columns([3, 2])
        with a:
            drive_heading(d)
        verbs = {"published": "Publish" if d.status == "draft" else "Re-open", "closed": "Close"}
        moves = sorted(DRIVE_TRANSITIONS[DriveStatus(d.status)], key=lambda s: s.value)
        for col, mv in zip(b.columns(max(len(moves), 1)), moves):
            if col.button(f"{'🚀' if mv.value == 'published' else '🔒'} {verbs[mv.value]}", key=f"m-{d.id}-{mv.value}", **stretch()):
                try:
                    drive_service.set_drive_status(conn, user, d.id, mv)
                    st.rerun()
                except PlaceTrackError as exc:
                    st.error(str(exc))

st.divider()
st.subheader("Create or edit a drive")
NEW = 0
choice = st.selectbox("Drive", [NEW] + [d.id for d in drives],
                      format_func=lambda i: "➕ New drive" if i == NEW else next(d.title for d in drives if d.id == i))
cur = next((d for d in drives if d.id == choice), None) or Drive(id=NEW, company_name="", role_title="")
dl = to_local(cur.deadline) if cur.deadline else to_local(now_utc())
years = list(range(now_utc().year - 1, now_utc().year + 6))

with st.form(f"drive-{choice}"):
    c1, c2 = st.columns(2)
    company = c1.text_input("Company", value=cur.company_name, max_chars=120)
    role = c2.text_input("Role title", value=cur.role_title, max_chars=120)
    desc = st.text_area("Job description", value=cur.description, max_chars=5000)
    c3, c4, c5 = st.columns(3)
    location = c3.text_input("Location", value=cur.location or "")
    package = c4.number_input("Package (LPA, 0 = not disclosed)", 0.0, 9999.0, value=cur.package_lpa or 0.0, step=0.5)
    url = c5.text_input("Application URL (https://…)", value=cur.application_url or "")
    st.markdown("**Eligibility criteria**")
    e1, e2 = st.columns(2)
    min_cgpa = e1.number_input("Minimum CGPA (0 = none)", 0.0, 10.0, value=cur.min_cgpa or 0.0, step=0.1)
    backlogs = e2.number_input("Max backlogs (-1 = no limit)", -1, 50, value=-1 if cur.max_backlogs is None else cur.max_backlogs)
    depts = st.multiselect("Eligible departments (empty = all)", DEPARTMENTS, default=[x for x in cur.eligible_departments if x in DEPARTMENTS])
    ys = st.multiselect("Eligible graduation years (empty = all)", sorted(set(years) | set(cur.eligible_years)), default=list(cur.eligible_years))
    d1, d2, d3 = st.columns(3)
    no_deadline = d1.checkbox("No deadline", value=bool(cur.id) and cur.deadline is None)
    ddate = d2.date_input("Deadline date", value=dl.date())
    dtime = d3.time_input("Deadline time", value=dl.time().replace(tzinfo=None, second=0, microsecond=0))
    submitted = st.form_submit_button("Save drive", type="primary")
if submitted:
    payload = {"company_name": company, "role_title": role, "description": desc, "location": location,
               "package_lpa": package or None, "application_url": url, "min_cgpa": min_cgpa or None,
               "max_backlogs": None if backlogs < 0 else backlogs, "eligible_departments": depts, "eligible_years": ys,
               "deadline": None if no_deadline else combine_local(ddate, dtime)}
    try:
        if cur.id:
            drive_service.update_drive(conn, user, cur.id, payload)
        else:
            drive_service.create_drive(conn, user, payload)
        st.success("Drive saved. New drives start as drafts: publish them above.")
        st.rerun()
    except PlaceTrackError as exc:
        st.error(str(exc))
