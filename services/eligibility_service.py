"""Pure eligibility rules (no database, no UI).

A rule the drive does not restrict is NOT_APPLICABLE. A restricted rule whose profile data is
missing is UNKNOWN (never silently eligible). Otherwise PASS or FAIL.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from services.models import Drive, Profile
from services.statuses import DriveStatus
from services.timeutil import fmt_dt, now_utc


class Outcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "n/a"


@dataclass(frozen=True)
class CheckResult:
    rule: str
    outcome: Outcome
    message: str


@dataclass(frozen=True)
class EligibilityResult:
    checks: tuple = field(default_factory=tuple)

    @property
    def failures(self): return [c for c in self.checks if c.outcome is Outcome.FAIL]
    @property
    def unknowns(self): return [c for c in self.checks if c.outcome is Outcome.UNKNOWN]

    @property
    def status(self) -> str:
        return "ineligible" if self.failures else "unknown" if self.unknowns else "eligible"

    @property
    def is_eligible(self) -> bool:
        return self.status == "eligible"

    @property
    def explanations(self) -> list:
        return [c.message for c in self.failures + self.unknowns]


def check_drive_status(drive: Drive) -> CheckResult:
    if drive.status == DriveStatus.PUBLISHED.value:
        return CheckResult("drive_status", Outcome.PASS, "Drive is open for applications.")
    return CheckResult("drive_status", Outcome.FAIL, f"This drive is {drive.status} and not open for applications.")


def check_deadline(drive: Drive, now: Optional[datetime] = None) -> CheckResult:
    now = now or now_utc()
    if drive.deadline is None:
        return CheckResult("deadline", Outcome.NOT_APPLICABLE, "No application deadline set.")
    if now > drive.deadline:
        return CheckResult("deadline", Outcome.FAIL, f"The application deadline passed on {fmt_dt(drive.deadline)}.")
    return CheckResult("deadline", Outcome.PASS, f"Deadline is {fmt_dt(drive.deadline)}.")


def check_cgpa(profile: Profile, drive: Drive) -> CheckResult:
    if drive.min_cgpa is None:
        return CheckResult("cgpa", Outcome.NOT_APPLICABLE, "No minimum CGPA required.")
    if profile.cgpa is None:
        return CheckResult("cgpa", Outcome.UNKNOWN,
                           f"Add your CGPA to your profile; this drive requires at least {drive.min_cgpa:.2f}.")
    if round(profile.cgpa, 2) < round(drive.min_cgpa, 2):
        return CheckResult("cgpa", Outcome.FAIL, f"Your CGPA {profile.cgpa:.2f} is below the required {drive.min_cgpa:.2f}.")
    return CheckResult("cgpa", Outcome.PASS, f"CGPA {profile.cgpa:.2f} meets the minimum {drive.min_cgpa:.2f}.")


def check_department(profile: Profile, drive: Drive) -> CheckResult:
    allowed = [d.strip() for d in drive.eligible_departments if d and d.strip()]
    if not allowed:
        return CheckResult("department", Outcome.NOT_APPLICABLE, "Open to all departments.")
    if not profile.department or not profile.department.strip():
        return CheckResult("department", Outcome.UNKNOWN,
                           f"Add your department to your profile; eligible departments: {', '.join(allowed)}.")
    if profile.department.strip().lower() in {d.lower() for d in allowed}:
        return CheckResult("department", Outcome.PASS, f"Your department ({profile.department}) is eligible.")
    return CheckResult("department", Outcome.FAIL,
                       f"Your department ({profile.department}) is not eligible. Eligible: {', '.join(allowed)}.")


def check_graduation_year(profile: Profile, drive: Drive) -> CheckResult:
    years = sorted(drive.eligible_years)
    if not years:
        return CheckResult("graduation_year", Outcome.NOT_APPLICABLE, "Open to all graduation years.")
    listed = ", ".join(str(y) for y in years)
    if profile.graduation_year is None:
        return CheckResult("graduation_year", Outcome.UNKNOWN,
                           f"Add your graduation year to your profile; eligible years: {listed}.")
    if profile.graduation_year in years:
        return CheckResult("graduation_year", Outcome.PASS, f"Graduation year {profile.graduation_year} is eligible.")
    return CheckResult("graduation_year", Outcome.FAIL,
                       f"Graduation year {profile.graduation_year} is not eligible. Eligible: {listed}.")


def check_backlogs(profile: Profile, drive: Drive) -> CheckResult:
    limit = drive.max_backlogs
    if limit is None:
        return CheckResult("backlogs", Outcome.NOT_APPLICABLE, "No backlog limit.")
    if profile.backlogs is None:
        return CheckResult("backlogs", Outcome.UNKNOWN,
                           f"Add your backlog count to your profile; the maximum allowed is {limit}.")
    if profile.backlogs > limit:
        return CheckResult("backlogs", Outcome.FAIL,
                           f"You have {profile.backlogs} backlog(s); the maximum allowed is {limit}.")
    return CheckResult("backlogs", Outcome.PASS, f"{profile.backlogs} backlog(s) is within the limit of {limit}.")


def evaluate_eligibility(profile: Profile, drive: Drive, now: Optional[datetime] = None) -> EligibilityResult:
    return EligibilityResult(checks=(
        check_drive_status(drive), check_deadline(drive, now), check_cgpa(profile, drive),
        check_department(profile, drive), check_graduation_year(profile, drive), check_backlogs(profile, drive)))


def evaluate_many(profile: Profile, drives, now: Optional[datetime] = None) -> list:
    return [(d, evaluate_eligibility(profile, d, now)) for d in drives]
