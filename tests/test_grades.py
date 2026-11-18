from conftest import csrf, login


def test_student_sees_only_their_own_grades(client):
    login(client, "alex")
    page = client.get("/grades/").get_data(as_text=True)
    assert "CSCE145" in page and "CSCE522" in page
    assert "Bina" not in page


def test_students_cannot_open_faculty_or_admin_pages(client):
    login(client, "alex")
    assert client.get("/grades/course/CSCE145").status_code == 403
    assert client.get("/admin/courses").status_code == 403


def test_faculty_grades_their_course_and_the_change_is_audited(client):
    login(client, "prof.lee")
    path = "/grades/course/CSCE145/student/4"
    data = {"midterm1": "90", "midterm2": "95", "midterm3": "", "final": "88", "csrf_token": csrf(client, path)}
    assert client.post(path, data=data).status_code == 302
    page = client.get("/grades/course/CSCE145").get_data(as_text=True)
    assert "90.2" in page  # (90*.2 + 95*.2 + 88*.4) / .8
    client.post("/logout", data={"csrf_token": csrf(client, "/account")})
    login(client, "admin")
    assert "grade_update" in client.get("/admin/audit").get_data(as_text=True)


def test_faculty_cannot_touch_another_instructors_course(client):
    login(client, "prof.lee")
    assert client.get("/grades/course/CSCE522").status_code == 404
    path = "/grades/course/CSCE522/student/4"
    assert client.post(path, data={"final": "100", "csrf_token": csrf(client, "/account")}).status_code == 404


def test_scores_outside_0_to_100_are_rejected(client):
    login(client, "prof.lee")
    path = "/grades/course/CSCE145/student/4"
    resp = client.post(path, data={"final": "150", "csrf_token": csrf(client, path)})
    assert resp.status_code == 200 and b"between 0 and 100" in resp.data


def test_old_url_based_login_bypass_is_gone(client):
    assert client.get("/facultylogindisplay/1").status_code == 404
    assert client.get("/grades/").headers["Location"] == "/login"


def test_admin_adds_courses_and_enrolls_students(client):
    login(client, "admin")
    data = {"course_id": "CSCE240", "name": "Systems Programming", "faculty_id": "2",
            "csrf_token": csrf(client, "/admin/courses")}
    assert client.post("/admin/courses", data=data).status_code == 302
    data = {"student_id": "5", "csrf_token": csrf(client, "/admin/courses/CSCE240/enroll")}
    assert client.post("/admin/courses/CSCE240/enroll", data=data).status_code == 302
    assert "CSCE240" in client.get("/admin/courses").get_data(as_text=True)
