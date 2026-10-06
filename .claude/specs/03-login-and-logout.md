# Spec: Login and Logout

## Overview
Let registered users sign in and out of Spendly. Right now `GET /login` only shows a form, the form posts to a route that does not accept POST, and `/logout` returns a placeholder string. This step adds POST handling to `/login`: it looks up the user by email, checks the password with werkzeug's `check_password_hash`, and stores the user's id and name in Flask's signed `session` cookie. `/logout` clears the session and redirects to the login page with a message. The navbar changes based on whether someone is signed in. Login comes after registration (Step 2) because users need an account first, and before the profile page (Step 4) because that page needs to know who is signed in. This step does **not** build the profile page or protect other routes with a login check. Those belong to Step 4 and later.

## Depends on
- **Step 1 — Database setup**: `get_db()` and the `users` table (`id`, `name`, `email UNIQUE`, `password_hash`) in `database/db.py`, plus the seeded demo user (`demo@spendly.com` / `demo123`).
- **Step 2 — Registration**: `get_user_by_email()` in `database/db.py`, `app.secret_key` in `app.py`, the flash-message block in `login.html`, the `.auth-success` and `.auth-error` styles, and the test fixtures in `tests/conftest.py`.

## Routes
- `GET /login` — render the sign-in form (already exists; keep its behaviour). If the user is already signed in, redirect to the home page (`landing`) instead — public
- `POST /login` — validate the form, check the credentials, start a session, and redirect to the home page (`landing`). On failure, re-render `login.html` with an error and the email the user entered — public
- `GET/POST /register` — (existing) now redirects a signed-in user to the home page (`landing`) instead of showing the form — public
- `GET /logout` — clear the session, flash "You've been signed out.", and redirect to `login`. Works whether or not anyone is signed in — public

`/login` becomes `@app.route("/login", methods=["GET", "POST"])`. `/logout` keeps its existing route and function name and stays GET.

## Database changes
No database changes. The `users` table already has every column needed, and `get_user_by_email(email)` already exists. Do not add new helpers to `database/db.py` for this step.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html`
    - add `value="{{ email or '' }}"` to the email input so it keeps what the user typed after a failed sign-in. The password field is never refilled.
  - `templates/base.html`
    - change the navbar links based on `session.user_id`:
      - signed out: keep the current "Sign in" and "Get started" links
      - signed in: show the user's name (`session.user_name`) and a "Sign out" link to `url_for('logout')`
    - use `url_for()` for every link

## Files to change
- `app.py`
  - import `session` from `flask`
  - import `check_password_hash` from `werkzeug.security`
  - change `login()` to accept GET and POST and add the validate, check and session flow
  - replace the `logout()` stub with the real logout flow
  - add a `_validate_login(email, password)` helper next to `_validate_registration()` if the validation needs more than one line
- `templates/login.html` — see Templates
- `templates/base.html` — see Templates
- `static/css/style.css` — add a style for the signed-in user's name in the navbar (for example `.nav-user`), using only CSS variables (`var(--ink-muted)`, `var(--font-body)`, and so on)
- `CLAUDE.md` — mark `GET/POST /login` and `GET /logout` as implemented (Step 3) in the routes table

## Files to create
- `tests/test_auth.py` — tests for the Definition of done items below, using the `client` and `app_module` fixtures from `tests/conftest.py`. Never import `app` at module level.

## New dependencies
No new dependencies. `flask` and `werkzeug` are already in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs. Use `sqlite3` through `database/db.py` helpers only.
- Parameterised queries only (`?` placeholders). Never use f-strings or `%` formatting in SQL.
- Passwords are checked with werkzeug's `check_password_hash`. Never compare plain passwords, and never store or log the plain password.
- Use CSS variables. Never hardcode hex values in new CSS.
- All templates extend `base.html`.
- No DB logic in `app.py`. The route calls `get_user_by_email()` only.
- Use `url_for()` for every internal link and form action, in templates and in `redirect()`.
- Normalise the email before using it: `email.strip().lower()`, matching registration. Do not strip the password.
- Validation, checked in this order. Re-render on the first failure with one message:
  1. Both fields present: "Email and password are required." (status `400`)
  2. A user with that email exists **and** `check_password_hash(user["password_hash"], password)` is `True`. Otherwise: "Invalid email or password." (status `401`)
- Use the same message for an unknown email and a wrong password, so the form does not reveal which emails are registered.
- Re-render failures with `render_template`, not `abort()`, so the user sees the form again.
- On success: call `session.clear()` first, then set `session["user_id"]` and `session["user_name"]`, then `redirect(url_for("landing"))` (POST/redirect/GET).
- On logout: `session.clear()`, `flash("You've been signed out.", "success")`, then `redirect(url_for("login"))`.
- Do not implement the profile page, and do not add a login-required check to other routes. `/profile` stays a stub until Step 4.
- Vanilla JS only. No JS is needed for this step.

## Definition of done
- [ ] `GET /login` returns 200 and shows the form when signed out
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects (302) to `/`, and the session holds the demo user's `user_id` and `user_name`
- [ ] Signing in with `  DEMO@Spendly.com ` (any case, extra spaces) and the right password also works
- [ ] Signing in with a wrong password shows "Invalid email or password." with status 401 and sets no session
- [ ] Signing in with an unregistered email shows the same "Invalid email or password." message with status 401
- [ ] Submitting with either field empty shows "Email and password are required." with status 400
- [ ] After a failed sign-in, the email field keeps its value and the password field is empty
- [ ] A user who registers through `/register` can then sign in with the same email and password
- [ ] When signed in, `GET`/`POST` to `/login` or `/register` redirects to `/`
- [ ] When signed in, the navbar shows the user's name and a "Sign out" link, and does not show "Sign in" or "Get started"
- [ ] When signed out, the navbar shows "Sign in" and "Get started" as before
- [ ] `GET /logout` clears the session and redirects (302) to `/login`, which shows "You've been signed out." once; the message is gone on refresh
- [ ] `GET /logout` when not signed in still redirects to `/login` without an error
- [ ] Nothing in `login.html` or `base.html` is hardcoded; all links use `url_for()`
- [ ] New CSS uses only CSS variables
- [ ] `pytest` passes, including the existing registration tests, and the tests use a temporary database, not `spendly.db`
- [ ] The app still starts with `python app.py` on port 5001, and the other routes behave as before
