import functools
import time
from collections import defaultdict
from threading import Lock

from flask import abort, current_app, g, redirect, session, url_for

from .db import get_db


def load_user():
    user_id = session.get("user_id")
    g.user = None if user_id is None else get_db().execute(
        "SELECT id, username, full_name, email, role FROM user WHERE id = ?", (user_id,)).fetchone()


def login_required(*roles: str):
    """Requires a signed-in user, and one of the given roles if any are listed."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped(**kwargs):
            load_user()
            if g.user is None:
                return redirect(url_for("auth.login"))
            if roles and g.user["role"] not in roles:
                abort(403)
            return view(**kwargs)
        return wrapped
    return decorator


class LoginThrottle:
    """Locks a username after repeated failures, to slow password guessing. In memory, per process."""

    def __init__(self):
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _recent(self, key: str) -> list[float]:
        window = current_app.config["LOGIN_LOCKOUT_SECONDS"]
        now = time.monotonic()
        self._failures[key] = [t for t in self._failures[key] if now - t < window]
        return self._failures[key]

    def is_locked(self, username: str) -> bool:
        with self._lock:
            return len(self._recent(username.lower())) >= current_app.config["LOGIN_MAX_FAILURES"]

    def fail(self, username: str) -> None:
        with self._lock:
            self._recent(username.lower()).append(time.monotonic())

    def reset(self, username: str) -> None:
        with self._lock:
            self._failures.pop(username.lower(), None)


throttle = LoginThrottle()
