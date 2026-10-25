-- PlaceTrack SQLite schema. Executed automatically on startup (idempotent).
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE CHECK (length(email) BETWEEN 3 AND 254),
    password_hash TEXT    NOT NULL,
    full_name     TEXT    NOT NULL CHECK (length(full_name) BETWEEN 1 AND 120),
    role          TEXT    NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin')),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS student_profiles (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    department      TEXT    CHECK (department IS NULL OR length(department) BETWEEN 1 AND 60),
    graduation_year INTEGER CHECK (graduation_year IS NULL OR graduation_year BETWEEN 2000 AND 2100),
    cgpa            REAL    CHECK (cgpa IS NULL OR (cgpa >= 0 AND cgpa <= 10)),
    backlogs        INTEGER CHECK (backlogs IS NULL OR (backlogs >= 0 AND backlogs <= 50)),
    skills          TEXT    NOT NULL DEFAULT '[]',          -- JSON array of strings
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS placement_drives (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name         TEXT    NOT NULL CHECK (length(company_name) BETWEEN 1 AND 120),
    role_title           TEXT    NOT NULL CHECK (length(role_title) BETWEEN 1 AND 120),
    package_lpa          REAL    CHECK (package_lpa IS NULL OR package_lpa >= 0),
    description          TEXT    NOT NULL DEFAULT '' CHECK (length(description) <= 5000),
    location             TEXT    CHECK (location IS NULL OR length(location) <= 120),
    min_cgpa             REAL    CHECK (min_cgpa IS NULL OR (min_cgpa >= 0 AND min_cgpa <= 10)),
    eligible_departments TEXT    NOT NULL DEFAULT '[]',     -- JSON array; [] = all departments
    eligible_years       TEXT    NOT NULL DEFAULT '[]',     -- JSON array; [] = all years
    max_backlogs         INTEGER CHECK (max_backlogs IS NULL OR max_backlogs >= 0),
    deadline             TEXT,                              -- ISO-8601 UTC
    application_url      TEXT    CHECK (application_url IS NULL
                                        OR application_url LIKE 'http://%' OR application_url LIKE 'https://%'),
    status               TEXT    NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'closed')),
    is_sample            INTEGER NOT NULL DEFAULT 0 CHECK (is_sample IN (0, 1)),
    created_by           INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    drive_id     INTEGER NOT NULL REFERENCES placement_drives(id) ON DELETE RESTRICT,
    status       TEXT    NOT NULL DEFAULT 'interested'
                 CHECK (status IN ('interested', 'applied', 'assessment', 'technical_interview',
                                   'hr_interview', 'selected', 'rejected', 'withdrawn')),
    interview_at TEXT,
    notes        TEXT    CHECK (notes IS NULL OR length(notes) <= 2000),
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (student_id, drive_id)                           -- no duplicate applications
);

CREATE TABLE IF NOT EXISTS application_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    from_status    TEXT,
    to_status      TEXT    NOT NULL,
    changed_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    drive_id   INTEGER REFERENCES placement_drives(id) ON DELETE SET NULL,
    title      TEXT    NOT NULL CHECK (length(title) <= 200),
    message    TEXT    NOT NULL CHECK (length(message) <= 1000),
    dedupe_key TEXT,
    is_read    INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (user_id, dedupe_key)
);

CREATE INDEX IF NOT EXISTS idx_users_role               ON users(role);
CREATE INDEX IF NOT EXISTS idx_drives_status_deadline   ON placement_drives(status, deadline);
CREATE INDEX IF NOT EXISTS idx_applications_student     ON applications(student_id);
CREATE INDEX IF NOT EXISTS idx_applications_drive       ON applications(drive_id);
CREATE INDEX IF NOT EXISTS idx_applications_status      ON applications(status);
CREATE INDEX IF NOT EXISTS idx_events_application       ON application_events(application_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_user       ON notifications(user_id, is_read, created_at);
