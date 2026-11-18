from flask import Blueprint, abort, flash, g, redirect, render_template, url_for

from .db import audit, get_db
from .forms import GradeForm
from .security import login_required

bp = Blueprint("grades", __name__, url_prefix="/grades")

WEIGHTS = {"midterm1": 0.2, "midterm2": 0.2, "midterm3": 0.2, "final": 0.4}


def letter(row) -> tuple[float | None, str]:
    """Weighted total over the scores entered so far, and its letter grade."""
    entered = {k: row[k] for k in WEIGHTS if row[k] is not None}
    if not entered:
        return None, "—"
    total = sum(WEIGHTS[k] * v for k, v in entered.items()) / sum(WEIGHTS[k] for k in entered)
    for cutoff, grade in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if total >= cutoff:
            return round(total, 1), grade
    return round(total, 1), "F"


@bp.route("/")
@login_required("student", "faculty")
def home():
    db = get_db()
    if g.user["role"] == "student":
        rows = db.execute(
            "SELECT c.id, c.name, f.full_name AS instructor, e.* FROM enrollment e "
            "JOIN course c ON c.id = e.course_id JOIN user f ON f.id = c.faculty_id "
            "WHERE e.student_id = ? ORDER BY c.id", (g.user["id"],)).fetchall()
        return render_template("student_grades.html", rows=[(r, *letter(r)) for r in rows])
    courses = db.execute(
        "SELECT c.id, c.name, COUNT(e.student_id) AS students FROM course c "
        "LEFT JOIN enrollment e ON e.course_id = c.id WHERE c.faculty_id = ? GROUP BY c.id ORDER BY c.id",
        (g.user["id"],)).fetchall()
    return render_template("faculty_home.html", courses=courses)


def _own_course(course_id: str):
    """Faculty may only see and change courses they teach; anything else is a 404, not a hint."""
    course = get_db().execute("SELECT id, name FROM course WHERE id = ? AND faculty_id = ?",
                              (course_id, g.user["id"])).fetchone()
    if course is None:
        abort(404)
    return course


@bp.route("/course/<course_id>")
@login_required("faculty")
def course(course_id: str):
    c = _own_course(course_id)
    rows = get_db().execute(
        "SELECT u.id AS student_id, u.full_name, e.* FROM enrollment e JOIN user u ON u.id = e.student_id "
        "WHERE e.course_id = ? ORDER BY u.full_name", (c["id"],)).fetchall()
    return render_template("course.html", course=c, rows=[(r, *letter(r)) for r in rows])


@bp.route("/course/<course_id>/student/<int:student_id>", methods=["GET", "POST"])
@login_required("faculty")
def edit(course_id: str, student_id: int):
    c = _own_course(course_id)
    db = get_db()
    row = db.execute("SELECT e.*, u.full_name FROM enrollment e JOIN user u ON u.id = e.student_id "
                     "WHERE e.course_id = ? AND e.student_id = ?", (c["id"], student_id)).fetchone()
    if row is None:
        abort(404)
    form = GradeForm(data={k: row[k] for k in WEIGHTS})
    if form.validate_on_submit():
        db.execute("UPDATE enrollment SET midterm1 = ?, midterm2 = ?, midterm3 = ?, final = ?, "
                   "updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE course_id = ? AND student_id = ?",
                   (form.midterm1.data, form.midterm2.data, form.midterm3.data, form.final.data,
                    g.user["id"], c["id"], student_id))
        audit(g.user["id"], "grade_update", f"{c['id']}:{student_id}")
        db.commit()
        flash(f"Saved grades for {row['full_name']}.", "info")
        return redirect(url_for("grades.course", course_id=c["id"]))
    return render_template("edit_grades.html", course=c, student=row, form=form)
