"""pandas helpers turning applications and drives into dashboard data."""
from datetime import timedelta
from typing import Optional

import pandas as pd

from services.statuses import ACTIVE_STAGES, INTERVIEW_STAGES, STATUS_ORDER, ApplicationStatus
from services.timeutil import now_utc, to_local


def status_counts(apps) -> pd.DataFrame:
    counts = {s: 0 for s in STATUS_ORDER}
    for a in apps:
        counts[a.status] += 1
    return pd.DataFrame({"status": [s.label for s in STATUS_ORDER], "count": [counts[s] for s in STATUS_ORDER]})


def summary_metrics(apps) -> dict:
    return {"total": len(apps),
            "active": sum(1 for a in apps if a.status in ACTIVE_STAGES),
            "interviews": sum(1 for a in apps if a.status in INTERVIEW_STAGES),
            "selected": sum(1 for a in apps if a.status is ApplicationStatus.SELECTED)}


def upcoming_deadlines(drives, days: int = 14, now=None) -> list:
    now = now or now_utc()
    end = now + timedelta(days=days)
    return sorted((d for d in drives if d.deadline and now <= d.deadline <= end), key=lambda d: d.deadline)


def upcoming_interviews(apps, now=None, days: Optional[int] = 30) -> list:
    now = now or now_utc()
    end = now + timedelta(days=days) if days else None
    return sorted((a for a in apps if a.interview_at and a.interview_at >= now and a.status in INTERVIEW_STAGES
                   and (end is None or a.interview_at <= end)), key=lambda a: a.interview_at)


def drive_application_matrix(apps) -> pd.DataFrame:
    """Rows = drive, columns = stage labels, values = counts, plus a Total column."""
    if not apps:
        return pd.DataFrame()
    df = pd.DataFrame([{"drive": a.drive.title if a.drive else str(a.drive_id), "status": a.status.label} for a in apps])
    m = df.pivot_table(index="drive", columns="status", aggfunc="size", fill_value=0)
    m = m[[s.label for s in STATUS_ORDER if s.label in m.columns]]
    m["Total"] = m.sum(axis=1)
    return m.sort_values("Total", ascending=False)


def applications_over_time(apps) -> pd.DataFrame:
    """Applications created per local day (cumulative), for the admin trend chart."""
    rows = [to_local(a.created_at).date() for a in apps if a.created_at]
    if not rows:
        return pd.DataFrame(columns=["date", "applications"])
    s = pd.Series(1, index=pd.to_datetime(rows)).groupby(level=0).sum().sort_index().cumsum()
    return pd.DataFrame({"date": s.index, "applications": s.values})


def package_by_company(drives) -> pd.DataFrame:
    rows = [{"drive": d.company_name.replace(" (Sample)", ""), "package": d.package_lpa} for d in drives if d.package_lpa]
    return pd.DataFrame(rows, columns=["drive", "package"]).sort_values("package", ascending=False)
