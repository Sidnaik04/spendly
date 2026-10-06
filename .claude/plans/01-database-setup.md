# Plan: Step 1 — Database Setup

## Context
`database/db.py` is a comment-only stub and `app.py` has no DB wiring. Spec `.claude/specs/01-database-setup.md` asks for the SQLite data layer (`get_db`, `init_db`, `seed_db`) and startup initialization so later steps (auth, profile, expenses) have a schema and demo data. No new routes, no new packages (`sqlite3` + `werkzeug.security` only).

## 1. `database/db.py`
- Imports: `os`, `sqlite3`, `datetime.date`, `werkzeug.security.generate_password_hash`.
- `DB_PATH = os.path.join(<project root via os.path.dirname(os.path.dirname(os.path.abspath(__file__)))>, "spendly.db")` — absolute, so pytest / `flask run` from other dirs don't create a stray DB.
- `CATEGORIES = ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other")` — module constant, reusable by later form validation. No CHECK constraint (spec schema doesn't list one).
- **`get_db()`**: `sqlite3.connect(DB_PATH)`, `row_factory = sqlite3.Row`, `execute("PRAGMA foreign_keys = ON")`, return conn. Caller closes. No `g`/teardown yet.
- **`init_db()`**: `executescript` (static SQL, no values) with two `CREATE TABLE IF NOT EXISTS`:
  - `users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))`
  - `expenses(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL, date TEXT NOT NULL, description TEXT, created_at TEXT DEFAULT (datetime('now')), FOREIGN KEY (user_id) REFERENCES users(id))`
  - Commit + close in `try/finally`.
- **`seed_db()`**:
  1. `SELECT COUNT(*) FROM users` > 0 → close and return early.
  2. Insert demo user with `?` placeholders: `("Demo User", "demo@spendly.com", generate_password_hash("demo123"))`; take `cursor.lastrowid`.
  3. 8 expenses (all 7 categories, Food twice), float amounts, short descriptions, inserted via `executemany` with `?` placeholders.
  4. Dates: spread evenly from day 1 to today within the current month — `day = 1 + i * (today.day - 1) // 7` for i in 0..7 → `date(today.year, today.month, day).isoformat()`. Always `YYYY-MM-DD`, always current month, never in the future.
  5. Single commit at end; `finally: conn.close()`.

## 2. `app.py`
- Add `from database.db import get_db, init_db, seed_db`.
- After `app = Flask(__name__)`, at module level (not inside `__main__`):
  ```python
  with app.app_context():
      init_db()
      seed_db()
  ```
- No route changes; port stays 5001.

## 3. `.gitignore`
Add `*.db` and `*.db-journal` (currently not ignored).

## Out of scope
No `tests/` file (spec: "Files to create: None"). Note for a later step: importing `app` in tests will touch the real `spendly.db`; a configurable DB path belongs in the step that adds tests.

## Verification (delegate to a subagent per CLAUDE.md)
From project root with venv active:
1. `rm -f spendly.db && python -c "import app"` → `spendly.db` created in root.
2. `.schema` / `sqlite_master` → both tables, UNIQUE email, FK, NOT NULLs, defaults.
3. Counts: users = 1, expenses = 8, distinct categories = 7; all dates match current `YYYY-MM` and ≤ today.
4. `check_password_hash(stored, "demo123")` → True.
5. Re-run `init_db(); seed_db(); seed_db()` → counts unchanged.
6. `PRAGMA foreign_keys` on `get_db()` → 1.
7. Duplicate `demo@spendly.com` insert → `IntegrityError: UNIQUE constraint failed`.
8. Expense with `user_id=9999` → `IntegrityError: FOREIGN KEY constraint failed`.
9. `python app.py` + `curl localhost:5001/` → 200.
