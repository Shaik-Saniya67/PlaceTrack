import streamlit as st

from services import application_service, drive_service
from services.errors import PlaceTrackError
from services.statuses import next_statuses
from services.timeutil import combine_local, fmt_dt, to_local
from ui.components import page_header, stretch
from ui.session import require_role

conn, user = require_role("admin")
page_header("Applications", "Review who is tracking each drive and move students through the stages.", eyebrow="Admin")
try:
    drives = drive_service.list_drives(conn, user)
except PlaceTrackError as exc:
    st.error(str(exc))
    st.stop()
if not drives:
    st.info("No drives yet.")
    st.stop()

sel = st.selectbox("Drive", [d.id for d in drives], format_func=lambda i: next(d.title for d in drives if d.id == i))
try:
    apps = application_service.list_applications_admin(conn, user, sel)
except PlaceTrackError as exc:
    st.error(str(exc))
    st.stop()
if not apps:
    st.info("No students have tracked this drive yet.")
    st.stop()

st.dataframe([{"Student": a.student_name, "Email": a.student_email, "Department": a.student_department or "—",
               "CGPA": a.student_cgpa if a.student_cgpa is not None else "—", "Stage": a.status.label,
               "Interview": fmt_dt(a.interview_at)} for a in apps], hide_index=True, **stretch())

st.subheader("Update a stage")
st.caption("Students are notified when you change their stage. Only valid transitions are offered.")
by_id = {a.id: a for a in apps}
pick = st.selectbox("Student", list(by_id), format_func=lambda i: f"{by_id[i].student_name} ({by_id[i].status.label})")
app = by_id[pick]
with st.form(f"adm-{pick}"):
    new = st.selectbox("New stage", [app.status] + next_statuses(app.status), format_func=lambda s: s.label)
    has_iv = st.checkbox("Interview / assessment scheduled", value=app.interview_at is not None)
    local = to_local(app.interview_at) if app.interview_at else None
    c1, c2 = st.columns(2)
    iv_d = c1.date_input("Date", value=local.date() if local else None)
    iv_t = c2.time_input("Time", value=local.time().replace(tzinfo=None) if local else None)
    if st.form_submit_button("Update", type="primary"):
        try:
            iv = combine_local(iv_d, iv_t) if (has_iv and iv_d and iv_t) else None
            application_service.update_application(conn, user, app.id, new, interview_at=iv)
            st.toast("Stage updated.")
            st.rerun()
        except PlaceTrackError as exc:
            st.error(str(exc))
