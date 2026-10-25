"""Timezone helpers. Everything is stored in UTC and displayed in APP_TIMEZONE."""
import os
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


def app_tz() -> ZoneInfo:
    return ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Kolkata"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value):
    """Parse an ISO string / datetime into an aware datetime (naive is assumed UTC)."""
    if value is None or value == "":
        return None
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def to_iso_utc(dt: datetime):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=app_tz())
    return dt.astimezone(timezone.utc).isoformat()


def to_local(dt: datetime) -> datetime:
    return dt.astimezone(app_tz())


def fmt_dt(dt) -> str:
    return "—" if dt is None else to_local(dt).strftime("%d %b %Y, %I:%M %p")


def combine_local(d: date, t: time) -> datetime:
    return datetime.combine(d, t).replace(tzinfo=app_tz())
