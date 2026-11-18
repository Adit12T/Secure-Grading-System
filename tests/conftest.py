import re

import pytest

from grading import create_app
from grading.db import init_db, seed_demo
from grading.security import throttle

PASSWORD = "demo-password-123"


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite"), "SECRET_KEY": "test-secret"})
    with app.app_context():
        init_db()
        seed_demo()
    throttle._failures.clear()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client, path: str) -> str:
    """Fetch a form page and return its CSRF token, as a browser would."""
    html = client.get(path).get_data(as_text=True)
    return re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', html).group(1)


def login(client, username: str, password: str = PASSWORD):
    return client.post("/login", data={"username": username, "password": password,
                                       "csrf_token": csrf(client, "/login")})
