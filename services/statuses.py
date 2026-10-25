"""Application / drive status enums and the allowed transitions."""
from enum import Enum

from services.errors import InvalidTransitionError


class ApplicationStatus(str, Enum):
    INTERESTED = "interested"
    APPLIED = "applied"
    ASSESSMENT = "assessment"
    TECHNICAL_INTERVIEW = "technical_interview"
    HR_INTERVIEW = "hr_interview"
    SELECTED = "selected"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    @property
    def label(self) -> str:
        return {"technical_interview": "Technical Interview", "hr_interview": "HR Interview"}.get(
            self.value, self.value.capitalize())


class DriveStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


S = ApplicationStatus
ALLOWED_TRANSITIONS = {
    S.INTERESTED: {S.APPLIED, S.WITHDRAWN},
    S.APPLIED: {S.ASSESSMENT, S.TECHNICAL_INTERVIEW, S.HR_INTERVIEW, S.SELECTED, S.REJECTED, S.WITHDRAWN},
    S.ASSESSMENT: {S.TECHNICAL_INTERVIEW, S.HR_INTERVIEW, S.SELECTED, S.REJECTED, S.WITHDRAWN},
    S.TECHNICAL_INTERVIEW: {S.HR_INTERVIEW, S.SELECTED, S.REJECTED, S.WITHDRAWN},
    S.HR_INTERVIEW: {S.SELECTED, S.REJECTED, S.WITHDRAWN},
    S.SELECTED: {S.WITHDRAWN},
    S.REJECTED: set(),
    S.WITHDRAWN: set(),
}
STATUS_ORDER = list(ApplicationStatus)
INTERVIEW_STAGES = {S.ASSESSMENT, S.TECHNICAL_INTERVIEW, S.HR_INTERVIEW}
ACTIVE_STAGES = {S.APPLIED} | INTERVIEW_STAGES

DRIVE_TRANSITIONS = {
    DriveStatus.DRAFT: {DriveStatus.PUBLISHED},
    DriveStatus.PUBLISHED: {DriveStatus.CLOSED},
    DriveStatus.CLOSED: {DriveStatus.PUBLISHED},   # re-open
}


def next_statuses(current) -> list:
    return [s for s in STATUS_ORDER if s in ALLOWED_TRANSITIONS[ApplicationStatus(current)]]


def can_transition(current, new) -> bool:
    return ApplicationStatus(new) in ALLOWED_TRANSITIONS[ApplicationStatus(current)]


def validate_transition(current, new) -> None:
    if not can_transition(current, new):
        raise InvalidTransitionError(
            f"Cannot move an application from {ApplicationStatus(current).label} to {ApplicationStatus(new).label}.")


def can_transition_drive(current, new) -> bool:
    return DriveStatus(new) in DRIVE_TRANSITIONS[DriveStatus(current)]
