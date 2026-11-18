# Secure Grading System

[![CI](https://github.com/Adit12T/Secure-Grading-System/actions/workflows/ci.yml/badge.svg)](https://github.com/Adit12T/Secure-Grading-System/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Adit12T/Secure-Grading-System/actions/workflows/codeql.yml/badge.svg)](https://github.com/Adit12T/Secure-Grading-System/actions/workflows/codeql.yml)

A web app where faculty record grades and students see only their own, built with **Python 3.12,
Flask 3 and SQLite**, with the security controls you would expect around student records.

I first built this in 2017 for an Internet Security course at the University of South Carolina.
Looking back at it, the original had real flaws: passwords were stored with reversible encryption and
emailed back in plain text, a URL let anyone act as any faculty member, and there was no CSRF
protection. Version 2 is a rebuild that fixes each of them, with tests that prove it.

## What changed from the original

| Area | 2017 version | Version 2 |
|---|---|---|
| Password storage | Reversible encryption | One-way hashing (Werkzeug scrypt) |
| Forgot password | Decrypted the password and emailed it | Signed link that expires in 30 minutes and stops working once used |
| Access control | `/facultylogindisplay/<id>` signed you in as any faculty member | Every page checks the signed-in user's role; faculty see only courses they teach |
| Forms | No CSRF protection | CSRF token on every form (Flask-WTF) |
| Login | Revealed which part was wrong | One message for any failure, lockout after 5 failures, new session on sign-in |
| Account creation | Anyone could sign up as faculty | Self sign-up creates students only; staff are added by an admin |
| Secrets | Hard-coded in the source | `SECRET_KEY` from the environment; required in production |
| Browser hardening | None | Content Security Policy, no framing, `nosniff`, `no-store`, secure cookie flags |
| Record keeping | None | Audit log of sign-ins, password resets, grade changes and enrolments |
| Tests | None | 16 pytest tests covering each of the above |

## Features

- **Roles:** students view their grades; faculty grade the courses they teach; admins add courses,
  enrol students and read the audit log.
- **Grades:** three midterms and a final from 0 to 100, a weighted total (20/20/20/40) over the scores
  entered so far, and a letter grade.
- **Validation:** every input is checked server-side; the database also enforces score ranges, unique
  usernames and emails, and valid roles.

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
flask --app grading seed-demo     # synthetic users, password: demo-password-123
flask --app grading run           # http://127.0.0.1:5000
```

Demo accounts: `admin`, `prof.lee`, `prof.diaz`, `alex`, `bina`.

With Docker:

```bash
docker build -t grading .
docker run -p 8000:8000 -e SECRET_KEY=$(openssl rand -hex 32) -v grading-data:/data grading
```

(The container starts with an empty database; run `flask --app grading init-db` inside it first.)

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Limitations

- Password reset links are written to the application log instead of being emailed; plugging in an
  SMTP service is a configuration step.
- The login lockout is kept in memory per process; a multi-server deployment would need a shared store.
- SQLite suits a single server; a larger deployment would move to PostgreSQL.

## License

Copyright © 2026 Aditya Tripathi. All rights reserved. The code is published for viewing only; see
[LICENSE](LICENSE). Security reports: see [SECURITY.md](SECURITY.md).
