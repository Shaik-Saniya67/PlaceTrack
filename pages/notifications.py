import streamlit as st

from services import notification_service
from services.errors import PlaceTrackError
from services.timeutil import fmt_dt, parse_ts
from ui.components import esc, page_header
from ui.session import require_role

conn, user = require_role("student")
page_header("Notifications", "Deadline and interview reminders, plus stage updates from the placement team.", eyebrow="Inbox")
try:
    notification_service.refresh_reminders(conn, user)
    items = notification_service.list_notifications(conn, user)
except PlaceTrackError as exc:
    st.error(str(exc))
    st.stop()
if not items:
    st.info("You're all caught up. Reminders appear here as deadlines and interviews approach.")
    st.stop()
if st.button("Mark all as read"):
    notification_service.mark_all_read(conn, user)
    st.rerun()
for n in items:
    with st.container(border=True):
        st.markdown(f"{'🔵' if not n['is_read'] else '⚪'} **{esc(n['title'])}**", unsafe_allow_html=False)
        st.write(n["message"])
        st.caption(fmt_dt(parse_ts(n["created_at"])))
        if not n["is_read"] and st.button("Mark read", key=f"r-{n['id']}"):
            notification_service.mark_read(conn, user, n["id"])
            st.rerun()
