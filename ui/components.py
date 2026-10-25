"""Reusable presentation helpers. Anything user-supplied is HTML-escaped before it reaches markdown."""
import html

import streamlit as st

from services.eligibility_service import Outcome
from services.statuses import ApplicationStatus
from services.timeutil import fmt_dt

STATUS_ICON = {"interested": "🔖", "applied": "📨", "assessment": "📝", "technical_interview": "💻",
               "hr_interview": "🤝", "selected": "🎉", "rejected": "✖️", "withdrawn": "↩️"}
STATUS_CHIP = {"interested": "info", "applied": "info", "assessment": "warn", "technical_interview": "warn",
               "hr_interview": "warn", "selected": "ok", "rejected": "bad", "withdrawn": ""}
OUTCOME_ICON = {Outcome.PASS: "✅", Outcome.FAIL: "❌", Outcome.UNKNOWN: "❔", Outcome.NOT_APPLICABLE: "➖"}
MANUAL_NOTE = ("PlaceTrack records your own progress. It does **not** submit applications to companies: "
               "apply on the company's portal, then mark it here.")


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def stretch() -> dict:
    """Width kwargs that work across Streamlit versions."""
    major, minor = (int(x) for x in st.__version__.split(".")[:2])
    return {"width": "stretch"} if (major, minor) >= (1, 50) else {"use_container_width": True}


def page_header(title: str, subtitle: str = "", eyebrow: str = "") -> None:
    eb = f'<span class="pt-eyebrow">{esc(eyebrow)}</span><br>' if eyebrow else ""
    st.markdown(f'<div class="pt-hero">{eb}<h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>', unsafe_allow_html=True)


def metric_cards(items) -> None:
    """items: [(label, value, hint)]"""
    cells = "".join(f'<div class="pt-metric"><span class="lbl">{esc(l)}</span><span class="val">{esc(v)}</span>'
                    f'<span class="hint">{esc(h)}</span></div>' for l, v, h in items)
    st.markdown(f'<div class="pt-metrics">{cells}</div>', unsafe_allow_html=True)


def chip(text, kind: str = "") -> str:
    return f'<span class="pt-chip {kind}">{esc(text)}</span>'


def status_chip(status) -> str:
    s = ApplicationStatus(status)
    return chip(f"{STATUS_ICON[s.value]} {s.label}", STATUS_CHIP[s.value])


def status_text(status) -> str:
    s = ApplicationStatus(status)
    return f"{STATUS_ICON[s.value]} {s.label}"


def fmt_package(lpa) -> str:
    return "Not disclosed" if lpa is None else f"₹{lpa:g} LPA"


def sample_banner(drives) -> None:
    if any(d.is_sample for d in drives):
        st.info("🧪 Drives marked **SAMPLE** are demonstration data (fictional companies).")


def drive_heading(drive, result=None) -> None:
    chips = [chip(drive.status.title(), {"published": "ok", "closed": "bad"}.get(drive.status, "warn"))]
    if drive.is_sample:
        chips.append(chip("SAMPLE", "sample"))
    if result is not None:
        chips.append(chip({"eligible": "Eligible", "ineligible": "Not eligible", "unknown": "Complete profile"}[result.status],
                          {"eligible": "ok", "ineligible": "bad", "unknown": "warn"}[result.status]))
    st.markdown(f'<div class="pt-drive-title">{esc(drive.company_name)} · {esc(drive.role_title)}</div>{"".join(chips)}'
                f'<div class="pt-sub">{esc(fmt_package(drive.package_lpa))} · {esc(drive.location or "Location TBA")} · '
                f'closes {esc(fmt_dt(drive.deadline))}</div>', unsafe_allow_html=True)


def drive_details(drive) -> None:
    if drive.description:
        st.write(drive.description)
    crit = []
    if drive.min_cgpa is not None:
        crit.append(f"Min CGPA **{drive.min_cgpa:.2f}**")
    if drive.eligible_departments:
        crit.append("Departments: " + ", ".join(drive.eligible_departments))
    if drive.eligible_years:
        crit.append("Graduation years: " + ", ".join(str(y) for y in drive.eligible_years))
    if drive.max_backlogs is not None:
        crit.append(f"Max backlogs **{drive.max_backlogs}**")
    st.caption(" · ".join(crit) if crit else "No eligibility restrictions.")


def render_eligibility(result) -> None:
    for c in result.checks:
        if c.outcome is not Outcome.NOT_APPLICABLE:
            st.markdown(f"{OUTCOME_ICON[c.outcome]} {c.message}")


def drive_label(drive) -> str:
    return drive.title + ("  [SAMPLE]" if drive.is_sample else "")
