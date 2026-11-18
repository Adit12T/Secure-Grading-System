import logging
import os
import sqlite3

from flask import Blueprint, current_app, flash, g, redirect, render_template, session, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from .db import audit, get_db
from .forms import ForgotForm, LoginForm, ResetForm, SignupForm
from .security import load_user, login_required, throttle

bp = Blueprint("auth", __name__)
log = logging.getLogger(__name__)

# A real hash to compare against when the username does not exist, so response time doesn't reveal it.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _deliver_reset_link(user_id: int, link: str) -> None:
    """Hands the link to the mailer. No mailer is configured, so: tests capture it, development logs it,
    and production logs only that a reset was requested (a link in a log would let log readers take over accounts)."""
    if current_app.testing:
        current_app.extensions.setdefault("sent_reset_links", []).append(link)
    elif current_app.debug or os.environ.get("FLASK_ENV") != "production":
        log.info("Password reset link (development only): %s", link)
    else:
        log.warning("Password reset requested for user %s, but no mailer is configured.", user_id)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


@bp.route("/", methods=["GET"])
def index():
    load_user()
    if g.user is None:
        return redirect(url_for("auth.login"))
    return redirect(url_for("admin.courses" if g.user["role"] == "admin" else "grades.home"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        if throttle.is_locked(username):
            flash("Too many failed attempts. Try again in 15 minutes.", "error")
            return render_template("login.html", form=form), 429
        user = get_db().execute("SELECT id, password_hash FROM user WHERE username = ?", (username,)).fetchone()
        valid = check_password_hash(user["password_hash"] if user else _DUMMY_HASH, form.password.data)
        if user and valid:
            throttle.reset(username)
            session.clear()  # new session on login prevents session fixation
            session["user_id"] = user["id"]
            session["pw"] = user["password_hash"][-16:]  # sessions end when the password changes
            session.permanent = True
            audit(user["id"], "login")
            get_db().commit()
            return redirect(url_for("auth.index"))
        throttle.fail(username)
        flash("Incorrect username or password.", "error")  # same message whichever was wrong
    return render_template("login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Self-registration creates student accounts only; faculty and admins are created by an admin."""
    form = SignupForm()
    if form.validate_on_submit():
        db = get_db()
        try:
            db.execute(
                "INSERT INTO user (username, full_name, email, password_hash, role) VALUES (?, ?, ?, ?, 'student')",
                (form.username.data.strip(), form.full_name.data.strip(), form.email.data.strip().lower(),
                 generate_password_hash(form.password.data)))
            db.commit()
        except sqlite3.IntegrityError:
            flash("That username or email is already registered.", "error")
            return render_template("signup.html", form=form), 409
        flash("Account created. Please sign in.", "info")
        return redirect(url_for("auth.login"))
    return render_template("signup.html", form=form)


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    """Sends a signed, single-purpose link that expires in 30 minutes. Passwords are never sent anywhere."""
    form = ForgotForm()
    if form.validate_on_submit():
        user = get_db().execute("SELECT id, password_hash FROM user WHERE email = ?",
                                (form.email.data.strip().lower(),)).fetchone()
        if user:
            # Binding the token to the current hash makes it stop working once the password changes.
            token = _serializer().dumps({"id": user["id"], "h": user["password_hash"][-16:]})
            link = url_for("auth.reset", token=token, _external=True)
            _deliver_reset_link(user["id"], link)
        # Same answer whether or not the email exists, so accounts cannot be enumerated.
        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("forgot.html", form=form)


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token: str):
    try:
        data = _serializer().loads(token, max_age=current_app.config["RESET_TOKEN_MAX_AGE"])
    except (SignatureExpired, BadSignature):
        flash("That reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot"))
    db = get_db()
    user = db.execute("SELECT id, password_hash FROM user WHERE id = ?", (data.get("id"),)).fetchone()
    if user is None or user["password_hash"][-16:] != data.get("h"):
        flash("That reset link has already been used.", "error")
        return redirect(url_for("auth.forgot"))
    form = ResetForm()
    if form.validate_on_submit():
        db.execute("UPDATE user SET password_hash = ? WHERE id = ?",
                   (generate_password_hash(form.password.data), user["id"]))
        audit(user["id"], "password_reset")
        db.commit()
        flash("Password updated. Please sign in.", "info")
        return redirect(url_for("auth.login"))
    return render_template("reset.html", form=form)


@bp.route("/account")
@login_required()
def account():
    return render_template("account.html")
