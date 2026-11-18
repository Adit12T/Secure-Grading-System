PRAGMA foreign_keys = ON;

CREATE TABLE user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    full_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('student', 'faculty', 'admin')),
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE course (
    id         TEXT PRIMARY KEY CHECK (length(id) BETWEEN 3 AND 12),
    name       TEXT    NOT NULL,
    faculty_id INTEGER NOT NULL REFERENCES user (id)
);

CREATE TABLE enrollment (
    student_id INTEGER NOT NULL REFERENCES user (id) ON DELETE CASCADE,
    course_id  TEXT    NOT NULL REFERENCES course (id) ON DELETE CASCADE,
    midterm1   REAL CHECK (midterm1 BETWEEN 0 AND 100),
    midterm2   REAL CHECK (midterm2 BETWEEN 0 AND 100),
    midterm3   REAL CHECK (midterm3 BETWEEN 0 AND 100),
    final      REAL CHECK (final BETWEEN 0 AND 100),
    updated_by INTEGER REFERENCES user (id),
    updated_at TEXT,
    PRIMARY KEY (student_id, course_id)
);

CREATE TABLE audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    at        TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_id  INTEGER,
    action    TEXT    NOT NULL,
    detail    TEXT
);
