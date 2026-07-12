"""Authentication and role-based access control."""
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_user, logout_user, login_required, current_user

from .models import db, User
from . import audit

auth_bp = Blueprint("auth", __name__)


def editor_required(f):
    """Authorization enforced on the route, not by hiding buttons in the UI."""
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.can_edit():
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # ORM query: parameterised, never string-concatenated
        user = db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if user and user.check_password(password):
            login_user(user)
            audit.record("LOGIN", f"user:{user.username}")
            return redirect(url_for("main.dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
