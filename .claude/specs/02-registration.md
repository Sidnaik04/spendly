# Spec: Registration

## Overview
Make the existing registration page work so new users can create a Spendly account. Right now `GET /register` only shows a form, and the form posts to a route that does not accept POST. This step adds POST handling to `/register`. It validates the input, rejects duplicate emails, hashes the password with werkzeug, saves the user to the `users` table, and redirects to the login page with a success message. Registration comes before login (Step 3) because a user needs an account before they can sign in. This step does **not** start a session or log the user in. That belongs to Step 3.

## Depends on
- **Step 1 — Database setup**: `get_db()`, `init_db()` and the `users` table (`id`, `name`, `email UNIQUE`, `password_hash`, `created_at`) in `database/db.py`.

## Routes
- `GET /register` — render the registration form (already exists; keep its behaviour) — public
- `POST /register` — validate the form, create the user, then redirect to `login` with a flashed success message. If validation fails, re-render `register.html` with an error and the name and email the user entered — public

Both methods are handled by the existing `register()` function: `@app.route("/register", methods=["GET", "POST"])`.

## Database changes
No database changes. The `users` table in `database/db.py` already has every column needed, and `UNIQUE` on `email` enforces no duplicates.

New helper functions in `database/db.py` (no schema change):
- `get_user_by_email(email)` — returns the `users` row as a `sqlite3.Row`, or `None`
- `create_user(name, email, password)` — hashes `password` with `generate_password_hash`, inserts the row with a parameterised query, commits, and returns the new user's `id`. Raises `sqlite3.IntegrityError` if the email is taken, which covers the race between the existence check and the insert.

Both helpers open their connection with `get_db()` and close it in a `finally` block, matching `init_db()` and `seed_db()`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html`
    - change `action="/register"` to `action="{{ url_for('register') }}"`, since URLs must not be hardcoded
    - add `value="{{ name or '' }}"` and `value="{{ email or '' }}"` so the form keeps what the user typed after a validation error. The password field is never refilled.
    - add `minlength="8"` to the password input to match server-side validation
  - `templates/login.html`
    - show flashed messages above the form, using `get_flashed_messages(with_categories=true)`, so the "Account created" message appears after the redirect
    - change `action="/login"` to `action="{{ url_for('login') }}"`. This is a one-line fix to the same hardcoded-URL rule; the login logic itself stays in Step 3.

## Files to change
- `app.py`
  - import `request`, `redirect`, `url_for`, `flash` from `flask`
  - import `get_user_by_email` and `create_user` from `database.db`
  - set `app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")`, which `flash()` needs
  - update `register()` to accept GET and POST and add the validation, create and redirect flow
- `database/db.py` — add `get_user_by_email()` and `create_user()`
- `templates/register.html` — see Templates
- `templates/login.html` — see Templates
- `static/css/style.css` — add an `.auth-success` class next to `.auth-error`, using only CSS variables (`var(--accent)`, `var(--accent-light)`, `var(--radius-sm)`, and so on)

## Files to create
- `tests/conftest.py` — pytest fixtures: point `database.db.DB_PATH` at a temporary file, run `init_db()`, and provide the Flask `app` and `client` (with `TESTING = True`)
- `tests/test_registration.py` — tests for the Definition of done items below

## New dependencies
No new dependencies. `flask`, `werkzeug`, `pytest` and `pytest-flask` are already in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs. Use `sqlite3` through `get_db()` only.
- Parameterised queries only (`?` placeholders). Never use f-strings or `%` formatting in SQL.
- Hash passwords with werkzeug's `generate_password_hash`. Never store or log the plain password.
- Use CSS variables. Never hardcode hex values in new CSS.
- All templates extend `base.html`.
- No DB logic in `app.py`. The route calls `get_user_by_email()` and `create_user()` only.
- Use `url_for()` for every internal link and form action, in templates and in `redirect()`.
- Normalise input before validating it: `name.strip()`, and `email.strip().lower()`.
- Validation rules, checked in this order. Re-render on the first failure with one clear message:
  1. All fields present: "All fields are required."
  2. Email contains `@` and a `.` after it: "Please enter a valid email address."
  3. Password is at least 8 characters: "Password must be at least 8 characters."
  4. Email not already registered: "An account with this email already exists."
- Re-render validation failures with HTTP status `400`. Use `render_template`, not `abort()`, so the user sees the form again.
- Catch `sqlite3.IntegrityError` from `create_user()` and treat it the same as a duplicate email.
- After a successful insert, `flash("Account created — please sign in.", "success")` and `redirect(url_for("login"))` (POST/redirect/GET).
- Do not implement login, logout or sessions. They belong to Step 3.
- Vanilla JS only. No JS is needed for this step.

## Definition of done
- [ ] `GET /register` returns 200 and shows the form
- [ ] The form's action renders as `/register` via `url_for`, and nothing in `register.html` or `login.html` is hardcoded
- [ ] Submitting a valid name, email and password (8+ characters) creates a row in `users` and redirects (302) to `/login`
- [ ] `/login` shows the "Account created — please sign in." message after that redirect, and the message is gone on refresh
- [ ] The stored `password_hash` is not the plain password, and `check_password_hash(hash, password)` returns `True`
- [ ] Email is stored lowercased and trimmed (`  Foo@Bar.com ` is stored as `foo@bar.com`)
- [ ] Registering an existing email (`demo@spendly.com`, in any letter case) shows "An account with this email already exists." with status 400 and adds no row
- [ ] Submitting with any field empty shows "All fields are required." with status 400
- [ ] Submitting an invalid email shows "Please enter a valid email address." with status 400
- [ ] Submitting a 7-character password shows "Password must be at least 8 characters." with status 400
- [ ] After a validation error, the name and email fields keep their values and the password field is empty
- [ ] The success message is styled with `.auth-success`, which uses only CSS variables
- [ ] `pytest` passes, and the tests use a temporary database, not `spendly.db`
- [ ] The app still starts with `python app.py` on port 5001, and the other routes behave as before
