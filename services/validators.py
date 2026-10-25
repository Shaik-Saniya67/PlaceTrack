"""Input validation shared by services. Each function returns a cleaned dict or raises ValidationError."""
import math
import re
from datetime import datetime
from urllib.parse import urlparse

from services.errors import ValidationError
from services.models import DEPARTMENTS
from services.timeutil import to_iso_utc

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def num(value, label, lo, hi, errors, integer=False):
    try:
        if isinstance(value, bool):
            raise ValueError
        n = float(value)
        if math.isnan(n) or math.isinf(n) or (integer and n != int(n)):
            raise ValueError
    except (TypeError, ValueError):
        errors.append(f"{label} must be a valid {'whole ' if integer else ''}number.")
        return None
    if not lo <= n <= hi:
        errors.append(f"{label} must be between {lo} and {hi}.")
        return None
    return int(n) if integer else round(n, 2)


def parse_skills(value) -> list:
    items = value.split(",") if isinstance(value, str) else list(value or [])
    seen, out = set(), []
    for item in items:
        s = str(item).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def validate_email_password(email, password, full_name=None):
    errors, email = [], (email or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        errors.append("Enter a valid email address.")
    pw = password or ""
    if len(pw) < 8:
        errors.append("Password must be at least 8 characters.")
    elif len(pw.encode("utf-8")) > 72:
        errors.append("Password must be at most 72 bytes (bcrypt limit).")
    if full_name is not None:
        full_name = full_name.strip()
        if not full_name or len(full_name) > 120:
            errors.append("Full name is required (max 120 characters).")
    if errors:
        raise ValidationError(errors)
    return email, full_name


def validate_profile(data: dict) -> dict:
    errors, clean = [], {}
    dept = str(data.get("department") or "").strip()
    if dept not in DEPARTMENTS:
        errors.append("Please choose a department from the list.")
    clean["department"] = dept
    clean["graduation_year"] = num(data.get("graduation_year"), "Graduation year", 2000, 2100, errors, True)
    clean["cgpa"] = num(data.get("cgpa"), "CGPA", 0, 10, errors)
    clean["backlogs"] = num(data.get("backlogs"), "Backlogs", 0, 50, errors, True)
    skills = parse_skills(data.get("skills"))
    if len(skills) > 50 or any(len(s) > 40 for s in skills):
        errors.append("Use at most 50 skills of up to 40 characters each.")
    clean["skills"] = skills
    if errors:
        raise ValidationError(errors)
    return clean


def validate_drive(data: dict) -> dict:
    errors, clean = [], {}
    for key, label in (("company_name", "Company name"), ("role_title", "Role title")):
        v = str(data.get(key) or "").strip()
        if not v or len(v) > 120:
            errors.append(f"{label} is required (max 120 characters).")
        clean[key] = v
    desc = str(data.get("description") or "").strip()
    if len(desc) > 5000:
        errors.append("Description must be at most 5000 characters.")
    clean["description"] = desc
    loc = str(data.get("location") or "").strip()
    if len(loc) > 120:
        errors.append("Location must be at most 120 characters.")
    clean["location"] = loc or None

    def opt(key, label, lo, hi, integer=False):
        v = data.get(key)
        return None if v in (None, "") else num(v, label, lo, hi, errors, integer)

    clean["package_lpa"] = opt("package_lpa", "Package (LPA)", 0, 9999)
    clean["min_cgpa"] = opt("min_cgpa", "Minimum CGPA", 0, 10)
    clean["max_backlogs"] = opt("max_backlogs", "Max backlogs", 0, 50, True)

    lookup = {d.lower(): d for d in DEPARTMENTS}
    depts = []
    for d in data.get("eligible_departments") or []:
        canon = lookup.get(str(d).strip().lower())
        if canon is None:
            errors.append(f"Unknown department: {d}.")
        elif canon not in depts:
            depts.append(canon)
    clean["eligible_departments"] = depts
    years = []
    for y in data.get("eligible_years") or []:
        n = num(y, "Graduation year", 2000, 2100, errors, True)
        if n is not None and n not in years:
            years.append(n)
    clean["eligible_years"] = sorted(years)

    deadline = data.get("deadline")
    if deadline is not None and not isinstance(deadline, datetime):
        errors.append("Deadline must be a date and time.")
        deadline = None
    clean["deadline"] = to_iso_utc(deadline)

    url = str(data.get("application_url") or "").strip()
    if url:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc or len(url) > 500:
            errors.append("Application URL must be a valid http:// or https:// link.")
    clean["application_url"] = url or None
    if errors:
        raise ValidationError(errors)
    return clean
