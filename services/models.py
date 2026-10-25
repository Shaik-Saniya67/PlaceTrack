"""Plain dataclasses built from sqlite3.Row objects."""
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from services.statuses import ApplicationStatus
from services.timeutil import parse_ts

DEPARTMENTS = ["CSE", "IT", "AI&ML", "Data Science", "ECE", "EEE", "Mechanical", "Civil", "Chemical", "Other"]


def _json_list(text) -> tuple:
    try:
        return tuple(json.loads(text or "[]"))
    except (TypeError, ValueError):
        return ()


@dataclass(frozen=True)
class User:
    id: int
    email: str
    full_name: str
    role: str = "student"
    is_active: bool = True

    @classmethod
    def from_row(cls, r) -> "User":
        return cls(id=r["id"], email=r["email"], full_name=r["full_name"], role=r["role"], is_active=bool(r["is_active"]))


@dataclass(frozen=True)
class Profile:
    user_id: int
    department: Optional[str] = None
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    backlogs: Optional[int] = None
    skills: tuple = field(default_factory=tuple)

    @classmethod
    def from_row(cls, r) -> "Profile":
        return cls(user_id=r["user_id"], department=r["department"], graduation_year=r["graduation_year"],
                   cgpa=r["cgpa"], backlogs=r["backlogs"], skills=_json_list(r["skills"]))

    def missing_fields(self) -> list:
        names = {"department": "department", "graduation_year": "graduation year", "cgpa": "CGPA", "backlogs": "backlogs"}
        return [label for attr, label in names.items() if getattr(self, attr) is None]

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields()


@dataclass(frozen=True)
class Drive:
    id: int
    company_name: str
    role_title: str
    package_lpa: Optional[float] = None
    description: str = ""
    location: Optional[str] = None
    min_cgpa: Optional[float] = None
    eligible_departments: tuple = field(default_factory=tuple)
    eligible_years: tuple = field(default_factory=tuple)
    max_backlogs: Optional[int] = None
    deadline: Optional[datetime] = None
    application_url: Optional[str] = None
    status: str = "draft"
    is_sample: bool = False

    @classmethod
    def from_row(cls, r, prefix: str = "") -> "Drive":
        g = lambda k: r[prefix + k]  # noqa: E731
        return cls(id=g("id"), company_name=g("company_name"), role_title=g("role_title"), package_lpa=g("package_lpa"),
                   description=g("description") or "", location=g("location"), min_cgpa=g("min_cgpa"),
                   eligible_departments=_json_list(g("eligible_departments")), eligible_years=_json_list(g("eligible_years")),
                   max_backlogs=g("max_backlogs"), deadline=parse_ts(g("deadline")), application_url=g("application_url"),
                   status=g("status"), is_sample=bool(g("is_sample")))

    @property
    def title(self) -> str:
        return f"{self.company_name}: {self.role_title}"


@dataclass
class Application:
    id: int
    student_id: int
    drive_id: int
    status: ApplicationStatus
    interview_at: Optional[datetime] = None
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    drive: Optional[Drive] = None
    student_name: str = ""
    student_email: str = ""
    student_department: Optional[str] = None
    student_cgpa: Optional[float] = None

    @classmethod
    def from_row(cls, r) -> "Application":
        cols = set(r.keys())
        return cls(id=r["id"], student_id=r["student_id"], drive_id=r["drive_id"], status=ApplicationStatus(r["status"]),
                   interview_at=parse_ts(r["interview_at"]), notes=r["notes"] or "", created_at=parse_ts(r["created_at"]),
                   updated_at=parse_ts(r["updated_at"]),
                   drive=Drive.from_row(r, "d_") if "d_id" in cols else None,
                   student_name=r["s_name"] if "s_name" in cols else "", student_email=r["s_email"] if "s_email" in cols else "",
                   student_department=r["s_dept"] if "s_dept" in cols else None,
                   student_cgpa=r["s_cgpa"] if "s_cgpa" in cols else None)
