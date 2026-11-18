from flask_wtf import FlaskForm
from wtforms import EmailField, FloatField, PasswordField, SelectField, StringField
from wtforms.validators import Email, EqualTo, InputRequired, Length, NumberRange, Optional, Regexp


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(max=40)])
    password = PasswordField("Password", validators=[InputRequired(), Length(max=128)])


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[
        InputRequired(), Length(min=3, max=40),
        Regexp(r"^[A-Za-z0-9._-]+$", message="Use letters, digits, dots, dashes or underscores.")])
    full_name = StringField("Full name", validators=[InputRequired(), Length(max=80)])
    email = EmailField("Email", validators=[InputRequired(), Email(check_deliverability=False), Length(max=254)])
    password = PasswordField("Password", validators=[
        InputRequired(), Length(min=12, max=128, message="Use at least 12 characters.")])
    confirm = PasswordField("Confirm password", validators=[EqualTo("password", message="Passwords must match.")])


class ForgotForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired(), Email(check_deliverability=False)])


class ResetForm(FlaskForm):
    password = PasswordField("New password", validators=[InputRequired(), Length(min=12, max=128)])
    confirm = PasswordField("Confirm password", validators=[EqualTo("password", message="Passwords must match.")])


def score_field(label: str) -> FloatField:
    return FloatField(label, validators=[Optional(), NumberRange(min=0, max=100)])


class GradeForm(FlaskForm):
    midterm1 = score_field("Midterm 1")
    midterm2 = score_field("Midterm 2")
    midterm3 = score_field("Midterm 3")
    final = score_field("Final")


class CourseForm(FlaskForm):
    course_id = StringField("Course code", validators=[
        InputRequired(), Regexp(r"^[A-Z]{2,5}[0-9]{2,4}$", message="For example CSCE145.")])
    name = StringField("Course name", validators=[InputRequired(), Length(max=100)])
    faculty_id = SelectField("Instructor", coerce=int)


class EnrollForm(FlaskForm):
    student_id = SelectField("Student", coerce=int)
