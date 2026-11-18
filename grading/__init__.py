"""Secure Grading System: a Flask app where faculty record grades and students see only their own."""
import os
import secrets
from datetime import timedelta

from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    secret = os.environ.get("SECRET_KEY")
    if not secret and os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("SECRET_KEY must be set in production.")
    app.config.from_mapping(
        SECRET_KEY=secret or secrets.token_hex(32),  # random per process in development
        DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "grading.sqlite")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
        MAX_CONTENT_LENGTH=64 * 1024,
        RESET_TOKEN_MAX_AGE=30 * 60,
        LOGIN_MAX_FAILURES=5,
        LOGIN_LOCKOUT_SECONDS=15 * 60,
    )
    if test_config:
        app.config.update(test_config)

    from . import db, auth, grades, admin
    db.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(grades.bp)
    app.register_blueprint(admin.bp)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'none'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", code=403, message="You do not have access to that page."), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="Page not found."), 404

    return app
