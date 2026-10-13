import os
import sqlite3
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    create_user,
    get_category_breakdown,
    get_db,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _validate_registration(name, email, password):
    if not name or not email or not password:
        return "All fields are required."
    at = email.find("@")
    if at < 1 or "." not in email[at + 1:]:
        return "Please enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def _validate_login(email, password):
    if not email or not password:
        return "Email and password are required."
    return None


@app.template_filter("inr")
def _format_inr(value):
    return f"₹{value:,.2f}"


def _bar_step(pct):
    # Round to the nearest 5% so bar widths map to .bar-w-N classes
    return max(5, min(100, 5 * round(pct / 5)))


def _initials(name):
    return "".join(word[0] for word in name.split()[:2]).upper()


def _profile_context(user_id):
    user = get_user_by_id(user_id)
    if user is None:
        return None

    summary = get_summary_stats(user_id)
    transactions = [
        {
            **t,
            "slug": t["category"].lower(),
            "date_label": datetime.strptime(t["date"], "%Y-%m-%d").strftime("%d %b %Y"),
        }
        for t in get_recent_transactions(user_id)
    ]
    categories = [
        {
            "name": c["name"],
            "slug": c["name"].lower(),
            "total": c["amount"],
            "percent": c["pct"],
            "bar_step": _bar_step(c["pct"]),
        }
        for c in get_category_breakdown(user_id)
    ]

    return {
        "user": {**user, "initials": _initials(user["name"])},
        "stats": {
            "total": summary["total_spent"],
            "count": summary["transaction_count"],
            "top_category": summary["top_category"],
        },
        "transactions": transactions,
        "categories": categories,
    }


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = _validate_registration(name, email, password)
    if not error and get_user_by_email(email) is not None:
        error = "An account with this email already exists."
    if not error:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = "An account with this email already exists."

    if error:
        return render_template(
            "register.html", error=error, name=name, email=email
        ), 400

    flash("Account created — please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = _validate_login(email, password)
    if error:
        return render_template("login.html", error=error, email=email), 400

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error="Invalid email or password.", email=email
        ), 401

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    context = _profile_context(user_id)
    if context is None:
        session.clear()
        return redirect(url_for("login"))
    return render_template("profile.html", **context)


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
