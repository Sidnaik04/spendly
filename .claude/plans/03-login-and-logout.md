# Plan: Step 3 — Login and Logout

## Context
Spec: `.claude/specs/03-login-and-logout.md`. `/login` is GET-only, so the sign-in form posts to a route that rejects POST. `/logout` is a stub string. Registered users can't sign in. This step adds credential checking, a Flask `session`, real logout, and a navbar that changes when someone is signed in. Profile (Step 4) and route protection are out of scope.

## Changes (in order)

### 1. `app.py`
- Import `session` from `flask` and `check_password_hash` from `werkzeug.security`.
- Add `_validate_login(email, password)` next to `_validate_registration()`. It returns `"Email and password are required."` if either value is empty, otherwise `None`. It does not touch the DB.
- `login()` → `methods=["GET", "POST"]`:
  1. If `session.get("user_id")` is set, `redirect(url_for("profile"))`. This happens before the GET/POST branch.
  2. GET: render `login.html`.
  3. POST: `email = request.form.get("email", "").strip().lower()` and `password = request.form.get("password", "")`. Don't strip the password.
  4. If validation fails, render `login.html` with `error` and `email`, status **400**.
  5. `user = get_user_by_email(email)` (reuse `database/db.py`). If there's no user, or `check_password_hash(user["password_hash"], password)` is false, render with "Invalid email or password." and `email`, status **401**. It's one combined check, so the message is the same either way.
  6. On success: `session.clear()`, set `session["user_id"]` and `session["user_name"]`, then `redirect(url_for("profile"))`.
- `logout()`: move it out of the placeholder section, keeping its name and GET method. It runs `session.clear()`, **then** `flash("You've been signed out.", "success")`, then `redirect(url_for("login"))`. The flash has to come after the clear, because flashes are stored in the session.
- `database/db.py` doesn't change.

### 2. `templates/login.html`
- Add `value="{{ email or '' }}"` to the email input. The password input gets no value. The existing flash block already styles the logout message with `auth-success`.

### 3. `templates/base.html` (nav, lines 21–24)
- `{% if session.user_id %}`: `<span class="nav-user">{{ session.user_name }}</span>` + `<a href="{{ url_for('logout') }}" class="nav-cta">Sign out</a>`
- `{% else %}`: keep the existing "Sign in" and "Get started" links.
- "Sign out" uses `nav-cta` so the existing rule at `style.css:693` (`.nav-links a:not(.nav-cta) { display:none }`) leaves it visible on mobile, with no new override needed.

### 4. `static/css/style.css`
- Add `.nav-user` after the `.nav-cta` rules (around line 115), using only variables: `color: var(--ink-muted)` and `font-family: var(--font-body)`, plus `font-weight: 500` and ellipsis overflow with a small max-width.
- In the 600px media query, add `.nav-user { display: none; }` so phones show only the "Sign out" button.

### 5. `tests/test_registration.py`
- In `test_stub_routes_unchanged` (lines 193–198), remove the `/logout` "coming in Step 3" case and keep `/profile`.

### 6. New `tests/test_auth.py`
Follow the conventions in `test_registration.py`:
- module-level message constants
- a `post_login(client, follow_redirects=False, **overrides)` helper
- `read_project_file`
- section banners
- `import database.db as db` only, never `app`

Read and set the session with `client.session_transaction()`. Get the demo user's id with `db.get_user_by_email("demo@spendly.com")["id"]`.

Tests, mapped to the Definition of done:
- `test_get_login_ok`: 200, and the form is rendered
- `test_login_success_redirects_and_sets_session`: 302 to `/profile`; `user_id` and `user_name` are in the session
- `test_login_normalises_email` (`"  DEMO@Spendly.com "`)
- `test_login_wrong_password`: 401, message shown, no `user_id` in the session
- `test_login_unknown_email`: 401, same message
- `test_login_missing_fields`: parametrized over email empty, password empty, both empty, and whitespace-only email. Each gives 400.
- `test_failed_login_keeps_email`: the email value is kept, and the password input has no `value=`
- `test_register_then_login`
- `test_login_redirects_when_signed_in`
- `test_navbar_signed_in` and `test_navbar_signed_out`: check only the `<nav>…</nav>` slice of the page body. Both `landing.html` and `login.html` contain "Sign in" and "Get started" text outside the nav.
- `test_logout_clears_session_and_flashes`: 302 to `/login`, the session is empty, the message shows once, and it's gone on the next GET
- `test_logout_when_signed_out`: 302 to `/login`
- `test_templates_use_url_for`: no `href="/` or `action="/` in `base.html` or `login.html`
- `test_nav_user_css_uses_variables`: no `#` in the `.nav-user` block
- `test_other_pages_still_render`: `/`, `/register`, `/terms` and `/privacy` return 200, and `/profile` still shows its Step 4 stub

### 7. `CLAUDE.md`
- In the routes table, mark `GET/POST /login` and `GET /logout` as implemented in Step 3.

## Verification
1. `pytest -v`: every test passes, including the existing registration tests. Check that the modification time of `spendly.db` doesn't change.
2. A subagent verifies the test results, per the policy in `CLAUDE.md`.
3. Run `python app.py` (port 5001) and check by hand:
   - Signing in as demo@spendly.com / demo123 lands on the profile stub, and the nav shows "Demo User" and "Sign out".
   - A wrong password shows the error and keeps the email.
   - Visiting `/login` while signed in redirects.
   - "Sign out" goes to `/login` with a one-time green message.
   - Below 600px, "Sign out" stays visible.
