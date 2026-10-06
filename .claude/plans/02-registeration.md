# Plan: Step 2 — Registration

## Context
`/register` currently only renders a form whose POST goes nowhere. Spec `.claude/specs/02-registration.md` makes it work: validate input, reject duplicate emails, store a werkzeug-hashed password, then redirect to `/login` with a flashed success message. No login/session — that's Step 3. Branch: `feature/registration`.

Small additions beyond the spec (needed to make it work):
- `import os` / `import sqlite3` in `app.py` (secret key + IntegrityError).
- New `pytest.ini` (`[pytest]`, `testpaths = tests`, `pythonpath = .`) — without it `tests/` can't `import app`.
- Update `CLAUDE.md` routes table (`GET/POST /register` implemented) and the stale "`db.py` is currently empty" warning.

## 1. `database/db.py` — two helpers after `seed_db()`
Reuse the existing `conn = get_db(); try: … finally: conn.close()` pattern and the already-imported `generate_password_hash`.
- `get_user_by_email(email)` → `SELECT * FROM users WHERE email = ?` → `sqlite3.Row` or `None`. No normalisation here; the route owns it.
- `create_user(name, email, password)` → `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)` with the hashed password, commit, return `cursor.lastrowid`. Let `sqlite3.IntegrityError` propagate.

## 2. `app.py`
- Imports: `os`, `sqlite3`; extend Flask import with `request, redirect, url_for, flash`; import `get_user_by_email, create_user`.
- After `app = Flask(__name__)`: `app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")`.
- Pure helper `_validate_registration(name, email, password) -> str | None` (no DB), rules in order:
  1. any empty → "All fields are required."
  2. needs `@` at index ≥ 1 and a `.` after it → "Please enter a valid email address."
  3. `len(password) < 8` → "Password must be at least 8 characters."
- `register()` → `methods=["GET", "POST"]`:
  - GET: render as today.
  - POST: `name.strip()`, `email.strip().lower()`, password untouched. Validate, then `get_user_by_email` → "An account with this email already exists."; else `create_user` inside `try/except sqlite3.IntegrityError` (same message).
  - Error: `render_template("register.html", error=…, name=…, email=…), 400`.
  - Success: `flash("Account created — please sign in.", "success")`, `redirect(url_for("login"))`.
- Leave `login`, `terms`, `privacy`, stub routes, startup `init_db()/seed_db()` and port 5001 untouched.

## 3. Templates
- `templates/register.html`: `action="{{ url_for('register') }}"`; `value="{{ name or '' }}"` / `value="{{ email or '' }}"`; `minlength="8"` on password (never refilled).
- `templates/login.html`: `action="{{ url_for('login') }}"`; inside `.auth-card`, before the error block, loop `get_flashed_messages(with_categories=true)` → `auth-success` for `success`, else `auth-error`. No login logic.

## 4. `static/css/style.css`
Add `.auth-success` right after `.auth-error` (~line 528), same box model, variables only: `background: var(--accent-light); color: var(--accent); border: 1px solid var(--accent); border-radius: var(--radius-sm);` plus the same padding/font-size/margin. (The existing hardcoded `#f5c6c2` in `.auth-error` is out of scope.)

## 5. Tests
**`tests/conftest.py`** — `app` fixture: `monkeypatch.setattr(database.db, "DB_PATH", tmp_path/"test.db")`, then import `app` *lazily inside the fixture*, run `init_db()` + `seed_db()` each test, set `TESTING=True`; `client` fixture from it. Works because `get_db()` reads `DB_PATH` at call time.
Guard rails: never import `app` at module top level in tests (it would hit the real `spendly.db`); never `from database.db import DB_PATH`.

**`tests/test_registration.py`** — one test per Definition-of-done item:
- GET 200 with form; rendered action is `/register`; no `action="/`/`href="/` in register/login template sources
- valid POST → 302 to `/login`, user count +1
- follow redirect shows message in `.auth-success`; second `GET /login` doesn't
- hash ≠ plain and `check_password_hash` passes
- `"  Foo@Bar.com "` stored as `foo@bar.com`
- duplicate `demo@spendly.com` / `DEMO@Spendly.COM` → 400, message, no new row
- IntegrityError path: monkeypatch `app.get_user_by_email` → `None`, post demo email → 400 duplicate message
- empty name/email/password and whitespace-only name → 400 "All fields are required."
- `foo`, `foo@bar`, `@bar.com` → 400 invalid email
- 7-char password → 400; 8-char succeeds
- on error, name/email values preserved, password input has no `value`
- `.auth-success` block in `style.css` has no hex and uses `var(--`
- regression: `/`, `/login`, `/terms`, `/privacy` 200; stubs unchanged

## 6. Verification
1. `source venv/bin/activate && pytest -v` — all pass; `spendly.db` mtime and user count unchanged (tests used temp DB). Per CLAUDE.md, a subagent re-runs and confirms test results.
2. `python app.py` → http://127.0.0.1:5001/register: register a new user → redirected to `/login` with green banner that disappears on refresh; re-register `demo@spendly.com` → error with fields kept.
3. Server-side checks bypassing browser validation: `curl -i -d "name=A&email=a@b&password=12345678" http://127.0.0.1:5001/register` → 400.
4. `sqlite3 spendly.db "SELECT email, substr(password_hash,1,20) FROM users ORDER BY id DESC LIMIT 1;"` → lowercased email, `scrypt:` hash.
5. Other routes behave as before.
