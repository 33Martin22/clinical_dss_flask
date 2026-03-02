"""routes/auth_routes.py — Login, register, logout."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth import login_user, register_user, set_session, clear_session, get_current_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return _role_redirect(get_current_user()["role"])

    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user, err = login_user(email, password)
        if err:
            error = err
        else:
            set_session(user)
            flash(f"Welcome back, {user['name']}!", "success")
            return _role_redirect(user["role"])

    return render_template("login.html", error=error)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if get_current_user():
        return redirect(url_for("patient.dashboard"))

    error = None
    if request.method == "POST":
        name       = request.form.get("name", "").strip()
        email      = request.form.get("email", "").strip()
        password   = request.form.get("password", "")
        confirm    = request.form.get("confirm_password", "")
        role       = request.form.get("role", "patient")
        age        = request.form.get("age")
        gender     = request.form.get("gender")
        conditions = request.form.get("conditions", "")

        if not all([name, email, password, confirm]):
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            age_val = int(age) if age and age.isdigit() else None
            user, err = register_user(name=name, email=email, password=password,
                                      role=role, age=age_val, gender=gender,
                                      conditions=conditions)
            if err:
                error = err
            else:
                set_session(user)
                flash("Account created successfully!", "success")
                return _role_redirect(user["role"])

    return render_template("register.html", error=error)


@auth_bp.route("/logout")
def logout():
    clear_session()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.landing"))


def _role_redirect(role: str):
    dest = {
        "patient": "patient.dashboard",
        "doctor":  "doctor.dashboard",
        "admin":   "admin.dashboard",
    }.get(role, "main.landing")
    return redirect(url_for(dest))
