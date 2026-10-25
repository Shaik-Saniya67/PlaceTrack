import streamlit as st

from services import analytics_service as an
from services import application_service, drive_service, notification_service
from services.eligibility_service import evaluate_many
from services.errors import PlaceTrackError
from services.profile_service import get_profile
from services.timeutil import fmt_dt
from ui.charts import status_bar, status_donut
from ui.components import fmt_package, metric_cards, page_header, sample_banner, status_text, stretch
from ui.session import require_role

conn, user = require_role("student")
page_header(f"Welcome back, {user.full_name.split()[0] if user.full_name else 'student'}",
            "Here is where your placement season stands today.", eyebrow="Student dashboard")

try:
    profile = get_profile(conn, user)
    drives = drive_service.list_open_drives(conn, user)
    apps = application_service.list_my_applications(conn, user)
    notification_service.refresh_reminders(conn, user)
    unread = notification_service.unread_count(conn, user)
except PlaceTrackError as exc:
    st.error(str(exc))
    st.stop()

if not profile.is_complete:
    st.warning("Your profile is incomplete (" + ", ".join(profile.missing_fields()) +
               "). Missing details are treated as **unknown**, never as eligible. Open **Profile** to complete it.")
sample_banner(drives)

tracked = {a.drive_id for a in apps}
evaluated = evaluate_many(profile, drives)
eligible = [d for d, r in evaluated if r.is_eligible and d.id not in tracked]
unknown = [d for d, r in evaluated if r.status == "unknown" and d.id not in tracked]
m = an.summary_metrics(apps)
metric_cards([("Eligible drives", len(eligible), "open and not yet tracked"), ("Applications", m["total"], "tracked by you"),
              ("In progress", m["active"], "applied or in rounds"), ("Selected", m["selected"], "offers recorded"),
              ("Unread alerts", unread, "see Notifications")])

left, right = st.columns([3, 2])
with left:
    st.subheader("Application pipeline")
    if apps:
        counts = an.status_counts(apps)
        t1, t2 = st.tabs(["By stage", "Share"])
        t1.plotly_chart(status_bar(counts), **stretch())
        t2.plotly_chart(status_donut(counts), **stretch())
    else:
        st.info("No applications yet. Open **Drives** and mark the ones you like.")
with right:
    st.subheader("Upcoming deadlines")
    ids = {d.id for d in eligible}
    ddl = [d for d in an.upcoming_deadlines(drives) if d.id in ids]
    for d in ddl[:6]:
        st.markdown(f"**{d.company_name}** · {fmt_dt(d.deadline)}")
    if not ddl:
        st.caption("No eligible deadlines in the next 14 days.")
    st.subheader("Interviews & assessments")
    ivs = an.upcoming_interviews(apps)
    for a in ivs[:6]:
        st.markdown(f"**{a.drive.company_name}** · {a.status.label} · {fmt_dt(a.interview_at)}")
    if not ivs:
        st.caption("Nothing scheduled. Add a date under My applications.")

st.subheader("Eligible opportunities")
if eligible:
    st.dataframe([{"Company": d.company_name, "Role": d.role_title, "Package": fmt_package(d.package_lpa),
                   "Location": d.location or "—", "Deadline": fmt_dt(d.deadline), "Sample": "Yes" if d.is_sample else ""}
                  for d in eligible], hide_index=True, **stretch())
else:
    st.info("No eligible open drives right now.")
if unknown:
    st.caption(f"{len(unknown)} drive(s) can't be checked until your profile is complete.")
