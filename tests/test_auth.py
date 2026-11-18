from conftest import PASSWORD, csrf, login


def test_login_redirects_by_role_and_rejects_wrong_password(client):
    assert login(client, "alex").headers["Location"] == "/"
    assert client.get("/").headers["Location"] == "/grades/"
    client.get("/logout")
    resp = login(client, "alex", "wrong-password")
    assert b"Incorrect username or password." in resp.data


def test_unknown_user_gets_the_same_message(client):
    assert b"Incorrect username or password." in login(client, "nobody").data


def test_requests_without_a_csrf_token_are_rejected(client):
    resp = client.post("/login", data={"username": "alex", "password": PASSWORD})
    assert resp.status_code == 400


def test_lockout_after_repeated_failures(client):
    for _ in range(5):
        login(client, "alex", "wrong")
    assert login(client, "alex").status_code == 429


def test_signup_creates_students_only_and_hashes_passwords(client, app):
    data = {"username": "carol", "full_name": "Carol", "email": "carol@example.com",
            "password": "a-long-password-1", "confirm": "a-long-password-1", "role": "admin",
            "csrf_token": csrf(client, "/signup")}
    assert client.post("/signup", data=data).status_code == 302
    with app.app_context():
        from grading.db import get_db
        row = get_db().execute("SELECT role, password_hash FROM user WHERE username = 'carol'").fetchone()
    assert row["role"] == "student"
    assert row["password_hash"].startswith(("scrypt:", "pbkdf2:")) and "a-long-password-1" not in row["password_hash"]


def test_signup_rejects_short_passwords_and_duplicates(client):
    data = {"username": "dan", "full_name": "Dan", "email": "dan@example.com",
            "password": "short", "confirm": "short", "csrf_token": csrf(client, "/signup")}
    assert b"at least 12 characters" in client.post("/signup", data=data).data
    data.update(username="alex", password="a-long-password-1", confirm="a-long-password-1",
                csrf_token=csrf(client, "/signup"))
    assert client.post("/signup", data=data).status_code == 409


def test_password_reset_link_works_once(client, app):
    client.post("/forgot", data={"email": "bina@example.com", "csrf_token": csrf(client, "/forgot")})
    link = app.extensions["sent_reset_links"][-1].replace("http://localhost", "")
    new = {"password": "brand-new-password", "confirm": "brand-new-password", "csrf_token": csrf(client, link)}
    assert client.post(link, data=new).headers["Location"] == "/login"
    assert login(client, "bina", "brand-new-password").headers["Location"] == "/"
    client.post("/logout", data={"csrf_token": csrf(client, "/account")})
    assert client.get(link).headers["Location"] == "/forgot"  # already used


def test_forgot_password_does_not_reveal_whether_an_email_exists(client, app):
    a = client.post("/forgot", data={"email": "nobody@example.com", "csrf_token": csrf(client, "/forgot")},
                    follow_redirects=True)
    assert b"If that email is registered" in a.data
    assert "sent_reset_links" not in app.extensions


def test_security_headers(client):
    headers = client.get("/login").headers
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
