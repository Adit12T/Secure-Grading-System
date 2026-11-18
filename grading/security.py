import functools
import time
from collections import defaultdict
from threading import Lock

from flask import abort, current_app, g, redirect, session, url_for

from .db import get_db


def load_user():
    """Loads the signed-in user. A session from before the last password change is ended."""
    g.user = None
    user_id = session.get("user_id")
    if user_id is None:
        return
    user = get_db().execute(
        "SELECT id, username, full_name, email, role, password_hash FROM user WHERE id = ?", (user_id,)).fetchone()
    if user is None or user["password_hash"][-16:] != session.get("pw"):
        session.clear()
        return
    g.user = user


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
        recent = [t for t in self._failures.get(key, ()) if now - t < window]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def is_locked(self, username: str) -> bool:
        with self._lock:
            return len(self._recent(username.lower())) >= current_app.config["LOGIN_MAX_FAILURES"]

    MAX_TRACKED = 10_000

    def fail(self, username: str) -> None:
        with self._lock:
            key = username.lower()
            if key not in self._failures and len(self._failures) >= self.MAX_TRACKED:
                # Bounded memory: forget every name whose failures have all expired.
                for stale in [k for k in self._failures if not self._recent(k)]:
                    self._failures.pop(stale, None)
            self._failures[key] = self._recent(key) + [time.monotonic()]

    def reset(self, username: str) -> None:
        with self._lock:
            self._failures.pop(username.lower(), None)


throttle = LoginThrottle()
