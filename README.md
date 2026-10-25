# 🎯 PlaceTrack: Placement Portal Tracker (SQLite edition)

Students track placement drives, see **why** they are or aren't eligible, and follow every application stage;
the placement cell publishes drives and moves students through the stages. Pure Python:
**Streamlit + SQLite (`sqlite3`) + pandas + Plotly + pytest**. No external database, account or cloud service.

> **Honesty note:** PlaceTrack records progress the student reports. It never submits anything to a company
> portal, and the UI says so. "Applied" means *"I applied on the company's site and I'm recording it here."*
> The bundled drives are **fictional sample data** and are labelled `SAMPLE`.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

On first start the app creates `placetrack.db` next to `app.py`, creates all tables and loads sample drives.
Then open the **First-time setup** tab on the sign-in page to create your administrator account (this tab vanishes
once an admin exists). Students sign up themselves on the **Create student account** tab.
Prefer the terminal? `python create_admin.py` also works, and is how you add further admins.

Optional environment variables: `PLACETRACK_DB` (database path), `APP_TIMEZONE` (default `Asia/Kolkata`).

## Run the tests

```bash
pytest          # 120 tests, uses temporary databases, nothing to configure
```

## Project structure and what each module does

```
app.py                      Entrypoint: theme, DB init, role-based navigation, sidebar user card + logout
pages/                      One file per screen (UI only; no SQL, no business rules)
  login.py                    sign in / student sign-up / first-time admin setup
  student_dashboard.py        metric cards, pipeline charts, eligible drives, deadlines, interviews
  drives.py                   search + filters + sort, eligibility explanations, mark interested/applied
  my_applications.py          stage updates, interview dates, notes, history per application
  notifications.py            reminders and stage-change alerts
  profile.py                  name, department, graduation year, CGPA, backlogs, skills
  admin_dashboard.py          cell-wide metrics and charts
  admin_drives.py             add / edit / publish / close / re-open drives
  admin_applications.py       applicants per drive, move students through stages
services/                   Business logic, validation and permissions (no Streamlit imports)
  auth_service.py             bcrypt hashing, register, login, throttling, first-admin bootstrap
  permissions.py              require_role(): re-reads the role from the database on every call
  profile_service.py          student profile read/save
  drive_service.py            drive CRUD, lifecycle (draft → published → closed), filters
  eligibility_service.py      pure rules: CGPA, department, graduation year, backlogs, deadline, status
  application_service.py      create / update applications, transitions, history, duplicate prevention
  notification_service.py     deadline/interview reminders (deduplicated), read state
  analytics_service.py        pandas aggregations for dashboards
  validators.py, statuses.py, models.py, errors.py, timeutil.py   shared helpers
database/
  schema.sql                  all tables, constraints, indexes
  db.py                       connect() with foreign keys on, transaction() context manager, init_db()
  seed.py                     sample drives (loaded once, when the drives table is empty)
ui/                         theme.py (3D background + glass styling), components.py, charts.py, session.py
tests/                      pytest suite
create_admin.py             CLI helper to create an admin
```

Layering: **pages → services → database**. Pages never write SQL; services never import Streamlit.

## Database

Six tables: `users`, `student_profiles`, `placement_drives`, `applications`, `application_events`, `notifications`.
Foreign keys are switched on for every connection (`PRAGMA foreign_keys = ON`). Notable constraints:

* `UNIQUE (student_id, drive_id)` on `applications`, so a student cannot track the same drive twice.
* `CHECK` constraints on roles, statuses, CGPA (0–10), backlogs, URLs (`http(s)://` only).
* `ON DELETE CASCADE` from users to their profile, applications and notifications; `RESTRICT` stops deleting a drive that
  has applications (close it instead).
* Indexes on role, drive status/deadline, application student/drive/status, event history and notifications.

Multi-step writes (register, create application + first history event, status change + event + notification) run inside
one `BEGIN IMMEDIATE … COMMIT` transaction and roll back together on any error.

## Security

| Concern | How |
|---|---|
| SQL injection | Every statement uses `?` placeholders; the only f-string SQL builds a `SET` list from hard-coded column names. Tests try classic injection payloads. |
| Passwords | **bcrypt** with per-user salt (cost 12). Plaintext is never stored or logged. Same error for unknown email and wrong password; 5 failures lock that email for 5 minutes (in-process). |
| Roles | Public sign-up can only create students. Admins come from the one-time setup screen / CLI. Every service call starts with `require_role()`, which re-reads the role from SQLite, so a tampered user object or stale session grants nothing. |
| Data isolation | Students only see published drives (plus ones they track), only their own applications, history and notifications. Admin pages re-verify the role on every load. |
| Eligibility | Evaluated inside the same transaction that inserts the application. **Missing profile data is "unknown", never eligible.** |
| Status changes | Validated against one transition table; every change is recorded in `application_events` with who made it. |
| XSS | User-supplied text is HTML-escaped before it reaches any `unsafe_allow_html` block. |

Application stages: Interested → Applied/Withdrawn · Applied → Assessment/Technical/HR/Selected/Rejected/Withdrawn ·
Assessment → Technical/HR/Selected/Rejected/Withdrawn · Technical → HR/Selected/Rejected/Withdrawn ·
HR → Selected/Rejected/Withdrawn · Selected → Withdrawn · Rejected and Withdrawn are final.

## The UI

A pure-CSS 3D scene sits behind every page: a moving perspective grid floor, rotating glass cubes, spinning rings and a slow aurora,
with glassmorphism cards, gradient metric tiles that tilt on hover, and dark Plotly charts. No JavaScript, images or
extra packages. It honours "reduce motion" system settings and hides some objects on small screens.
All styling is in `ui/theme.py` (and `.streamlit/config.toml` for the base dark theme) if you want to change colours.

## Limitations (MVP)

* The login throttle is per server process and is reset on restart.
* Sessions live in Streamlit's session state: refreshing the browser tab signs you out.
* Reminders are generated when a student opens their dashboard/notifications (there is no background job, email or SMS).
* SQLite suits one college's traffic on one machine; for a multi-server deployment move to a client/server database.
* Deleting is deliberately not supported: close drives, withdraw applications; history stays intact.
