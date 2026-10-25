import streamlit as st

from services import application_service
from services.errors import PlaceTrackError
from services.statuses import next_statuses
from services.timeutil import combine_local, fmt_dt, parse_ts, to_local
from ui.components import MANUAL_NOTE, page_header, status_chip, status_text, stretch
from ui.session import require_role

conn, user = require_role("student")
page_header("My applications", MANUAL_NOTE.replace("**", ""), eyebrow="Tracker")

try:
    apps = application_service.list_my_applications(conn, user)
except PlaceTrackError as exc:
    st.error(str(exc))
    st.stop()
if not apps:
    st.info("You haven't tracked any drives yet. Head to **Drives** to start.")
    st.stop()

chosen = st.multiselect("Filter by stage", sorted({a.status.label for a in apps}))
for a in apps:
    if chosen and a.status.label not in chosen:
        continue
    with st.container(border=True):
        st.markdown(f"**{a.drive.company_name}** · {a.drive.role_title}", unsafe_allow_html=False)
        st.markdown(status_chip(a.status.value), unsafe_allow_html=True)
        t_edit, t_hist = st.tabs(["Update", "History"])
        with t_edit:
            options = [a.status] + next_statuses(a.status)
            with st.form(f"f-{a.id}"):
                new = st.selectbox("Stage", options, format_func=lambda s: s.label, key=f"s-{a.id}")
                has_iv = st.checkbox("Interview / assessment scheduled", value=a.interview_at is not None, key=f"h-{a.id}")
                local = to_local(a.interview_at) if a.interview_at else None
                c1, c2 = st.columns(2)
                iv_d = c1.date_input("Date", value=local.date() if local else None, key=f"d-{a.id}")
                iv_t = c2.time_input("Time", value=local.time().replace(tzinfo=None) if local else None, key=f"t-{a.id}")
                notes = st.text_area("Notes", value=a.notes, max_chars=2000, key=f"n-{a.id}")
                if st.form_submit_button("Save changes", type="primary"):
                    try:
                        iv = combine_local(iv_d, iv_t) if (has_iv and iv_d and iv_t) else None
                        application_service.update_application(conn, user, a.id, new, notes, iv)
                        st.toast("Updated.")
                        st.rerun()
                    except PlaceTrackError as exc:
                        st.error(str(exc))
            if not next_statuses(a.status):
                st.caption("This is a final stage: no further stage changes are possible.")
        with t_hist:
            try:
                events = application_service.list_events(conn, user, a.id)
            except PlaceTrackError as exc:
                st.error(str(exc))
                events = []
            st.dataframe([{"When": fmt_dt(parse_ts(e["created_at"])), "From": (e["from_status"] or "—").replace("_", " "),
                           "To": e["to_status"].replace("_", " "),
                           "Changed by": "You" if e["changed_by_role"] == "student" else f"Placement team ({e['changed_by_name']})"}
                          for e in events], hide_index=True, **stretch())
