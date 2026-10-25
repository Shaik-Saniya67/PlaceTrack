"""SAMPLE drives (fictional companies) so the app is usable on first run."""
import json
from datetime import timedelta

from database.db import transaction
from services.timeutil import now_utc, to_iso_utc

# (company, role, lpa, description, location, min_cgpa, departments, years, max_backlogs, days, url, status)
SAMPLES = [
    ("Northwind Systems (Sample)", "Software Engineer Intern", 6.0,
     "SAMPLE: six-month backend internship on Python services and REST APIs.", "Bengaluru", 7.0,
     ["CSE", "IT", "AI&ML", "Data Science"], [2027], 0, 10, "https://example.com/northwind", "published"),
    ("Contoso Analytics (Sample)", "Data Analyst", 8.5,
     "SAMPLE: SQL, dashboards and stakeholder reporting for a retail analytics team.", "Hyderabad", 7.5,
     ["CSE", "IT", "ECE", "Data Science", "AI&ML"], [2026, 2027], 1, 2, "https://example.com/contoso", "published"),
    ("Fabrikam Devices (Sample)", "Embedded Engineer", 5.5,
     "SAMPLE: firmware development for IoT devices in C/C++.", "Chennai", 6.5,
     ["ECE", "EEE"], [2027], 2, 21, "https://example.com/fabrikam", "published"),
    ("Tailspin Cloud (Sample)", "Cloud Support Associate", 4.5,
     "SAMPLE: open to every department; cloud fundamentals training provided.", "Remote", None,
     [], [], None, 14, "https://example.com/tailspin", "published"),
    ("Litware Finance (Sample)", "Quant Developer", 14.0,
     "SAMPLE: high-bar role with strict criteria, useful to see ineligibility explanations.", "Mumbai", 9.0,
     ["CSE", "IT"], [2027], 0, 18, "https://example.com/litware", "published"),
    ("Proseware Mobility (Sample)", "Full-Stack Developer", 7.2,
     "SAMPLE: Python and TypeScript product team, hybrid.", "Pune", 7.0,
     ["CSE", "IT", "AI&ML"], [2027, 2028], 1, 5, "https://example.com/proseware", "published"),
    ("Adventure Works (Sample)", "Product Analyst", 9.0,
     "SAMPLE: draft drive, hidden from students until published.", "Pune", 8.0,
     ["CSE", "IT"], [2027], 0, 30, None, "draft"),
    ("Wingtip Labs (Sample)", "ML Engineer", 12.0,
     "SAMPLE: closed drive, kept for history.", "Bengaluru", 8.0,
     ["CSE", "AI&ML"], [2026], 0, -5, "https://example.com/wingtip", "closed"),
]


def seed_sample_drives(conn) -> int:
    if conn.execute("SELECT COUNT(*) FROM placement_drives").fetchone()[0]:
        return 0
    now = now_utc()
    with transaction(conn):
        for (company, role, lpa, desc, loc, cgpa, depts, years, backlogs, days, url, status) in SAMPLES:
            conn.execute(
                """INSERT INTO placement_drives
                   (company_name, role_title, package_lpa, description, location, min_cgpa,
                    eligible_departments, eligible_years, max_backlogs, deadline, application_url,
                    status, is_sample)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (company, role, lpa, desc, loc, cgpa, json.dumps(depts), json.dumps(years), backlogs,
                 to_iso_utc(now + timedelta(days=days)), url, status))
    return len(SAMPLES)
