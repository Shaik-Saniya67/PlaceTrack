from dataclasses import replace
from datetime import timedelta

from services.eligibility_service import (Outcome, check_backlogs, check_cgpa, check_deadline, check_department,
                                          check_drive_status, check_graduation_year, evaluate_eligibility)
from services.models import Profile
from tests.conftest import make_drive, make_profile


# CGPA
def test_cgpa_pass(): assert check_cgpa(make_profile(), make_drive()).outcome is Outcome.PASS
def test_cgpa_exact_min_passes(): assert check_cgpa(make_profile(cgpa=7.0), make_drive()).outcome is Outcome.PASS

def test_cgpa_below_fails():
    r = check_cgpa(make_profile(cgpa=6.5), make_drive())
    assert r.outcome is Outcome.FAIL and "6.50" in r.message and "7.00" in r.message

def test_cgpa_missing_unknown(): assert check_cgpa(make_profile(cgpa=None), make_drive()).outcome is Outcome.UNKNOWN
def test_cgpa_not_required(): assert check_cgpa(make_profile(cgpa=None), make_drive(min_cgpa=None)).outcome is Outcome.NOT_APPLICABLE

# Department
def test_department_pass_case_insensitive(): assert check_department(make_profile(department=" cse "), make_drive()).outcome is Outcome.PASS

def test_department_fail_lists_allowed():
    r = check_department(make_profile(department="ECE"), make_drive())
    assert r.outcome is Outcome.FAIL and "CSE" in r.message

def test_department_missing_unknown():
    assert check_department(make_profile(department=None), make_drive()).outcome is Outcome.UNKNOWN
    assert check_department(make_profile(department="  "), make_drive()).outcome is Outcome.UNKNOWN

def test_department_open_to_all():
    assert check_department(make_profile(department=None), make_drive(eligible_departments=())).outcome is Outcome.NOT_APPLICABLE

# Graduation year
def test_year_pass(): assert check_graduation_year(make_profile(), make_drive()).outcome is Outcome.PASS

def test_year_fail():
    r = check_graduation_year(make_profile(graduation_year=2026), make_drive())
    assert r.outcome is Outcome.FAIL and "2027" in r.message

def test_year_missing_unknown(): assert check_graduation_year(make_profile(graduation_year=None), make_drive()).outcome is Outcome.UNKNOWN
def test_year_open_to_all(): assert check_graduation_year(make_profile(), make_drive(eligible_years=())).outcome is Outcome.NOT_APPLICABLE

# Backlogs
def test_backlogs_pass_at_limit(): assert check_backlogs(make_profile(backlogs=2), make_drive(max_backlogs=2)).outcome is Outcome.PASS

def test_backlogs_fail():
    r = check_backlogs(make_profile(backlogs=1), make_drive())
    assert r.outcome is Outcome.FAIL and "maximum allowed is 0" in r.message

def test_backlogs_zero_is_known(): assert check_backlogs(make_profile(backlogs=0), make_drive()).outcome is Outcome.PASS
def test_backlogs_missing_unknown(): assert check_backlogs(make_profile(backlogs=None), make_drive()).outcome is Outcome.UNKNOWN
def test_backlogs_no_limit(): assert check_backlogs(make_profile(backlogs=9), make_drive(max_backlogs=None)).outcome is Outcome.NOT_APPLICABLE

# Deadline & drive status
def test_deadline_future(now): assert check_deadline(make_drive(), now).outcome is Outcome.PASS
def test_deadline_passed(now): assert check_deadline(make_drive(deadline=now - timedelta(minutes=1)), now).outcome is Outcome.FAIL
def test_deadline_exactly_now_open(now): assert check_deadline(make_drive(deadline=now), now).outcome is Outcome.PASS
def test_no_deadline(now): assert check_deadline(make_drive(deadline=None), now).outcome is Outcome.NOT_APPLICABLE
def test_status_published(): assert check_drive_status(make_drive()).outcome is Outcome.PASS

def test_status_not_published_fails():
    for s in ("draft", "closed"):
        assert check_drive_status(make_drive(status=s)).outcome is Outcome.FAIL

# Aggregation
def test_overall_eligible(now):
    r = evaluate_eligibility(make_profile(), make_drive(), now)
    assert r.is_eligible and r.explanations == []

def test_overall_reports_every_failure(now):
    r = evaluate_eligibility(make_profile(cgpa=5.0, department="ECE"), make_drive(), now)
    assert r.status == "ineligible" and len(r.failures) == 2

def test_missing_profile_is_unknown_not_eligible(now):
    r = evaluate_eligibility(Profile(user_id=1), make_drive(), now)
    assert r.status == "unknown" and not r.is_eligible and len(r.unknowns) == 4

def test_failure_outranks_unknown(now):
    assert evaluate_eligibility(make_profile(cgpa=5.0, department=None), make_drive(), now).status == "ineligible"

def test_unrestricted_drive_eligible_with_empty_profile(now):
    d = make_drive(min_cgpa=None, eligible_departments=(), eligible_years=(), max_backlogs=None)
    assert evaluate_eligibility(Profile(user_id=1), d, now).is_eligible
