import sqlite3

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


def audit(actor_id: int | None, action: str, detail: str = "") -> None:
    get_db().execute("INSERT INTO audit_log (actor_id, action, detail) VALUES (?, ?, ?)", (actor_id, action, detail))


def seed_demo() -> None:
    """Synthetic demo users; every password is 'demo-password-123'. Never use in production."""
    db = get_db()
    pw = generate_password_hash("demo-password-123")
    users = [
        ("admin", "Avery Admin", "admin@example.com", "admin"),
        ("prof.lee", "Dr. Morgan Lee", "lee@example.com", "faculty"),
        ("prof.diaz", "Dr. Sam Diaz", "diaz@example.com", "faculty"),
        ("alex", "Alex Student", "alex@example.com", "student"),
        ("bina", "Bina Student", "bina@example.com", "student"),
    ]
    db.executemany("INSERT INTO user (username, full_name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                   [(u, n, e, pw, r) for u, n, e, r in users])
    ids = {row["username"]: row["id"] for row in db.execute("SELECT id, username FROM user")}
    db.executemany("INSERT INTO course (id, name, faculty_id) VALUES (?, ?, ?)", [
        ("CSCE145", "Algorithmic Design", ids["prof.lee"]),
        ("CSCE522", "Information Security", ids["prof.diaz"]),
    ])
    db.executemany("INSERT INTO enrollment (student_id, course_id, midterm1, midterm2) VALUES (?, ?, ?, ?)", [
        (ids["alex"], "CSCE145", 88, 92), (ids["bina"], "CSCE145", 75, 81), (ids["alex"], "CSCE522", 95, None),
    ])
    db.commit()


@click.command("init-db")
def init_db_command() -> None:
    """Create a fresh, empty database."""
    init_db()
    click.echo("Initialised the database.")


@click.command("seed-demo")
def seed_demo_command() -> None:
    """Create a fresh database with synthetic demo data."""
    init_db()
    seed_demo()
    click.echo("Created demo users (password: demo-password-123).")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_demo_command)
