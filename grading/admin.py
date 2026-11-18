import sqlite3

from flask import Blueprint, abort, flash, g, redirect, render_template, url_for

from .db import audit, get_db
from .forms import CourseForm, EnrollForm
from .security import login_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/courses", methods=["GET", "POST"])
@login_required("admin")
def courses():
    db = get_db()
    form = CourseForm()
    form.faculty_id.choices = [(r["id"], r["full_name"]) for r in
                               db.execute("SELECT id, full_name FROM user WHERE role = 'faculty' ORDER BY full_name")]
    if form.validate_on_submit():
        try:
            db.execute("INSERT INTO course (id, name, faculty_id) VALUES (?, ?, ?)",
                       (form.course_id.data, form.name.data.strip(), form.faculty_id.data))
            audit(g.user["id"], "course_add", form.course_id.data)
            db.commit()
            flash(f"Added {form.course_id.data}.", "info")
            return redirect(url_for("admin.courses"))
        except sqlite3.IntegrityError:
            flash("That course code already exists.", "error")
    rows = db.execute("SELECT c.id, c.name, u.full_name AS instructor, "
                      "(SELECT COUNT(*) FROM enrollment e WHERE e.course_id = c.id) AS students "
                      "FROM course c JOIN user u ON u.id = c.faculty_id ORDER BY c.id").fetchall()
    return render_template("admin_courses.html", form=form, courses=rows)


@bp.route("/courses/<course_id>/enroll", methods=["GET", "POST"])
@login_required("admin")
def enroll(course_id: str):
    db = get_db()
    course = db.execute("SELECT id, name FROM course WHERE id = ?", (course_id,)).fetchone()
    if course is None:
        abort(404)
    form = EnrollForm()
    form.student_id.choices = [(r["id"], r["full_name"]) for r in db.execute(
        "SELECT id, full_name FROM user WHERE role = 'student' AND id NOT IN "
        "(SELECT student_id FROM enrollment WHERE course_id = ?) ORDER BY full_name", (course_id,))]
    if form.validate_on_submit():
        db.execute("INSERT INTO enrollment (student_id, course_id) VALUES (?, ?)", (form.student_id.data, course_id))
        audit(g.user["id"], "enroll", f"{course_id}:{form.student_id.data}")
        db.commit()
        flash("Student enrolled.", "info")
        return redirect(url_for("admin.courses"))
    return render_template("enroll.html", form=form, course=course)


@bp.route("/audit")
@login_required("admin")
def audit_log():
    rows = get_db().execute("SELECT a.at, u.username, a.action, a.detail FROM audit_log a "
                            "LEFT JOIN user u ON u.id = a.actor_id ORDER BY a.id DESC LIMIT 200").fetchall()
    return render_template("audit.html", rows=rows)
