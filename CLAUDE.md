# CLAUDE.md

## Project overview

Spendly is a lightweight personal expense tracker built with Flask and SQLite.

---

## Architecture
```
spendly/
├── app.py              # All routes — single file, no blueprints
├── database/
│   └── db.py           # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│   ├── base.html       # Shared layout — all templates must extend this
│   └── *.html          # One template per page
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles + :root tokens (incl. --cat-* colours)
│   │   ├── profile.css     # Profile-page-only styles
│   │   └── landing.css     # Landing-page-only styles (not yet created)
│   └── js/
│       └── main.js         # Vanilla JS only — Lucide icon init
└── requirements.txt
```

**Where things belong:**
- New routes → `app.py` only, no blueprints
- DB logic → `database/db.py` only, never inline in routes
- New pages → new `.html` file extending `base.html`
- Page-specific styles → new `.css` file, not inline `<style>` tags

---

## Code style

- Python: PEP 8, snake_case for all variables and functions
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs
- Route functions: one responsibility only — fetch data, render template, done
- DB queries: always use parameterized queries (`?` placeholders) — never f-strings in SQL
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`

---

## Tech constraints

- **Flask only** — no FastAPI, no Django, no other web frameworks
- **SQLite only** — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Vanilla JS only** — no React, no jQuery, no npm packages. The only third-party script is Lucide icons, loaded from a pinned unpkg URL in `base.html` (never `@latest`) and initialised in `main.js`
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise
- Python 3.10+ assumed — f-strings and `match` statements are fine

---

## Subagent Policy
- Always use a builtin explore subagent for codebase exploration 
  before implementing any new feature
- Always use a subagent to verify test results 
  after any implementation
- When asked to plan, delegate codebase research 
  to a subagent before presenting the plan
- always use a builtin plan subagent in plan mode

---

## Commands
```bash
# Setup
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_foo.py

# Run a specific test by name
pytest -k "test_name"

# Run tests with output visible
pytest -s
```

---

## Implemented vs stub routes

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET/POST /register` | Implemented — Step 2: validates, creates user, redirects to login; signed-in users are redirected to `/profile` |
| `GET/POST /login` | Implemented — Step 3: checks credentials, starts session, redirects to `/profile`; signed-in users are redirected to `/profile` |
| `GET /logout` | Implemented — Step 3: clears session, flashes message, redirects to login |
| `GET /profile` | Implemented — Step 4: login-guarded; renders `profile.html` with hardcoded `_profile_placeholder_data()` (real queries in Step 5) |
| `GET /expenses/add` | Stub — Step 7 |
| `GET /expenses/<id>/edit` | Stub — Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |

**Do not implement a stub route unless the active task explicitly targets that step.**

---

## Warnings and things to avoid

- **Never use raw string returns for stub routes** once a step is implemented — always render a template
- **Never hardcode URLs** in templates — always use `url_for()`
- **Never put DB logic in route functions** — it belongs in `database/db.py`
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync
- **Never use JS frameworks** — the frontend is intentionally vanilla
- **`database/db.py` helpers** — only `get_db()`, `init_db()`, `seed_db()`, `get_user_by_email()` and `create_user()` exist; do not assume others exist until the step that implements them
- **Tests** — never import `app` at module level in `tests/`; importing it runs `init_db()`/`seed_db()`. Use the fixtures in `tests/conftest.py`, which point `DB_PATH` at a temp file first
- **FK enforcement is manual** — SQLite foreign keys are off by default; `get_db()` must run `PRAGMA foreign_keys = ON` on every connection
- **Category colours** live only in `:root` as `--cat-<slug>` / `--cat-<slug>-light`; badges and bars pick them up via `.badge-<slug>` / `.cat-bar-<slug>` classes
- **Money formatting** — use the `inr` Jinja filter (defined in `app.py`) for every ₹ amount
- The app runs on **port 5001**, not the Flask default 5000 — don't change this