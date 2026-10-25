import streamlit as st

from services import analytics_service as an
from services import application_service, drive_service
from services.errors import PlaceTrackError
from ui.charts import drives_stacked, package_bar, status_bar, trend_line
from ui.components import metric_cards, page_header, sample_banner, stretch
from ui.session import require_role

conn, user = require_role("admin")
page_header("Placement overview", "Drive health and student progress across the whole cell.", eyebrow="Admin dashboard")
try:
    drives = drive_service.list_drives(conn, user)
    apps = application_service.list_applications_admin(conn, user)
    students = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
except PlaceTrackError as exc:
    st.error(str(exc))
    st.stop()
sample_banner(drives)

m = an.summary_metrics(apps)
metric_cards([("Published drives", sum(d.status == "published" for d in drives), f"{sum(d.status == 'draft' for d in drives)} drafts"),
              ("Students", students, "registered"), ("Applications", m["total"], "tracked"),
              ("In progress", m["active"], "applied or in rounds"), ("Selected", m["selected"], "offers recorded")])

l, r = st.columns(2)
with l:
    st.subheader("Package by drive")
    pk = an.package_by_company([d for d in drives if d.status != "draft"])
    if len(pk):
        st.plotly_chart(package_bar(pk), **stretch())
with r:
    st.subheader("Applications by stage")
    st.plotly_chart(status_bar(an.status_counts(apps)), **stretch())
if apps:
    a, b = st.columns(2)
    with a:
        st.subheader("Applications per drive")
        matrix = an.drive_application_matrix(apps)
        st.plotly_chart(drives_stacked(matrix), **stretch())
    with b:
        st.subheader("Growth")
        st.plotly_chart(trend_line(an.applications_over_time(apps)), **stretch())
    st.dataframe(matrix, **stretch())
else:
    st.info("No applications yet. They will appear here as students start tracking drives.")
